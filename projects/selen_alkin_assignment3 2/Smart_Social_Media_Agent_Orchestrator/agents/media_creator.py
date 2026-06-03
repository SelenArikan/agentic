from __future__ import annotations

import base64
import json
import textwrap
from pathlib import Path
from typing import Optional

from config import IMAGE_PROVIDER, MISTRAL_IMAGE_FALLBACK_TO_PILLOW, NVIDIA_IMAGE_FALLBACK_TO_PILLOW
from models import PostState
from providers import MistralImageClient, NvidiaBuildClient


class MediaCreatorAgent:
    """Creates a local placeholder image for the MVP."""

    FALLBACK_JPEG = (
        "/9j/4AAQSkZJRgABAQAASABIAAD/4QBMRXhpZgAATU0AKgAAAAgAAYdpAAQAAAABAAAAGgAAAAAAA6ABAAMAAAABAAEAAKACAAQAAAABAAAAAaADAAQAAAABAAAAAQAAAAD/7QA4UGhvdG9zaG9wIDMuMAA4QklNBAQAAAAAAAA4QklNBCUAAAAAABDUHYzZjwCyBOmACZjs+EJ+/8AAEQgAAQABAwEiAAIRAQMRAf/EAB8AAAEFAQEBAQEBAAAAAAAAAAABAgMEBQYHCAkKC//EALUQAAIBAwMCBAMFBQQEAAABfQECAwAEEQUSITFBBhNRYQcicRQygZGhCCNCscEVUtHwJDNicoIJChYXGBkaJSYnKCkqNDU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6g4SFhoeIiYqSk5SVlpeYmZqio6Slpqeoqaqys7S1tre4ubrCw8TFxsfIycrS09TV1tfY2drh4uPk5ebn6Onq8fLz9PX29/j5+v/EAB8BAAMBAQEBAQEBAQEAAAAAAAABAgMEBQYHCAkKC//EALURAAIBAgQEAwQHBQQEAAECdwABAgMRBAUhMQYSQVEHYXETIjKBCBRCkaGxwQkjM1LwFWJy0QoWJDThJfEXGBkaJicoKSo1Njc4OTpDREVGR0hJSlNUVVZXWFlaY2RlZmdoaWpzdHV2d3h5eoKDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uLj5OXm5+jp6vLz9PX29/j5+v/bAEMAAgICAgICAwICAwUDAwMFBgUFBQUGCAYGBgYGCAoICAgICAgKCgoKCgoKCgwMDAwMDA4ODg4ODw8PDw8PDw8PD//bAEMBAgICBAQEBwQEBxALCQsQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEP/dAAQAAf/aAAwDAQACEQMRAD8A/fyiiigD/9k="
    )

    def __init__(
        self,
        nvidia_client: Optional[NvidiaBuildClient] = None,
        mistral_client: Optional[MistralImageClient] = None,
        *,
        image_provider: str = IMAGE_PROVIDER,
        strict_api: bool = False,
    ) -> None:
        self.nvidia_client = nvidia_client
        self.mistral_client = mistral_client
        self.image_provider = image_provider
        self.strict_api = strict_api

    def create_media(self, state: PostState, output_dir: Path) -> PostState:
        output_dir.mkdir(parents=True, exist_ok=True)
        state.image_provider = self.image_provider
        media_path = output_dir / "generated_post.jpg"
        prompt = self._effective_prompt(state)

        if self.image_provider == "nvidia":
            return self._create_with_nvidia_or_fallback(state, output_dir, media_path, prompt)

        if self.image_provider == "mistral":
            return self._create_with_mistral_or_fallback(state, output_dir, output_dir / "generated_post.png", prompt)

        if self.image_provider == "auto":
            try:
                return self._create_with_nvidia_or_fallback(state, output_dir, media_path, prompt, allow_pillow_fallback=False)
            except Exception as nvidia_exc:
                state.add_log("media_creator", "warning", f"NVIDIA image provider failed in auto mode: {nvidia_exc}")
                try:
                    return self._create_with_mistral_or_fallback(
                        state,
                        output_dir,
                        output_dir / "generated_post.png",
                        prompt,
                        allow_pillow_fallback=False,
                    )
                except Exception as mistral_exc:
                    state.add_log("media_creator", "warning", f"Mistral image provider failed in auto mode: {mistral_exc}")
                    if self.strict_api:
                        raise

        return self._create_with_pillow_or_fallback(state, output_dir, media_path)

    def _create_with_nvidia_or_fallback(
        self,
        state: PostState,
        output_dir: Path,
        media_path: Path,
        prompt: str,
        *,
        allow_pillow_fallback: bool = NVIDIA_IMAGE_FALLBACK_TO_PILLOW,
    ) -> PostState:
        if not self.nvidia_client:
            raise RuntimeError("NVIDIA image provider selected but NVIDIA client is not configured.")
        try:
            response = self.nvidia_client.generate_image(prompt, media_path, negative_prompt=state.negative_media_prompt)
            (output_dir / "generated_post.nvidia_response.json").write_text(
                json.dumps(response, indent=2),
                encoding="utf-8",
            )
            self._write_prompt_metadata(state, output_dir, provider="nvidia-nim")
            self._set_media_state(state, media_path, provider="nvidia")
            state.add_log("media_creator", "success", f"Image generated with NVIDIA NIM and saved to {media_path}.")
            return state
        except Exception as exc:
            state.add_log("media_creator", "error", f"NVIDIA image generation failed: {exc}")
            if not allow_pillow_fallback:
                raise
            return self._create_with_pillow_or_fallback(state, output_dir, media_path)

    def _create_with_mistral_or_fallback(
        self,
        state: PostState,
        output_dir: Path,
        media_path: Path,
        prompt: str,
        *,
        allow_pillow_fallback: bool = MISTRAL_IMAGE_FALLBACK_TO_PILLOW,
    ) -> PostState:
        if not self.mistral_client:
            raise RuntimeError("Mistral image provider selected but Mistral client is not configured.")
        try:
            response = self.mistral_client.generate_image(prompt, media_path)
            selected_media_path = Path(
                response.get("_mistral_image_selection", {}).get("output_path", str(media_path))
            )
            (output_dir / "generated_post.mistral_response.json").write_text(
                json.dumps(response, indent=2),
                encoding="utf-8",
            )
            self._write_prompt_metadata(state, output_dir, provider="mistral-image-generation")
            self._set_media_state(state, selected_media_path, provider="mistral")
            state.add_log(
                "media_creator",
                "success",
                f"Image generated with Mistral image_generation and saved to {selected_media_path}.",
            )
            return state
        except Exception as exc:
            state.add_log("media_creator", "error", f"Mistral image generation failed: {exc}")
            if not allow_pillow_fallback:
                raise
            return self._create_with_pillow_or_fallback(state, output_dir, output_dir / "generated_post.jpg")

    def _create_with_pillow_or_fallback(self, state: PostState, output_dir: Path, media_path: Path) -> PostState:
        try:
            self._create_with_pillow(state, media_path)
        except Exception as exc:
            if self.strict_api:
                raise
            media_path.write_bytes(base64.b64decode(self.FALLBACK_JPEG))
            state.add_log("media_creator", "warning", f"Pillow generation failed; used fallback JPEG: {exc}")

        self._write_prompt_metadata(state, output_dir, provider="pillow")
        self._set_media_state(state, media_path, provider="pillow")
        state.add_log("media_creator", "success", f"Placeholder image saved to {media_path}.")
        return state

    def _set_media_state(self, state: PostState, media_path: Path, *, provider: str) -> None:
        state.media_path = str(media_path)
        state.media_type = "image"
        state.has_media_file = media_path.exists()
        state.image_provider = provider

    def _write_prompt_metadata(self, state: PostState, output_dir: Path, *, provider: str) -> None:
        prompt_path = output_dir / "generated_post.prompt.json"
        prompt_path.write_text(
            json.dumps(
                {
                    "media_prompt": state.media_prompt,
                    "optimized_media_prompt": state.optimized_media_prompt,
                    "negative_media_prompt": state.negative_media_prompt,
                    "visual_prompt_template": state.visual_prompt_template,
                    "topic": state.topic,
                    "provider": provider,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    def _effective_prompt(self, state: PostState) -> str:
        prompt = state.optimized_media_prompt or state.media_prompt or state.topic or state.user_prompt
        if state.negative_media_prompt and "avoid:" not in prompt.lower():
            return f"{prompt}\n\nAvoid: {state.negative_media_prompt}"
        return prompt

    def _create_with_pillow(self, state: PostState, media_path: Path) -> None:
        from PIL import Image, ImageDraw, ImageFont

        width, height = 1080, 1080
        image = Image.new("RGB", (width, height), color=(244, 239, 229))
        draw = ImageDraw.Draw(image)

        title = (state.topic or "Social Post").title()
        subtitle = state.media_prompt or "Generated social media placeholder"
        hashtags = " ".join(state.hashtags[:4])

        try:
            title_font = ImageFont.truetype("Arial.ttf", 72)
            body_font = ImageFont.truetype("Arial.ttf", 34)
        except OSError:
            title_font = ImageFont.load_default()
            body_font = ImageFont.load_default()

        draw.rectangle([(80, 80), (1000, 1000)], outline=(35, 66, 54), width=6)
        draw.rectangle([(120, 120), (960, 360)], fill=(35, 66, 54))
        draw.text((160, 190), title[:28], fill=(255, 255, 255), font=title_font)

        y = 430
        for line in textwrap.wrap(subtitle, width=42)[:7]:
            draw.text((150, y), line, fill=(40, 40, 40), font=body_font)
            y += 52

        if hashtags:
            draw.text((150, 890), hashtags, fill=(35, 66, 54), font=body_font)

        image.save(media_path, "JPEG", quality=92)
