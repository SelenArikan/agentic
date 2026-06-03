from __future__ import annotations

import re
from typing import Any, Optional

from models import PostState

from .writer import (
    detect_language,
    extract_english_topic,
    extract_turkish_topic,
    is_usable_english_topic,
    normalize_english_request_text,
    normalize_english_topic,
)


class RequestBriefVerifierAgent:
    """Extract a structured requirement brief before the main route executes."""

    LOW_CONFIDENCE = 0.55
    GENERIC_TOPICS = {"this", "it", "that", "post", "image", "content", "your update"}

    def prepare(self, state: PostState) -> PostState:
        source = " ".join(part for part in (state.user_prompt, state.post_details or "") if part).strip()
        current_topic = self._usable_topic(state.topic)
        extracted_topic = current_topic or self._extract_topic(source)
        visual_constraints, avoid_constraints = extract_visual_constraints(source)
        ambiguities = []

        if not extracted_topic:
            ambiguities.append("topic_missing")
        if has_ambiguous_reference(source):
            ambiguities.append("ambiguous_reference")

        confidence = self._confidence(extracted_topic, ambiguities)
        state.request_confidence = confidence
        state.request_brief = {
            "version": "assignment4_requirement_brief_v1",
            "topic": extracted_topic,
            "language": detect_language(source),
            "media_required": media_requested(source),
            "upload_requested": upload_requested(source),
            "visual_constraints": visual_constraints,
            "avoid_constraints": avoid_constraints,
            "ambiguities": ambiguities,
            "confidence": confidence,
        }

        if extracted_topic and confidence >= self.LOW_CONFIDENCE and not self._usable_topic(state.topic):
            state.topic = extracted_topic

        if confidence < self.LOW_CONFIDENCE:
            state.approval_required = True
            state.approval_reason = "Low-confidence request brief requires human confirmation before publish."

        state.add_log(
            "request_brief_verifier",
            "success" if confidence >= self.LOW_CONFIDENCE else "low_confidence",
            "Structured requirement brief prepared.",
            topic=extracted_topic,
            confidence=confidence,
            visual_constraints=visual_constraints,
            ambiguities=ambiguities,
        )
        return state

    def needs_topic_clarification(self, state: PostState) -> bool:
        brief = state.request_brief or {}
        if state.clarification_history or self._usable_topic(state.topic):
            return False
        return float(brief.get("confidence") or 0) < self.LOW_CONFIDENCE and bool(brief.get("ambiguities"))

    def enforce_visual_constraints(self, state: PostState) -> PostState:
        brief = state.request_brief or {}
        constraints = list(brief.get("visual_constraints") or [])
        avoid = list(brief.get("avoid_constraints") or [])
        if not constraints and not avoid:
            return state

        base = state.media_prompt or f"professional social media image about {state.topic or 'the requested topic'}"
        lower = base.lower()
        additions = []
        if constraints and "required user visual constraints:" not in lower:
            additions.append(f"Required user visual constraints: {', '.join(constraints)}")
        if avoid and "avoid user constraint violations:" not in lower:
            additions.append(f"Avoid user constraint violations: {', '.join(avoid)}")
        if not additions:
            return state

        state.media_prompt = f"{base}; {'; '.join(additions)}"
        state.optimized_media_prompt = None
        state.negative_media_prompt = None
        state.visual_prompt_template = None
        state.add_log(
            "request_brief_verifier",
            "constraints_applied",
            "User visual constraints injected before visual prompt generation.",
            visual_constraints=constraints,
            avoid_constraints=avoid,
        )
        return state

    def _extract_topic(self, source: str) -> Optional[str]:
        turkish = extract_turkish_topic(source)
        if turkish:
            return turkish

        english = extract_english_topic(source)
        if self._usable_topic(english):
            return english

        direct_post_match = re.search(
            r"\b(?:make|create|write)\s+(?:a|an)\s+(.+?)\s+post\b",
            normalize_english_request_text(source),
            flags=re.IGNORECASE,
        )
        if direct_post_match:
            candidate = normalize_english_topic(direct_post_match.group(1))
            if self._usable_topic(candidate):
                return candidate

        visual_match = re.search(
            r"\b(?:picture|image|photo|visual)\s+(?:of|showing|with)\s+(.+?)(?:[.,]|$)",
            normalize_english_request_text(source),
            flags=re.IGNORECASE,
        )
        if visual_match:
            candidate = normalize_english_topic(visual_match.group(1))
            if self._usable_topic(candidate):
                return candidate
        return None

    def _usable_topic(self, topic: Optional[str]) -> Optional[str]:
        if not topic:
            return None
        normalized = normalize_english_topic(topic)
        if normalized.lower() in self.GENERIC_TOPICS:
            return None
        if not is_usable_english_topic(normalized):
            return None
        return topic.strip()

    def _confidence(self, topic: Optional[str], ambiguities: list[str]) -> float:
        if not topic:
            return 0.2
        if "ambiguous_reference" in ambiguities:
            return 0.35
        return 0.92


def has_ambiguous_reference(text: str) -> bool:
    lower = normalize_english_request_text(text).lower()
    patterns = (
        r"\b(?:make|create|write|share)\s+(?:a\s+)?post\s+about\s+(?:this|it|that)\b",
        r"\b(?:post|share|upload)\s+(?:this|it|that)\b",
    )
    return any(re.search(pattern, lower) for pattern in patterns)


def media_requested(text: str) -> bool:
    lower = text.lower()
    if any(phrase in lower for phrase in ("no image", "without image", "text only", "caption only")):
        return False
    return any(word in lower for word in ("post", "image", "photo", "picture", "visual", "görsel", "fotoğraf"))


def upload_requested(text: str) -> bool:
    lower = text.lower()
    if any(phrase in lower for phrase in ("draft only", "do not upload", "no upload")):
        return False
    return any(word in lower for word in ("share", "publish", "upload", "post", "paylaş"))


def extract_visual_constraints(text: str) -> tuple[list[str], list[str]]:
    lower = normalize_english_request_text(text).lower()
    required: list[str] = []
    avoid: list[str] = []

    if any(word in lower for word in ("outdoor", "outside", "park", "garden", "nature", "açık hava")):
        required.append("outdoor environment")
    if "park" in lower:
        required.append("park setting")
    if "pilates" in lower and "mat" in lower:
        required.append("mat Pilates exercise")
    if "close-up" in lower or "close up" in lower or "macro" in lower:
        required.append("close-up composition")
    if "ear" in lower and "earring" in lower:
        required.append("earrings visible on a woman's ear")
    if ("3 " in f"{lower} " or "three" in lower) and "earring" in lower:
        required.append("three earrings")
    if "silver" in lower and "earring" in lower:
        required.append("silver earrings")
    if "dağ" in lower or "mountain" in lower:
        required.append("mountain setting")
    if "hiking" in lower or "yürüyüş" in lower or "yuruyus" in lower:
        required.append("hiking subject")

    if any(phrase in lower for phrase in ("not an indoor", "not indoor", "not a studio", "no studio")):
        avoid.append("indoor studio")
    if "no text" in lower or "without text" in lower:
        avoid.append("text overlay")

    return dedupe(required), dedupe(avoid)


def dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))
