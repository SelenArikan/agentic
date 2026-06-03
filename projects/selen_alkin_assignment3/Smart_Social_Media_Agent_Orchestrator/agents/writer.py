from __future__ import annotations

import json
from typing import Optional

from models import PostState
from providers import NvidiaBuildClient, NvidiaBuildError


class ContentWriterAgent:
    """Creates a caption and a media prompt without overwriting provided captions."""

    def __init__(self, llm_client: Optional[NvidiaBuildClient] = None, *, strict_api: bool = False) -> None:
        self.llm_client = llm_client
        self.strict_api = strict_api

    def write_content(self, state: PostState) -> PostState:
        if self.llm_client:
            generated = self._try_nvidia_writer(state)
            if generated:
                state.add_log("writer", "success", "Caption and media prompt generated with NVIDIA Build.")
                return state

        brief = build_local_brief(state)
        topic = brief["topic"]
        if state.topic != topic and should_replace_topic(state.topic, topic):
            state.topic = topic
        hashtags = state.hashtags[:4] or brief["hashtags"]

        if not state.caption:
            state.caption = brief["caption"]

        if not state.media_prompt and state.routing_plan.get("media_creator", False):
            state.media_prompt = brief["media_prompt"]

        state.add_log("writer", "success", "Caption and media prompt generated with local rules.")
        return state

    def _try_nvidia_writer(self, state: PostState) -> bool:
        if not self.llm_client:
            return False

        try:
            target_language = detect_language(" ".join([state.user_prompt or "", state.post_details or "", state.topic or ""]))
            data = self.llm_client.chat_json(
                [
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "task": "Generate social media caption and media prompt.",
                                "topic": state.topic,
                                "target_language": target_language,
                                "post_details": state.post_details,
                                "existing_caption": state.caption,
                                "keywords": state.keywords,
                                "hashtags": state.hashtags,
                                "visual_style": state.visual_style,
                                "reference_image": {
                                    "path": state.reference_image_path,
                                    "note": state.reference_image_note,
                                    "use_as_style_reference_only": bool(state.reference_image_path)
                                    and not state.use_reference_as_final_media,
                                },
                                "routing_plan": state.routing_plan,
                                "rules": [
                                    "Do not overwrite existing_caption if it is present.",
                                    "post_details are creative constraints and must not be copied directly into the caption.",
                                    "Use post_details for tone, colors, audience, visual direction, CTA, and constraints only.",
                                    "Write the caption in target_language. If target_language is en, do not write Turkish copy.",
                                    "Caption must be under 2200 characters.",
                                    "Use no more than 8 hashtags.",
                                    "Return media_prompt if media_creator is true.",
                                    "If a reference_image note exists, incorporate its style/composition in the media_prompt as text guidance.",
                                ],
                                "schema": {"caption": "string", "media_prompt": "string"},
                            }
                        ),
                    }
                ],
                temperature=0.4,
            )
        except (NvidiaBuildError, ValueError, TypeError) as exc:
            state.add_log("writer", "error" if self.strict_api else "warning", f"NVIDIA NIM writer failed: {exc}")
            if self.strict_api:
                raise
            return False

        if not state.caption:
            state.caption = str(data.get("caption", "")).strip() or None
        if state.routing_plan.get("media_creator", False) and not state.media_prompt:
            state.media_prompt = str(data.get("media_prompt", "")).strip() or None
            if state.reference_image_note and state.media_prompt:
                state.media_prompt = f"{state.media_prompt}. Reference guidance: {state.reference_image_note}"

        return bool(state.caption and (state.media_prompt or not state.routing_plan.get("media_creator", False)))


def _hashtag(text: str) -> str:
    return "".join(part.capitalize() for part in text.split())[:40] or "Post"


def build_local_brief(state: PostState) -> dict:
    base_prompt, embedded_requirements = split_post_requirements(state.user_prompt or "")
    request_source = clean_source_text(" ".join([base_prompt, state.topic or "", state.media_prompt or ""]))
    requirements = clean_source_text(" ".join([state.post_details or "", embedded_requirements]))
    language = detect_language(" ".join([request_source, requirements]))

    if language == "tr":
        return build_turkish_brief(state, request_source, requirements)

    extracted_topic = extract_english_topic(" ".join([request_source, requirements]))
    topic = normalize_english_topic(extracted_topic or state.topic or "your update")
    style = state.visual_style or "clean, modern, social-media-ready"
    hashtags = clean_english_hashtags(state.hashtags[:4], topic)
    visual_constraints = requirements or extract_english_visual_constraints(request_source) or style
    caption = english_caption_for_topic(topic, hashtags)
    return {
        "topic": topic,
        "caption": caption,
        "media_prompt": (
            f"{style} professional social media image about {topic}; visual constraints: {visual_constraints}; "
            "premium commercial photography, high quality composition, no text overlay"
        ),
        "hashtags": hashtags,
    }


def build_turkish_brief(state: PostState, source: str, requirements: str = "") -> dict:
    topic = extract_turkish_topic(source) or state.topic or "markanız"
    scene = extract_turkish_scene(source)
    visual_source = " ".join([source, requirements])
    image_palette = extract_palette(visual_source)
    mood = extract_mood(visual_source)
    hashtags = state.hashtags[:4] or hashtags_for_turkish_topic(topic)

    if "doğa" in topic.lower() or "outdoor" in source.lower():
        caption = (
            "Doğaya çıkmaya hazır mısın?\n\n"
            f"{topic.title()} için seçilmiş dayanıklı ve konforlu ürünlerle her rota daha güvenli, "
            "her yürüyüş daha keyifli.\n\n"
            "Ekipmanını seç, rotanı planla ve outdoor deneyimini bir üst seviyeye taşı.\n\n"
            f"{' '.join(hashtags)}"
        )
        media_prompt = (
            f"premium outdoor retail campaign photo, {scene}, wearing high-quality outdoor gear, "
            f"{mood} atmosphere, {image_palette} color palette, mountain trail, "
            "commercial lifestyle photography, realistic, no text overlay"
        )
    else:
        caption = (
            f"{topic.title()} için profesyonel ve dikkat çekici bir paylaşım.\n\n"
            "Markanızın değerini net anlatan, güven veren ve aksiyona çağıran modern bir sosyal medya dili.\n\n"
            f"{' '.join(hashtags)}"
        )
        media_prompt = (
            f"premium commercial social media photo for {topic}, {mood} atmosphere, {image_palette} color palette, "
            "professional brand campaign photography, realistic, no text overlay"
        )

    return {
        "topic": topic,
        "caption": caption,
        "media_prompt": media_prompt,
        "hashtags": hashtags,
    }


def clean_source_text(text: str) -> str:
    cleaned = text.replace("Post requirements:", " ")
    cleaned = cleaned.replace("Create a social media image for this post.", " ")
    cleaned = cleaned.replace("Share this to the local demo upload page.", " ")
    cleaned = cleaned.replace("Draft only. Do not upload.", " ")
    return " ".join(cleaned.split())


def split_post_requirements(text: str) -> tuple[str, str]:
    import re

    pattern = re.compile(
        r"Post requirements:\s*(.*?)(?=\s+(?:Create a social media image|Share this|No image|Text only|Use the uploaded|Draft only|Do not upload)\b|$)",
        flags=re.IGNORECASE,
    )
    requirements = []

    def remove(match: re.Match) -> str:
        requirements.append(match.group(1).strip())
        return " "

    base = pattern.sub(remove, text)
    return " ".join(base.split()), " ".join(part for part in requirements if part)


def detect_language(text: str) -> str:
    lower = text.lower()
    strong_turkish_markers = ("ğ", "ü", "ş", "ö", "ç", " için ", " olsun", " şirket", " burada", " burda")
    english_markers = (
        " i am ",
        " i'm ",
        " can you ",
        " make a ",
        " create a ",
        " instagram ",
        " selling ",
        " seller ",
        " image ",
        " photo ",
        " realistic ",
    )
    strong_count = sum(1 for marker in strong_turkish_markers if marker in lower)
    english_count = sum(1 for marker in english_markers if marker in f" {lower} ")
    has_many_dotless_i = lower.count("ı") >= 2
    if strong_count > 0 and english_count == 0:
        return "tr"
    if strong_count >= 2:
        return "tr"
    if has_many_dotless_i and english_count == 0:
        return "tr"
    return "en"


def should_replace_topic(current: Optional[str], replacement: str) -> bool:
    if not current:
        return True
    lower = current.lower()
    noisy_markers = (
        "yapmanı",
        "istiyorum",
        "şirketim",
        "post requirements",
        "my insta account",
        "in the image",
        "i want",
        "can you",
    )
    return len(current) > 55 or any(word in lower for word in noisy_markers)


def extract_turkish_topic(text: str) -> Optional[str]:
    lower = text.lower()
    if "doğa spor" in lower:
        return "doğa sporları ekipmanları"
    patterns = [
        r"şirketim\s+(.+?)\s+(?:satıyor|satmakta|için)",
        r"(.+?)\s+ile ilgili\s+(?:malzemeler|ürünler|ekipmanlar)",
        r"(.+?)\s+için\s+bir\s+post",
    ]
    for pattern in patterns:
        match = __import__("re").search(pattern, text, flags=__import__("re").IGNORECASE)
        if match:
            topic = normalize_turkish_topic(match.group(1))
            if topic:
                return topic
    return None


def extract_turkish_scene(text: str) -> str:
    import re

    patterns = [
        r"(?:burada|burda|görselde|fotoğrafta)\s+(.+?)\s+olsun",
        r"(.+?)\s+olsun",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            scene = " ".join(match.group(1).strip(" .,!").split())
            if 3 <= len(scene) <= 120 and not any(word in scene.lower() for word in ("tonlarında", "post requirements")):
                return translate_scene_to_english(scene)
    return "a man hiking on a scenic mountain trail"


def translate_scene_to_english(scene: str) -> str:
    lower = scene.lower()
    if "dağ" in lower and ("yürüyüş" in lower or "yuruyus" in lower):
        return "a man hiking on a scenic mountain trail"
    return scene


def extract_palette(text: str) -> str:
    lower = text.lower()
    colors = []
    for turkish, english in (("mavi", "blue"), ("beyaz", "white"), ("siyah", "black"), ("yeşil", "green"), ("bej", "beige")):
        if turkish in lower:
            colors.append(english)
    return ", ".join(colors) if colors else "natural brand"


def extract_palette_display(text: str) -> str:
    lower = text.lower()
    colors = []
    for color in ("mavi", "beyaz", "siyah", "yeşil", "bej"):
        if color in lower:
            colors.append(color)
    return ", ".join(colors) if colors else "markanıza uygun"


def extract_mood(text: str) -> str:
    lower = text.lower()
    if "cozy" in lower or "sıcak" in lower or "samimi" in lower:
        return "cozy"
    if "lüks" in lower or "premium" in lower:
        return "premium"
    return "polished"


def hashtags_for_turkish_topic(topic: str) -> list[str]:
    if "doğa" in topic.lower():
        return ["#DoğaSporları", "#Outdoor", "#Trekking", "#KampEkipmanları"]
    return [f"#{_hashtag(topic)}", "#Marka", "#SosyalMedya"]


def normalize_turkish_topic(text: str) -> Optional[str]:
    cleaned = " ".join(text.strip(" .,!?'\"").split())
    cleaned = cleaned.replace("ile ilgili", "").replace("malzemeler", "ekipmanları").strip()
    if not cleaned or cleaned.lower() in {"şirketim", "post", "bunun"}:
        return None
    return cleaned[:80]


def extract_english_topic(text: str) -> Optional[str]:
    import re

    normalized = normalize_english_request_text(text)
    product_topic = extract_product_topic(normalized)
    if product_topic:
        return product_topic

    for pattern in (
        r"\babout\s+(.+?)(?=\s+(?:with|create a social media image|share this|draft only|do not upload|no image|text only)\b|[.,]|$)",
        r"\bfor\s+(?:a|an)?\s*(.+?)\s+post\b",
    ):
        match = re.search(pattern, normalized, flags=re.IGNORECASE)
        if match:
            topic = normalize_english_topic(match.group(1).strip())
            if is_usable_english_topic(topic):
                return topic
    return None


def normalize_english_topic(text: str) -> str:
    cleaned = normalize_english_request_text(text)
    cleaned = " ".join(cleaned.strip(" .,!?'\"").split())
    cleaned = remove_english_topic_noise(cleaned)
    if len(cleaned) > 80:
        cleaned = cleaned[:77].rsplit(" ", 1)[0] + "..."
    return cleaned or "your update"


def normalize_english_request_text(text: str) -> str:
    cleaned = text.replace("ı", "i").replace("İ", "I")
    replacements = {
        "jewerly": "jewelry",
        "jewellery": "jewelry",
        "earings": "earrings",
        "earing": "earring",
        "shoukld": "should",
        "photage": "photo",
        "closer": "close-up",
        "insta": "instagram",
    }
    for typo, replacement in replacements.items():
        cleaned = cleaned.replace(typo, replacement).replace(typo.capitalize(), replacement.capitalize())
    cleaned = remove_generation_boilerplate(cleaned)
    return " ".join(cleaned.split())


def extract_product_topic(text: str) -> Optional[str]:
    lower = text.lower()
    if "earring" in lower and "silver" in lower:
        return "silver earrings"
    if "earring" in lower:
        return "earrings"
    if "jewelry" in lower and "silver" in lower:
        return "silver jewelry"
    if "jewelry" in lower:
        return "jewelry"

    import re

    selling_match = re.search(
        r"\bselling\s+(.+?)(?:\s+(?:on|for|and|can|make|create|post|image|photo)\b|[.,]|$)",
        text,
        flags=re.IGNORECASE,
    )
    if selling_match:
        return normalize_english_topic(selling_match.group(1))
    return None


def remove_english_topic_noise(text: str) -> str:
    import re

    cleaned = re.sub(r"\b(?:my|your|the)?\s*(?:instagram|insta)\s+account\b", " ", text, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b(?:can you|could you|please|make|create|post|share|publish)\b", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b(?:in the image|i want you to|i want|there should be|they must be|realistic)\b", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b(?:image|photo|picture|post|caption|account)\b", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b(?:a\s+)?social\s+media(?:\s+image)?(?:\s+for\s+this)?\b", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b(?:local\s+demo\s+upload\s+page|demo\s+upload\s+page)\b", " ", cleaned, flags=re.IGNORECASE)
    return " ".join(cleaned.strip(" .,!?'\"").split())


def remove_generation_boilerplate(text: str) -> str:
    import re

    cleaned = re.sub(r"\bcreate a social media image for this post\b", " ", text, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bshare this to the local demo upload page\b", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bdraft only\.?\s*do not upload\b", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bno image\.?\s*text only\b", " ", cleaned, flags=re.IGNORECASE)
    return cleaned


def is_usable_english_topic(topic: str) -> bool:
    lower = topic.lower()
    if not topic or topic == "your update":
        return False
    noisy = ("instagram account", "in the image", "i want", "can you", "photo of", "picture of")
    return not any(marker in lower for marker in noisy)


def clean_english_hashtags(existing: list[str], topic: str) -> list[str]:
    usable = []
    for tag in existing:
        normalized = tag.strip()
        if not normalized:
            continue
        compact = normalized.lower().replace("#", "")
        if len(compact) > 28 or "," in compact:
            continue
        if any(noise in compact for noise in ("myinsta", "intheimage", "iwant", "canyou")):
            continue
        usable.append(normalized if normalized.startswith("#") else f"#{normalized}")
    if usable:
        return usable[:4]
    if "earring" in topic.lower() or "jewelry" in topic.lower():
        return ["#SilverJewelry", "#Earrings", "#JewelryStyle", "#MinimalLuxury"]
    return [f"#{_hashtag(topic)}", "#socialmedia"]


def extract_english_visual_constraints(text: str) -> Optional[str]:
    lower = normalize_english_request_text(text).lower()
    if "ear" in lower and "earring" in lower:
        count = "three" if "3" in lower or "three" in lower else "multiple"
        material = "silver " if "silver" in lower else ""
        return (
            f"close-up realistic commercial photo of a woman's ear wearing {count} "
            f"{material}earrings, sharp jewelry detail, natural skin texture, elegant styling"
        )
    if "close-up" in lower or "close up" in lower:
        return "close-up realistic commercial photography with sharp product detail"
    return None


def english_caption_for_topic(topic: str, hashtags: list[str]) -> str:
    lower = topic.lower()
    if "earring" in lower or "jewelry" in lower:
        return (
            "Small details, strong presence.\n\n"
            f"Discover {topic} designed to bring a clean, polished finish to everyday style. "
            "Elegant, versatile, and made for close-up moments.\n\n"
            f"{' '.join(hashtags)}"
        )
    return (
        f"Bring more intention into your day with {topic}.\n\n"
        "Designed for people who care about quality, comfort, and real momentum.\n\n"
        f"{' '.join(hashtags)}"
    )
