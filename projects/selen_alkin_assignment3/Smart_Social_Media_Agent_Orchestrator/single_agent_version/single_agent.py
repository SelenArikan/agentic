from __future__ import annotations

import base64
import json
import re
import sys
import textwrap
import time
from pathlib import Path
from typing import Any, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents.qa_agent import caption_copies_post_details, topic_matches_media_prompt
from agents.writer import build_local_brief, detect_language, extract_english_topic
from config import (
    IMAGE_PROVIDER,
    MISTRAL_API_KEY,
    MISTRAL_IMAGE_MODEL,
    NVIDIA_API_KEY,
    NVIDIA_BASE_URL,
    NVIDIA_IMAGE_BASE_URL,
    NVIDIA_IMAGE_CANDIDATES,
    NVIDIA_IMAGE_ENDPOINT,
    NVIDIA_IMAGE_MODEL,
    NVIDIA_MODEL,
    NVIDIA_WRITER_MODEL,
    OUTPUT_DIR,
)
from models import PostState
from providers import MistralImageClient, NvidiaBuildClient, NvidiaBuildError


SINGLE_OUTPUT_DIR = OUTPUT_DIR / "single_agent"


class SingleSocialMediaAgent:
    """One agent that handles planning, writing, media creation, QA, and demo upload.

    The multi-agent version delegates these responsibilities to specialized agents.
    This class intentionally keeps the same output contract while recording every
    step under a single `single_agent` log channel for Assignment 3 comparison.
    """

    BANNED_WORDS = {"illegal", "violence", "hate", "self-harm"}

    def __init__(
        self,
        *,
        provider: str = "mock",
        image_provider: str = IMAGE_PROVIDER,
        output_dir: Path | str = SINGLE_OUTPUT_DIR,
        use_playwright: bool = False,
    ) -> None:
        self.provider = provider
        self.image_provider = image_provider
        self.output_dir = Path(output_dir)
        self.use_playwright = use_playwright
        self.llm_client = NvidiaBuildClient(model=NVIDIA_WRITER_MODEL) if provider == "nvidia" else None
        self.nvidia_image_client = self._build_nvidia_image_client()
        self.mistral_image_client = self._build_mistral_image_client()

    def run(self, state: PostState) -> PostState:
        started_at = time.perf_counter()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        state.image_provider = self.image_provider
        state.add_log(
            "single_agent",
            "start",
            "Single-agent workflow started.",
            architecture="single_agent",
            provider=self.provider,
            image_provider=self.image_provider,
        )

        needs_media, needs_upload = self._plan(state)
        self._create_content(state, needs_media)

        if needs_media and not state.has_media_file:
            self._build_visual_prompt(state)
            self._create_media(state)
        elif state.has_media_file:
            state.add_log("single_agent", "media_ready", "Using existing media file.")

        self._quality_check(state, needs_media)
        if state.qa_status == "rejected":
            self._repair_once(state, needs_media)

        if state.qa_status == "approved" and needs_upload:
            self._upload_to_demo(state)
        elif needs_upload:
            state.add_log("single_agent", "blocked", "QA rejected the post; browser step skipped.")

        elapsed_ms = round((time.perf_counter() - started_at) * 1000)
        state.add_log("single_agent", "success", f"Single-agent workflow finished in {elapsed_ms} ms.", elapsed_ms=elapsed_ms)
        self._save_outputs(state)
        return state

    def _plan(self, state: PostState) -> tuple[bool, bool]:
        prompt = state.user_prompt or ""
        lower = prompt.lower()

        if not state.caption:
            state.caption = extract_caption(prompt)
        if not state.topic:
            state.topic = extract_english_topic(prompt) or extract_basic_topic(prompt)
        if not state.platform:
            state.platform = extract_platform(lower) or "local_demo"

        needs_media = should_create_media(lower, state)
        needs_upload = should_upload(lower)
        state.routing_plan = {
            "single_agent": True,
            "uses_media_tool": needs_media and not state.has_media_file,
            "uses_browser_tool": needs_upload,
        }
        state.add_log(
            "single_agent",
            "planning",
            "Prompt parsed and single-agent route selected.",
            topic=state.topic,
            needs_media=needs_media,
            needs_upload=needs_upload,
        )
        return needs_media, needs_upload

    def _create_content(self, state: PostState, needs_media: bool) -> None:
        if self.llm_client and self._try_nvidia_content(state, needs_media):
            state.add_log("single_agent", "content", "Caption, hashtags, and visual brief generated with one NVIDIA NIM call.")
            return

        brief = build_local_brief(state)
        state.topic = brief["topic"]
        state.hashtags = brief["hashtags"]
        if not state.caption:
            state.caption = brief["caption"]
        if needs_media and not state.media_prompt:
            state.media_prompt = brief["media_prompt"]
        state.add_log("single_agent", "content", "Caption, hashtags, and media prompt generated by the single-agent local policy.")

    def _try_nvidia_content(self, state: PostState, needs_media: bool) -> bool:
        if not self.llm_client:
            return False

        target_language = detect_language(" ".join([state.user_prompt or "", state.post_details or "", state.topic or ""]))
        payload = {
            "task": "Act as one single social media automation agent.",
            "user_prompt": state.user_prompt,
            "topic": state.topic,
            "post_details": state.post_details,
            "existing_caption": state.caption,
            "visual_style": state.visual_style,
            "target_language": target_language,
            "needs_media": needs_media,
            "rules": [
                "Return one coherent result from a single agent, not a multi-agent plan.",
                "If existing_caption is present, keep it unchanged.",
                "If target_language is en, write English. If target_language is tr, write Turkish.",
                "Do not copy raw instructions or post_details into the caption.",
                "For product posts, infer the product as the topic.",
                "Return media_prompt and optimized_media_prompt when needs_media is true.",
                "Avoid text overlays, watermarks, logos, and unrealistic anatomy in media prompts.",
            ],
            "schema": {
                "topic": "string",
                "caption": "string",
                "hashtags": ["#string"],
                "media_prompt": "string",
                "optimized_media_prompt": "string",
                "negative_media_prompt": "string",
            },
        }
        try:
            data = self.llm_client.chat_json([{"role": "user", "content": json.dumps(payload)}], temperature=0.35)
        except (NvidiaBuildError, ValueError, TypeError) as exc:
            state.add_log("single_agent", "warning", f"NVIDIA single-agent content call failed: {exc}")
            return False

        state.topic = str(data.get("topic") or state.topic or "").strip() or state.topic
        if not state.caption:
            state.caption = str(data.get("caption") or "").strip() or None
        state.hashtags = normalize_hashtags(data.get("hashtags")) or state.hashtags
        if needs_media:
            state.media_prompt = str(data.get("media_prompt") or state.media_prompt or "").strip() or None
            state.optimized_media_prompt = str(data.get("optimized_media_prompt") or "").strip() or None
            state.negative_media_prompt = str(data.get("negative_media_prompt") or "").strip() or default_negative_prompt()
        return bool(state.topic and state.caption and (state.media_prompt or not needs_media))

    def _build_visual_prompt(self, state: PostState) -> None:
        base = state.media_prompt or state.topic or state.user_prompt
        style = state.visual_style or "realistic editorial"
        topic = state.topic or "social media post"
        detail = state.post_details or ""
        prompt_lower = f"{base} {detail}".lower()

        if "earring" in prompt_lower or "jewelry" in prompt_lower:
            subject = "macro close-up of a woman's ear wearing three silver earrings, sharp jewelry detail"
            camera = "85mm macro lens, shallow depth of field, crisp metal reflections"
        else:
            subject = f"photorealistic commercial lifestyle scene for {topic}"
            camera = "35mm full-frame lens, clean social media composition"

        state.negative_media_prompt = state.negative_media_prompt or default_negative_prompt()
        state.optimized_media_prompt = state.optimized_media_prompt or (
            f"{style} premium commercial photography. Subject: {subject}. "
            f"Brief: {base}. Camera: {camera}. Lighting: soft natural daylight, balanced exposure, "
            "realistic textures, no text overlay, no watermark, no logo."
        )
        state.visual_prompt_template = {
            "version": "single_agent_photo_v1",
            "topic": topic,
            "subject": subject,
            "style": style,
            "camera": camera,
            "final_prompt": state.optimized_media_prompt,
            "negative_prompt": state.negative_media_prompt,
        }
        state.add_log("single_agent", "visual_prompt", "Professional image brief prepared inside the single agent.")

    def _create_media(self, state: PostState) -> None:
        prompt = state.optimized_media_prompt or state.media_prompt or state.topic or state.user_prompt
        media_path = self.output_dir / "generated_post.jpg"

        if self.image_provider == "nvidia":
            self._create_with_nvidia(state, prompt, media_path)
        elif self.image_provider == "mistral":
            self._create_with_mistral(state, prompt, self.output_dir / "generated_post.png")
        elif self.image_provider == "auto":
            try:
                self._create_with_nvidia(state, prompt, media_path)
            except Exception as exc:
                state.add_log("single_agent", "warning", f"NVIDIA image failed in auto mode: {exc}")
                self._create_with_mistral(state, prompt, self.output_dir / "generated_post.png")
        else:
            self._create_with_pillow(state, media_path)

    def _create_with_nvidia(self, state: PostState, prompt: str, media_path: Path) -> None:
        if not self.nvidia_image_client:
            raise RuntimeError("NVIDIA image provider selected but NVIDIA client is not configured.")
        response = self.nvidia_image_client.generate_image(prompt, media_path, negative_prompt=state.negative_media_prompt)
        (self.output_dir / "single_agent.nvidia_image_response.json").write_text(json.dumps(response, indent=2), encoding="utf-8")
        self._set_media_state(state, media_path, provider="nvidia")
        state.add_log("single_agent", "media", f"Image generated with NVIDIA NIM and saved to {media_path}.")

    def _create_with_mistral(self, state: PostState, prompt: str, media_path: Path) -> None:
        if not self.mistral_image_client:
            raise RuntimeError("Mistral image provider selected but Mistral client is not configured.")
        response = self.mistral_image_client.generate_image(prompt, media_path)
        selected = Path(response.get("_mistral_image_selection", {}).get("output_path", str(media_path)))
        (self.output_dir / "single_agent.mistral_image_response.json").write_text(json.dumps(response, indent=2), encoding="utf-8")
        self._set_media_state(state, selected, provider="mistral")
        state.add_log("single_agent", "media", f"Image generated with Mistral image_generation and saved to {selected}.")

    def _create_with_pillow(self, state: PostState, media_path: Path) -> None:
        try:
            from PIL import Image, ImageDraw, ImageFont

            media_path.parent.mkdir(parents=True, exist_ok=True)
            width, height = 1080, 1080
            image = Image.new("RGB", (width, height), color=(18, 19, 19))
            draw = ImageDraw.Draw(image)
            title = (state.topic or "Single Agent Post").title()
            subtitle = state.media_prompt or state.optimized_media_prompt or "Single-agent generated visual placeholder"
            try:
                title_font = ImageFont.truetype("Arial.ttf", 68)
                body_font = ImageFont.truetype("Arial.ttf", 34)
            except OSError:
                title_font = ImageFont.load_default()
                body_font = ImageFont.load_default()
            draw.rectangle([(72, 72), (1008, 1008)], outline=(78, 222, 163), width=5)
            draw.rectangle([(120, 120), (960, 330)], fill=(32, 31, 32))
            draw.text((154, 182), title[:30], fill=(229, 226, 225), font=title_font)
            y = 410
            for line in textwrap.wrap(subtitle, width=42)[:7]:
                draw.text((140, y), line, fill=(198, 198, 202), font=body_font)
                y += 54
            image.save(media_path, "JPEG", quality=92)
        except Exception:
            media_path.write_bytes(base64.b64decode(FALLBACK_JPEG))
        self._set_media_state(state, media_path, provider="pillow")
        state.add_log("single_agent", "media", f"Placeholder image saved to {media_path}.")

    def _set_media_state(self, state: PostState, media_path: Path, *, provider: str) -> None:
        state.media_path = str(media_path)
        state.media_type = "image"
        state.has_media_file = media_path.exists()
        state.image_provider = provider

    def _quality_check(self, state: PostState, needs_media: bool) -> None:
        feedback = []
        caption = state.caption or ""
        lower_caption = caption.lower()
        if not caption.strip():
            feedback.append("Caption is missing.")
        if len(caption) > 2200:
            feedback.append("Caption is over the platform character limit.")
        if any(word in lower_caption for word in self.BANNED_WORDS):
            feedback.append("Caption contains unsafe terms.")
        if caption_copies_post_details(caption, state.post_details or ""):
            feedback.append("Caption copies creative brief details instead of polished social copy.")
        if needs_media and not state.has_media_file:
            feedback.append("Media file is required but missing.")
        media_prompt = state.optimized_media_prompt or state.media_prompt or ""
        if needs_media and state.topic and media_prompt and not topic_matches_media_prompt(state.topic, media_prompt):
            feedback.append("Media prompt does not clearly match the topic.")

        state.qa_status = "rejected" if feedback else "approved"
        state.qa_feedback = " ".join(feedback) if feedback else "Caption and media are ready for demo upload."
        state.add_log("single_agent", state.qa_status, state.qa_feedback)

    def _repair_once(self, state: PostState, needs_media: bool) -> None:
        state.add_log("single_agent", "repair", "Single agent is revising its own rejected output.")
        if "caption" in (state.qa_feedback or "").lower():
            state.caption = None
        if "media" in (state.qa_feedback or "").lower():
            state.optimized_media_prompt = None
            state.media_prompt = None
        self._create_content(state, needs_media)
        if needs_media and not state.optimized_media_prompt:
            self._build_visual_prompt(state)
        self._quality_check(state, needs_media)

    def _upload_to_demo(self, state: PostState) -> None:
        manifest_path = self.output_dir / "single_agent_upload_manifest.json"
        manifest = {
            "architecture": "single_agent",
            "platform": state.platform or "local_demo",
            "caption": state.caption,
            "media_path": state.media_path,
            "mode": "playwright" if self.use_playwright else "simulated",
        }
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

        if not self.use_playwright:
            state.browser_status = "success"
            state.browser_feedback = f"Simulated local demo upload. Manifest: {manifest_path}"
            state.add_log("single_agent", "browser", state.browser_feedback)
            return

        from config import DEMO_UPLOAD_PAGE

        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            state.browser_status = "error"
            state.browser_feedback = "Playwright is not installed. Run pip install -r requirements.txt and playwright install."
            state.add_log("single_agent", "error", state.browser_feedback)
            return

        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(DEMO_UPLOAD_PAGE.resolve().as_uri())
                page.fill("#caption", state.caption or "")
                if state.media_path:
                    page.set_input_files("#media", state.media_path)
                page.click("#share-button")
                status = page.locator("#status").inner_text(timeout=3000)
                browser.close()
        except Exception as exc:
            state.browser_status = "error"
            state.browser_feedback = f"Playwright demo upload failed: {exc}"
            state.add_log("single_agent", "error", state.browser_feedback)
            return

        state.browser_status = "success" if "success" in status.lower() else "error"
        state.browser_feedback = status
        state.add_log("single_agent", "browser", status)

    def _save_outputs(self, state: PostState) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / "single_agent_state.json").write_text(json.dumps(state.to_dict(), indent=2), encoding="utf-8")
        (self.output_dir / "single_agent_logs.json").write_text(json.dumps(state.logs, indent=2), encoding="utf-8")

    def _build_nvidia_image_client(self) -> Optional[NvidiaBuildClient]:
        if self.image_provider not in {"nvidia", "auto"}:
            return None
        if not NVIDIA_API_KEY and self.image_provider == "auto":
            return None
        return NvidiaBuildClient(model=NVIDIA_WRITER_MODEL)

    def _build_mistral_image_client(self) -> Optional[MistralImageClient]:
        if self.image_provider not in {"mistral", "auto"}:
            return None
        if not MISTRAL_API_KEY and self.image_provider == "auto":
            return None
        return MistralImageClient(model=MISTRAL_IMAGE_MODEL)


def extract_caption(prompt: str) -> Optional[str]:
    patterns = [
        r"(?:exact text|caption|post text|text)\s*:\s*['\"]([^'\"]{2,2200})['\"]",
        r"(?:use|share|post)\s+this\s+exact\s+text\s*['\"]([^'\"]{2,2200})['\"]",
    ]
    for pattern in patterns:
        match = re.search(pattern, prompt, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


def extract_basic_topic(prompt: str) -> Optional[str]:
    lower = prompt.lower()
    if "doğa spor" in lower:
        return "doğa sporları ekipmanları"
    for pattern in (r"\babout\s+(.+?)(?:\s+with\b|\.|,|$)", r"\bfor\s+(?:a|an)?\s*(.+?)\s+post\b"):
        match = re.search(pattern, prompt, flags=re.IGNORECASE)
        if match:
            return " ".join(match.group(1).strip(" .,!?'\"").split())[:80]
    return None


def extract_platform(lower_prompt: str) -> Optional[str]:
    for platform in ("instagram", "tiktok", "linkedin", "facebook", "twitter"):
        if platform in lower_prompt:
            return "x" if platform == "twitter" else platform
    if re.search(r"\bx\b", lower_prompt):
        return "x"
    if "local demo" in lower_prompt or "local_demo" in lower_prompt:
        return "local_demo"
    return None


def should_create_media(lower: str, state: PostState) -> bool:
    if state.has_media_file or "text only" in lower or "no image" in lower or "without image" in lower:
        return False
    media_words = ("picture", "image", "photo", "visual", "video", "reel", "görsel", "fotoğraf", "resim")
    return any(word in lower for word in media_words) or should_upload(lower)


def should_upload(lower: str) -> bool:
    if "draft only" in lower or "do not upload" in lower or "no upload" in lower:
        return False
    return any(word in lower for word in ("upload", "share", "publish")) or "post" in lower


def normalize_hashtags(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    tags = []
    for item in value:
        tag = str(item).strip()
        if not tag:
            continue
        tags.append(tag if tag.startswith("#") else f"#{tag}")
    return tags[:8]


def default_negative_prompt() -> str:
    return (
        "text, typography, caption, logo, watermark, signature, blurry, low resolution, distorted anatomy, "
        "extra limbs, plastic skin, cartoon, illustration, generic stock photo"
    )


FALLBACK_JPEG = (
    "/9j/4AAQSkZJRgABAQAASABIAAD/4QBMRXhpZgAATU0AKgAAAAgAAYdpAAQAAAABAAAAGgAAAAAAA6ABAAMAAAABAAEAAKACAAQAAAABAAAAAaADAAQAAAABAAAAAQAAAAD/7QA4UGhvdG9zaG9wIDMuMAA4QklNBAQAAAAAAAA4QklNBCUAAAAAABDUHYzZjwCyBOmACZjs+EJ+/8AAEQgAAQABAwEiAAIRAQMRAf/EAB8AAAEFAQEBAQEBAAAAAAAAAAABAgMEBQYHCAkKC//EALUQAAIBAwMCBAMFBQQEAAABfQECAwAEEQUSITFBBhNRYQcicRQygZGhCCNCscEVUtHwJDNicoIJChYXGBkaJSYnKCkqNDU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6g4SFhoeIiYqSk5SVlpeYmZqio6Slpqeoqaqys7S1tre4ubrCw8TFxsfIycrS09TV1tfY2drh4uPk5ebn6Onq8fLz9PX29/j5+v/EAB8BAAMBAQEBAQEBAQEAAAAAAAABAgMEBQYHCAkKC//EALURAAIBAgQEAwQHBQQEAAECdwABAgMRBAUhMQYSQVEHYXETIjKBCBRCkaGxwQkjM1LwFWJy0QoWJDThJfEXGBkaJicoKSo1Njc4OTpDREVGR0hJSlNUVVZXWFlaY2RlZmdoaWpzdHV2d3h5eoKDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uLj5OXm5+jp6vLz9PX29/j5+v/bAEMAAgICAgICAwICAwUDAwMFBgUFBQUGCAYGBgYGCAoICAgICAgKCgoKCgoKCgwMDAwMDA4ODg4ODw8PDw8PDw8PD//bAEMBAgICBAQEBwQEBxALCQsQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEP/dAAQAAf/aAAwDAQACEQMRAD8A/fyiiigD/9k="
)


def single_agent_summary(state: PostState, output_dir: str, provider: str) -> dict:
    data = {
        "architecture": "single_agent",
        "can_continue": state.can_continue,
        "routing_plan": state.routing_plan,
        "topic": state.topic,
        "post_details": state.post_details,
        "platform": state.platform,
        "caption": state.caption,
        "media_prompt": state.media_prompt,
        "optimized_media_prompt": state.optimized_media_prompt,
        "negative_media_prompt": state.negative_media_prompt,
        "visual_prompt_template": state.visual_prompt_template,
        "media_path": state.media_path,
        "image_provider": state.image_provider,
        "qa_status": state.qa_status,
        "qa_feedback": state.qa_feedback,
        "browser_status": state.browser_status,
        "browser_feedback": state.browser_feedback,
        "output_dir": str(Path(output_dir).resolve()),
    }
    if provider == "nvidia":
        data["nvidia"] = {
            "default_chat_model": NVIDIA_MODEL,
            "writer_model": NVIDIA_WRITER_MODEL,
            "chat_endpoint": f"{NVIDIA_BASE_URL.rstrip('/')}/chat/completions",
            "image_model": NVIDIA_IMAGE_MODEL,
            "image_endpoint": NVIDIA_IMAGE_ENDPOINT or f"{NVIDIA_IMAGE_BASE_URL.rstrip('/')}/{NVIDIA_IMAGE_MODEL}",
            "image_candidates": NVIDIA_IMAGE_CANDIDATES,
        }
    return data
