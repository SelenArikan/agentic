from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from config import NVIDIA_QA_FALLBACK_TO_RULES
from models import PostState
from providers import NvidiaBuildClient


class QAAgent:
    BANNED_WORDS = {"hate", "violence", "illegal"}

    def __init__(self, llm_client: Optional[NvidiaBuildClient] = None, *, strict_api: bool = False) -> None:
        self.llm_client = llm_client
        self.strict_api = strict_api

    def review(self, state: PostState) -> PostState:
        if self.llm_client:
            return self._review_with_nvidia(state)
        return self._review_with_rules(state)

    def _review_with_nvidia(self, state: PostState) -> PostState:
        media_exists = bool(state.media_path and Path(state.media_path).exists())
        try:
            data = self.llm_client.chat_json(
                [
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "task": "Quality assurance review for a social media post.",
                                "caption": state.caption,
                                "topic": state.topic,
                                "post_details": state.post_details,
                                "media_prompt": state.media_prompt,
                                "media_path_exists": media_exists,
                                "needs_media": state.routing_plan.get("media_creator", False) or state.has_media_file,
                                "reference_image_path": state.reference_image_path,
                                "rules": [
                                    "Approve only if caption is non-empty, safe, under 2200 characters, and aligned with the topic.",
                                    "Reject if caption copies post_details or implementation instructions instead of polished post copy.",
                                    "Reject if media is required but the media path does not exist.",
                                    "Reject unsafe, hateful, violent, illegal, or brand-risky content.",
                                ],
                                "schema": {"status": "approved|rejected", "feedback": "string"},
                            }
                        ),
                    }
                ],
                temperature=0.1,
            )
            status = str(data.get("status", "")).strip().lower()
            feedback = str(data.get("feedback", "")).strip() or "NVIDIA NIM QA completed."
            if status not in {"approved", "rejected"}:
                raise ValueError(f"Invalid QA status: {status}")
            if (state.routing_plan.get("media_creator", False) or state.has_media_file) and not media_exists:
                status = "rejected"
                feedback = f"{feedback} Media file is required but missing."
            state.qa_status = status
            state.qa_feedback = feedback
            state.add_log("qa", status, f"NVIDIA NIM QA: {feedback}")
            return state
        except Exception as exc:
            state.add_log("qa", "error", f"NVIDIA NIM QA failed: {exc}")
            if self.strict_api and not NVIDIA_QA_FALLBACK_TO_RULES:
                raise
            state.add_log("qa", "fallback", "Using local QA rules because NVIDIA QA is unavailable.")
            return self._review_with_rules(state)

    def _review_with_rules(self, state: PostState) -> PostState:
        feedback = []

        if not state.caption or not state.caption.strip():
            feedback.append("Caption is empty.")
        elif len(state.caption) > 2200:
            feedback.append("Caption is too long for a standard social media post.")

        lower_caption = (state.caption or "").lower()
        if caption_copies_post_details(state.caption or "", state.post_details or ""):
            feedback.append("Caption copies post details or creative brief text instead of using it only as guidance.")

        instructional_markers = (
            "yapmanı istiyorum",
            "şirketim",
            "post requirements",
            "create a social media image",
            "share this to the local demo",
        )
        if any(marker in lower_caption for marker in instructional_markers):
            feedback.append("Caption contains instructional or placeholder text instead of polished post copy.")

        banned = sorted(word for word in self.BANNED_WORDS if word in lower_caption)
        if banned:
            feedback.append(f"Caption contains banned words: {', '.join(banned)}.")

        if state.routing_plan.get("media_creator", False) or state.has_media_file:
            if not state.media_path:
                feedback.append("Media file is required but missing.")
            elif not Path(state.media_path).exists():
                feedback.append(f"Media file does not exist: {state.media_path}")

        media_prompt = " ".join([state.media_prompt or "", state.optimized_media_prompt or ""])
        if state.routing_plan.get("media_creator", False) and media_prompt and state.topic:
            if not topic_matches_media_prompt(state.topic, media_prompt):
                feedback.append("Media prompt does not clearly match the topic.")

        if feedback:
            state.qa_status = "rejected"
            state.qa_feedback = " ".join(feedback)
            state.add_log("qa", "rejected", state.qa_feedback)
        else:
            state.qa_status = "approved"
            state.qa_feedback = "Caption and media are ready for demo upload."
            state.add_log("qa", "approved", state.qa_feedback)

        return state


def topic_matches_media_prompt(topic: str, media_prompt: str) -> bool:
    topic_lower = topic.lower()
    prompt_lower = media_prompt.lower()
    first_topic_word = topic_lower.split()[0] if topic_lower.split() else ""
    if first_topic_word and first_topic_word in prompt_lower:
        return True
    semantic_aliases = [
        (("doğa", "outdoor", "trekking", "kamp"), ("outdoor", "hiking", "mountain", "trail", "camping", "trekking")),
        (("pilates",), ("pilates", "reformer", "studio", "wellness")),
        (("fitness", "spor"), ("fitness", "workout", "activewear", "training")),
    ]
    for topic_terms, prompt_terms in semantic_aliases:
        if any(term in topic_lower for term in topic_terms) and any(term in prompt_lower for term in prompt_terms):
            return True
    return False


def caption_copies_post_details(caption: str, post_details: str) -> bool:
    caption_tokens = normalize_for_overlap(caption).split()
    detail_tokens = normalize_for_overlap(post_details).split()
    if len(caption_tokens) < 4 or len(detail_tokens) < 4:
        return False

    caption_text = " ".join(caption_tokens)
    for size in range(6, 3, -1):
        for index in range(0, len(detail_tokens) - size + 1):
            phrase = " ".join(detail_tokens[index : index + size])
            if phrase and phrase in caption_text:
                return True

    detail_content = {token for token in detail_tokens if len(token) > 3 and token not in STOP_DETAIL_WORDS}
    if not detail_content:
        return False
    overlap = sum(1 for token in detail_content if token in caption_tokens)
    return overlap / len(detail_content) >= 0.65


def normalize_for_overlap(value: str) -> str:
    import re

    return re.sub(r"[^0-9a-zA-ZğüşöçıİĞÜŞÖÇ]+", " ", value.lower()).strip()


STOP_DETAIL_WORDS = {
    "olsun",
    "daha",
    "çok",
    "cok",
    "için",
    "icin",
    "with",
    "that",
    "this",
    "tone",
    "style",
    "post",
}
