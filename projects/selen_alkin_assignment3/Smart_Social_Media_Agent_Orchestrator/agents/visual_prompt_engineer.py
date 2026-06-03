from __future__ import annotations

import json
from typing import Any, Dict, Optional

from models import PostState
from providers import NvidiaBuildClient, NvidiaBuildError


class VisualPromptEngineerAgent:
    """Turns a rough media prompt into a structured, production-grade photo brief."""

    def __init__(self, llm_client: Optional[NvidiaBuildClient] = None, *, strict_api: bool = False) -> None:
        self.llm_client = llm_client
        self.strict_api = strict_api

    def refine_prompt(self, state: PostState) -> PostState:
        if not state.routing_plan.get("media_creator", False) or state.has_media_file:
            state.add_log("visual_prompt_engineer", "skipped", "Visual prompt engineering skipped by routing plan.")
            return state

        if self.llm_client:
            generated = self._try_nvidia_prompt_engineer(state)
            if generated:
                state.add_log(
                    "visual_prompt_engineer",
                    "success",
                    "Professional visual prompt JSON generated with NVIDIA Build.",
                )
                return state

        template = self._local_template(state)
        self._apply_template(state, template)
        state.add_log("visual_prompt_engineer", "success", "Professional visual prompt JSON generated with local rules.")
        return state

    def _try_nvidia_prompt_engineer(self, state: PostState) -> bool:
        if not self.llm_client:
            return False

        try:
            data = self.llm_client.chat_json(
                [
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "task": "Convert a rough social media image request into a professional text-to-image photo prompt JSON.",
                                "topic": state.topic,
                                "rough_media_prompt": state.media_prompt,
                                "post_details": state.post_details,
                                "visual_style": state.visual_style,
                                "caption": state.caption,
                                "reference_image": {
                                    "path": state.reference_image_path,
                                    "note": state.reference_image_note,
                                    "use_as_style_reference_only": bool(state.reference_image_path)
                                    and not state.use_reference_as_final_media,
                                },
                                "rules": [
                                    "Output must be photorealistic commercial photography, not illustration.",
                                    "post_details are visual constraints; use them for color palette, mood, composition, and brand direction.",
                                    "Do not turn post_details into visible text, typography, or caption overlays.",
                                    "Make the image look like a premium brand campaign, not a generic stock image.",
                                    "Use precise camera, lens, lighting, composition, subject, environment, color palette, and quality details.",
                                    "Avoid text overlays, logos, watermarks, distorted anatomy, extra limbs, bad hands, low resolution, clutter, and unrealistic objects.",
                                    "If the user explicitly asks for outdoor, mountain, trail, park, or nature, the environment must be outdoors.",
                                    "For outdoor Pilates, use a realistic outdoor mat/bodyweight Pilates scene; do not use a studio or reformer machine unless explicitly requested.",
                                    "If the topic is fitness or Pilates without outdoor constraints, prefer elegant boutique studio realism, correct equipment, natural body posture, and warm editorial lighting.",
                                    "Return only JSON. No Markdown.",
                                ],
                                "schema": {
                                    "version": "professional_photo_v1",
                                    "creative_brief": "string",
                                    "subject": "string",
                                    "environment": "string",
                                    "composition": "string",
                                    "camera": {
                                        "shot_type": "string",
                                        "angle": "string",
                                        "lens": "string",
                                        "depth_of_field": "string",
                                    },
                                    "lighting": {
                                        "source": "string",
                                        "mood": "string",
                                        "color_temperature": "string",
                                    },
                                    "style": {
                                        "aesthetic": "string",
                                        "color_palette": "string",
                                        "texture": "string",
                                    },
                                    "quality_modifiers": ["string"],
                                    "negative_prompt": "string",
                                    "final_prompt": "string",
                                },
                            }
                        ),
                    }
                ],
                temperature=0.25,
                max_tokens=1400,
            )
        except (NvidiaBuildError, ValueError, TypeError) as exc:
            state.add_log(
                "visual_prompt_engineer",
                "error" if self.strict_api else "warning",
                f"NVIDIA NIM visual prompt engineer failed: {exc}",
            )
            if self.strict_api:
                raise
            return False

        template = self._normalize_template(data, state)
        self._apply_template(state, template)
        return bool(state.optimized_media_prompt)

    def _local_template(self, state: PostState) -> Dict[str, Any]:
        topic = state.topic or "the requested social media post"
        rough_prompt = state.media_prompt or topic
        style = state.visual_style or "warm editorial"
        detail_palette = extract_visual_palette(state.post_details or "")
        detail_mood = extract_visual_mood(state.post_details or "")
        is_pilates = "pilates" in f"{topic} {rough_prompt}".lower()
        is_outdoor = any(
            word in f"{topic} {rough_prompt}".lower()
            for word in ("outdoor", "hiking", "mountain", "trekking", "doğa", "dağ", "kamp")
        )

        if is_outdoor and is_pilates:
            subject = "one adult woman practicing outdoor mat Pilates exercises on a yoga mat"
            environment = (
                "peaceful outdoor park or garden setting, soft grass, trees, open sky, fresh morning atmosphere, "
                "natural wellness lifestyle environment"
            )
            composition = (
                "editorial three-quarter lifestyle composition, Pilates mat and full body posture clearly visible, "
                "rule of thirds, clean negative space for social crop, no text overlay"
            )
            quality_context = [
                "photorealistic",
                "premium outdoor wellness brand campaign",
                "high-end editorial fitness photography",
                "natural anatomy",
                "accurate mat Pilates posture",
                "outdoor exercise realism",
                "sharp focus",
                "balanced exposure",
                "social media ready",
            ]
            negative_context = "indoor Pilates studio, reformer machine, gym interior, awkward pose, unrealistic body proportions"
        elif is_pilates:
            subject = "an elegant Pilates practice scene with one adult subject on a reformer machine"
            environment = (
                "premium boutique Pilates studio, natural wood reformer beds, warm neutral walls, soft plants, "
                "clean uncluttered interior, realistic wellness studio details"
            )
            composition = (
                "editorial three-quarter composition, subject and reformer framed cleanly, rule of thirds, "
                "subtle negative space for social crop, no text overlay"
            )
            quality_context = [
                "photorealistic",
                "premium wellness brand campaign",
                "high-end editorial fitness photography",
                "natural anatomy",
                "accurate Pilates equipment",
                "sharp focus",
                "balanced exposure",
                "social media ready",
            ]
            negative_context = "malformed reformer machine, awkward pose, unrealistic body proportions"
        elif is_outdoor:
            subject = "one adult man hiking on a mountain trail wearing premium technical outdoor gear"
            environment = (
                "scenic mountain hiking trail, soft mist, layered hills, natural rocks and pine trees, "
                "cozy adventure atmosphere, outdoor retail campaign setting"
            )
            composition = (
                "editorial three-quarter lifestyle composition, hiker framed on the trail, rule of thirds, "
                "strong product visibility, clean negative space for social crop, no text overlay"
            )
            quality_context = [
                "photorealistic",
                "premium outdoor retail campaign",
                "high-end adventure lifestyle photography",
                "natural anatomy",
                "realistic technical hiking equipment",
                "sharp focus",
                "balanced exposure",
                "social media ready",
            ]
            negative_context = "unsafe cliff edge, fake gear, distorted backpack straps, unrealistic terrain"
        else:
            subject = f"photorealistic commercial lifestyle subject for {topic}"
            environment = f"professionally styled environment matching this brief: {rough_prompt}"
            composition = "editorial social media composition, rule of thirds, clean background, no text overlay"
            quality_context = [
                "photorealistic",
                "premium brand campaign",
                "high-end editorial commercial photography",
                "natural anatomy",
                "sharp focus",
                "balanced exposure",
                "social media ready",
            ]
            negative_context = "generic stock photo, unrealistic objects"

        camera = {
            "shot_type": "premium lifestyle campaign photograph",
            "angle": "natural eye-level to slight three-quarter angle",
            "lens": "35mm full-frame lens",
            "depth_of_field": "soft background separation with crisp subject detail",
        }
        lighting = {
            "source": "large natural window light with soft fill",
            "mood": detail_mood or "warm, calm, polished, aspirational",
            "color_temperature": "warm daylight, balanced skin tones",
        }
        palette = (
            "natural greens, soft sky blue, warm sunlight, clean whites, earthy neutrals"
            if is_outdoor
            else "warm neutrals, soft beige, natural wood, muted green accents, clean whites"
        )
        texture = (
            "real athletic fabric texture, natural skin texture, soft grass, outdoor wellness details"
            if is_outdoor
            else "real fabric texture, natural skin texture, polished studio surfaces"
        )
        visual_style = {
            "aesthetic": f"{style} premium commercial photography, realistic not CGI",
            "color_palette": detail_palette or palette,
            "texture": texture,
        }
        quality_modifiers = quality_context
        negative_prompt = (
            "text, typography, caption, logo, watermark, signature, blurry, low resolution, pixelated, cartoon, "
            "illustration, CGI, plastic skin, distorted anatomy, extra limbs, missing limbs, bad hands, bad feet, "
            f"duplicate person, cluttered scene, harsh flash, oversaturated colors, uncanny face, {negative_context}"
        )
        final_prompt = build_final_prompt(
            {
                "creative_brief": f"Create a professional social media image for: {rough_prompt}",
                "subject": subject,
                "environment": environment,
                "composition": composition,
                "camera": camera,
                "lighting": lighting,
                "style": visual_style,
                "quality_modifiers": quality_modifiers,
                "negative_prompt": negative_prompt,
            }
        )

        return {
            "version": "professional_photo_v1",
            "creative_brief": f"Create a professional social media image for: {rough_prompt}",
            "subject": subject,
            "environment": environment,
            "composition": composition,
            "camera": camera,
            "lighting": lighting,
            "style": visual_style,
            "quality_modifiers": quality_modifiers,
            "negative_prompt": negative_prompt,
            "final_prompt": final_prompt,
        }

    def _normalize_template(self, data: Dict[str, Any], state: PostState) -> Dict[str, Any]:
        fallback = self._local_template(state)
        template = {
            "version": str(data.get("version") or fallback["version"]),
            "creative_brief": str(data.get("creative_brief") or fallback["creative_brief"]),
            "subject": str(data.get("subject") or fallback["subject"]),
            "environment": str(data.get("environment") or fallback["environment"]),
            "composition": str(data.get("composition") or fallback["composition"]),
            "camera": _dict_or_fallback(data.get("camera"), fallback["camera"]),
            "lighting": _dict_or_fallback(data.get("lighting"), fallback["lighting"]),
            "style": _dict_or_fallback(data.get("style"), fallback["style"]),
            "quality_modifiers": _list_or_fallback(data.get("quality_modifiers"), fallback["quality_modifiers"]),
            "negative_prompt": str(data.get("negative_prompt") or fallback["negative_prompt"]),
        }
        final_prompt = str(data.get("final_prompt") or "").strip()
        template["final_prompt"] = final_prompt or build_final_prompt(template)
        if violates_environment_constraints(template, state):
            return fallback
        return template

    def _apply_template(self, state: PostState, template: Dict[str, Any]) -> None:
        state.visual_prompt_template = template
        state.optimized_media_prompt = str(template.get("final_prompt") or "").strip() or state.media_prompt
        state.negative_media_prompt = str(template.get("negative_prompt") or "").strip() or None


def build_final_prompt(template: Dict[str, Any]) -> str:
    camera = template.get("camera") if isinstance(template.get("camera"), dict) else {}
    lighting = template.get("lighting") if isinstance(template.get("lighting"), dict) else {}
    style = template.get("style") if isinstance(template.get("style"), dict) else {}
    quality = template.get("quality_modifiers")
    quality_text = ", ".join(str(item) for item in quality if item) if isinstance(quality, list) else str(quality or "")

    parts = [
        template.get("creative_brief"),
        f"Subject: {template.get('subject')}",
        f"Environment: {template.get('environment')}",
        f"Composition: {template.get('composition')}",
        "Camera: "
        + ", ".join(
            str(value)
            for value in [
                camera.get("shot_type"),
                camera.get("angle"),
                camera.get("lens"),
                camera.get("depth_of_field"),
            ]
            if value
        ),
        "Lighting: "
        + ", ".join(
            str(value)
            for value in [
                lighting.get("source"),
                lighting.get("mood"),
                lighting.get("color_temperature"),
            ]
            if value
        ),
        "Style: "
        + ", ".join(
            str(value)
            for value in [
                style.get("aesthetic"),
                style.get("color_palette"),
                style.get("texture"),
            ]
            if value
        ),
        f"Quality: {quality_text}",
        "No text overlay, no logo, no watermark.",
    ]
    return ". ".join(str(part).strip(" .") for part in parts if part).strip()


def _dict_or_fallback(value: Any, fallback: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(value, dict):
        return fallback
    merged = dict(fallback)
    for key, item in value.items():
        if item:
            merged[str(key)] = str(item)
    return merged


def _list_or_fallback(value: Any, fallback: list[str]) -> list[str]:
    if not isinstance(value, list):
        return fallback
    cleaned = [str(item).strip() for item in value if str(item).strip()]
    return cleaned or fallback


def violates_environment_constraints(template: Dict[str, Any], state: PostState) -> bool:
    text = " ".join(
        str(value)
        for value in [
            state.topic,
            state.media_prompt,
            state.post_details,
            state.user_prompt,
            template.get("subject"),
            template.get("environment"),
            template.get("creative_brief"),
            template.get("final_prompt"),
        ]
        if value
    ).lower()
    request_text = " ".join(
        str(value)
        for value in [state.topic, state.media_prompt, state.post_details, state.user_prompt]
        if value
    ).lower()
    wants_outdoor = any(
        word in request_text
        for word in ("outdoor", "outside", "park", "garden", "nature", "trail", "mountain", "doğa", "dağ", "açık hava")
    )
    wants_pilates = "pilates" in request_text
    if not wants_outdoor:
        return False
    indoor_markers = ("studio", "indoor", "interior", "reformer", "reformer machine", "gym interior")
    outdoor_markers = ("outdoor", "outside", "park", "garden", "grass", "nature", "trail", "mountain", "open sky")
    if any(marker in text for marker in indoor_markers):
        return True
    if wants_pilates and not any(marker in text for marker in outdoor_markers):
        return True
    return False


def extract_visual_palette(text: str) -> Optional[str]:
    lower = text.lower()
    colors = []
    for source, target in (
        ("mavi", "deep blue"),
        ("beyaz", "clean white"),
        ("siyah", "matte black"),
        ("yeşil", "muted green"),
        ("bej", "warm beige"),
        ("blue", "deep blue"),
        ("white", "clean white"),
        ("black", "matte black"),
    ):
        if source in lower and target not in colors:
            colors.append(target)
    if colors:
        return ", ".join(colors) + " brand palette"
    return None


def extract_visual_mood(text: str) -> Optional[str]:
    lower = text.lower()
    if "cozy" in lower or "sıcak" in lower or "samimi" in lower:
        return "cozy, warm, inviting, polished"
    if "premium" in lower or "lüks" in lower:
        return "premium, refined, aspirational"
    if "minimal" in lower:
        return "minimal, clean, calm"
    return None
