from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional
import urllib.error
import urllib.request

from config import MISTRAL_API_KEY, MISTRAL_BASE_URL, MISTRAL_IMAGE_MODEL


class MistralImageError(RuntimeError):
    """Raised when Mistral image generation cannot produce a downloadable file."""


class MistralImageClient:
    """Mistral image generation via Conversations API built-in image_generation tool."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: int = 120,
    ) -> None:
        self.api_key = api_key or MISTRAL_API_KEY
        self.base_url = (base_url or MISTRAL_BASE_URL).rstrip("/")
        self.model = model or MISTRAL_IMAGE_MODEL
        self.timeout = timeout
        if not self.api_key:
            raise MistralImageError("MISTRAL_API_KEY is required for Mistral image generation.")

    def generate_image(self, prompt: str, output_path: Path) -> Dict[str, Any]:
        payload = {
            "model": self.model,
            "instructions": (
                "Use the image_generation tool whenever the input requests an image. "
                "Generate one polished social media image and avoid adding text overlays."
            ),
            "inputs": (
                "Generate exactly one high-quality social media image from this prompt. "
                "Do not include text overlays, watermarks, logos, or identifiable real people unless explicitly requested.\n\n"
                f"Prompt: {prompt}"
            ),
            "tools": [{"type": "image_generation"}],
            "store": False,
            "stream": False,
            "completion_args": {
                "temperature": 0.3,
                "top_p": 0.95,
            },
        }
        response = self.post_json(f"{self.base_url}/conversations", payload)
        file_id = find_tool_file_id(response)
        if not file_id:
            raise MistralImageError(f"Mistral response did not include an image file_id. Keys: {list(response)[:20]}")

        file_bytes = self.download_file(file_id)
        actual_output_path = output_path.with_suffix(detect_image_suffix(file_bytes, output_path.suffix))
        actual_output_path.parent.mkdir(parents=True, exist_ok=True)
        actual_output_path.write_bytes(file_bytes)
        response["_mistral_image_selection"] = {
            "model": self.model,
            "endpoint": f"{self.base_url}/conversations",
            "file_id": file_id,
            "download_endpoint": f"{self.base_url}/files/{file_id}/content",
            "output_path": str(actual_output_path),
        }
        return response

    def post_json(self, url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise MistralImageError(f"Mistral API HTTP {exc.code}: {body}") from exc
        except TimeoutError as exc:
            raise MistralImageError("Mistral API request timed out.") from exc
        except urllib.error.URLError as exc:
            raise MistralImageError(f"Mistral API connection failed: {exc.reason}") from exc

        try:
            return json.loads(body)
        except json.JSONDecodeError as exc:
            raise MistralImageError(f"Expected JSON from Mistral API, got: {body[:500]}") from exc

    def download_file(self, file_id: str) -> bytes:
        request = urllib.request.Request(
            f"{self.base_url}/files/{file_id}/content",
            headers={"Authorization": f"Bearer {self.api_key}"},
            method="GET",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise MistralImageError(f"Mistral file download HTTP {exc.code}: {body}") from exc
        except TimeoutError as exc:
            raise MistralImageError("Mistral file download timed out.") from exc
        except urllib.error.URLError as exc:
            raise MistralImageError(f"Mistral file download failed: {exc.reason}") from exc


def find_tool_file_id(value: Any) -> Optional[str]:
    if isinstance(value, dict):
        if value.get("type") == "tool_file" and value.get("file_id"):
            return str(value["file_id"])
        if value.get("tool") == "image_generation" and value.get("file_id"):
            return str(value["file_id"])
        for item in value.values():
            found = find_tool_file_id(item)
            if found:
                return found
    if isinstance(value, list):
        for item in value:
            found = find_tool_file_id(item)
            if found:
                return found
    return None


def detect_image_suffix(file_bytes: bytes, fallback: str = ".png") -> str:
    if file_bytes.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if file_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if file_bytes.startswith(b"RIFF") and file_bytes[8:12] == b"WEBP":
        return ".webp"
    if file_bytes.startswith(b"GIF87a") or file_bytes.startswith(b"GIF89a"):
        return ".gif"
    return fallback if fallback.startswith(".") else f".{fallback}"
