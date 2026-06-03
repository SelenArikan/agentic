from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

import base64
from pathlib import Path

from config import (
    NVIDIA_API_KEY,
    NVIDIA_BASE_URL,
    NVIDIA_IMAGE_BASE_URL,
    NVIDIA_IMAGE_ASPECT_RATIO,
    NVIDIA_IMAGE_CANDIDATES,
    NVIDIA_IMAGE_CFG_SCALE,
    NVIDIA_IMAGE_ENDPOINT,
    NVIDIA_IMAGE_MODEL,
    NVIDIA_IMAGE_NEGATIVE_PROMPT,
    NVIDIA_IMAGE_STEPS,
    NVIDIA_MODEL,
)


class NvidiaBuildError(RuntimeError):
    """Raised when NVIDIA Build cannot return a valid response."""


class NvidiaBuildClient:
    """Minimal OpenAI-compatible NVIDIA Build client.

    Official NIM docs expose chat completions at:
    https://integrate.api.nvidia.com/v1/chat/completions
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        image_base_url: Optional[str] = None,
        image_endpoint: Optional[str] = None,
        image_model: Optional[str] = None,
        timeout: int = 60,
    ) -> None:
        self.api_key = api_key or NVIDIA_API_KEY
        self.base_url = (base_url or NVIDIA_BASE_URL).rstrip("/")
        self.model = model or NVIDIA_MODEL
        self.image_base_url = (image_base_url or NVIDIA_IMAGE_BASE_URL).rstrip("/")
        self.image_endpoint = image_endpoint or NVIDIA_IMAGE_ENDPOINT
        self.image_model = image_model or NVIDIA_IMAGE_MODEL
        self.timeout = timeout
        if not self.api_key:
            raise NvidiaBuildError("NVIDIA_API_KEY is required for provider='nvidia'.")

    def chat_text(
        self,
        messages: List[Dict[str, str]],
        *,
        temperature: float = 0.2,
        max_tokens: int = 800,
    ) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
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
            raise NvidiaBuildError(f"NVIDIA API HTTP {exc.code}: {body}") from exc
        except TimeoutError as exc:
            raise NvidiaBuildError("NVIDIA API request timed out.") from exc
        except urllib.error.URLError as exc:
            raise NvidiaBuildError(f"NVIDIA API connection failed: {exc.reason}") from exc

        try:
            data = json.loads(body)
            return data["choices"][0]["message"]["content"]
        except (json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
            raise NvidiaBuildError(f"Unexpected NVIDIA API response: {body[:500]}") from exc

    def chat_json(
        self,
        messages: List[Dict[str, str]],
        *,
        temperature: float = 0.1,
        max_tokens: int = 800,
    ) -> Dict[str, Any]:
        json_messages = [
            {"role": "system", "content": "Return only valid JSON. Do not include Markdown fences."},
            *messages,
        ]
        raw = self.chat_text(json_messages, temperature=temperature, max_tokens=max_tokens)
        return extract_json_object(raw)

    def generate_image(
        self,
        prompt: str,
        output_path: Path,
        *,
        height: int = 1024,
        width: int = 1024,
        steps: int = NVIDIA_IMAGE_STEPS,
        seed: int = 0,
        negative_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        attempts = self._image_attempts()
        errors: List[str] = []
        data: Optional[Dict[str, Any]] = None
        image_b64: Optional[str] = None
        used_model = self.image_model
        used_endpoint = self.image_endpoint or f"{self.image_base_url}/{self.image_model}"

        for model, endpoint in attempts:
            self.image_model = model
            payload = self._image_payload(
                prompt,
                endpoint,
                height=height,
                width=width,
                steps=steps,
                seed=seed,
                negative_prompt=negative_prompt,
            )
            try:
                data = self.post_json(endpoint, payload)
                image_b64 = find_base64_image(data)
                if not image_b64:
                    raise NvidiaBuildError(f"response did not contain a base64 image. Keys: {list(data)[:20]}")
                used_model = model
                used_endpoint = endpoint
                break
            except Exception as exc:
                errors.append(f"{model} @ {endpoint}: {exc}")

        if not image_b64 or data is None:
            raise NvidiaBuildError("All NVIDIA image candidates failed:\n" + "\n".join(errors))

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(base64.b64decode(image_b64))
        data.setdefault("_nvidia_image_selection", {})
        data["_nvidia_image_selection"] = {
            "model": used_model,
            "endpoint": used_endpoint,
            "failed_attempts": errors,
        }
        return data

    def _image_attempts(self) -> List[tuple[str, str]]:
        if self.image_endpoint:
            return [(self.image_model, self.image_endpoint)]
        models = NVIDIA_IMAGE_CANDIDATES if self.image_model == "auto" else [self.image_model]
        return [(model, f"{self.image_base_url}/{model}") for model in models]

    def _image_payload(
        self,
        prompt: str,
        endpoint: str,
        *,
        height: int,
        width: int,
        steps: int,
        seed: int,
        negative_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        negative = negative_prompt or NVIDIA_IMAGE_NEGATIVE_PROMPT
        if "flux.2-klein-4b" in self.image_model:
            return {
                "prompt": prompt,
                "seed": seed,
                "steps": max(1, steps),
            }
        if "flux.1-schnell" in self.image_model:
            return {
                "prompt": prompt,
                "height": height,
                "width": width,
                "cfg_scale": 0,
                "mode": "base",
                "samples": 1,
                "seed": seed,
                "steps": min(max(1, steps), 4),
            }
        if "stable-diffusion-3-medium" in self.image_model:
            return {
                "prompt": prompt,
                "negative_prompt": negative,
                "aspect_ratio": NVIDIA_IMAGE_ASPECT_RATIO,
                "cfg_scale": min(max(NVIDIA_IMAGE_CFG_SCALE, 0), 9),
                "mode": "text-to-image",
                "model": "sd3",
                "output_format": "jpeg",
                "seed": seed,
                "steps": min(max(steps, 5), 100),
            }
        if "stable-diffusion-3.5-large" in self.image_model or endpoint.rstrip("/").endswith("/v1/infer"):
            return {
                "prompt": prompt,
                "mode": "base",
                "seed": seed,
                "steps": max(1, steps),
            }
        if "stable-diffusion-xl" in self.image_model or "bria" in self.image_model or "consistory" in self.image_model:
            return {
                "prompt": prompt,
                "negative_prompt": negative,
                "cfg_scale": min(max(NVIDIA_IMAGE_CFG_SCALE, 0), 9),
                "sampler": "K_DPM_2_ANCESTRAL",
                "seed": seed,
                "steps": min(max(steps, 5), 100),
            }
        return {
            "prompt": prompt,
            "height": height,
            "width": width,
            "cfg_scale": 0,
            "mode": "base",
            "samples": 1,
            "seed": seed,
            "steps": min(max(1, steps), 4),
        }

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
            raise NvidiaBuildError(f"NVIDIA API HTTP {exc.code}: {body}") from exc
        except TimeoutError as exc:
            raise NvidiaBuildError("NVIDIA API request timed out.") from exc
        except urllib.error.URLError as exc:
            raise NvidiaBuildError(f"NVIDIA API connection failed: {exc.reason}") from exc

        try:
            return json.loads(body)
        except json.JSONDecodeError as exc:
            raise NvidiaBuildError(f"Expected JSON from NVIDIA API, got: {body[:500]}") from exc


def extract_json_object(raw: str) -> Dict[str, Any]:
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
    if text.endswith("```"):
        text = text.rsplit("\n", 1)[0]
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise NvidiaBuildError(f"Expected JSON object, got: {raw[:300]}")
    return json.loads(text[start : end + 1])


def find_base64_image(value: Any) -> Optional[str]:
    if isinstance(value, str):
        candidate = value.split(",", 1)[1] if value.startswith("data:image") and "," in value else value
        compact = "".join(candidate.split())
        if len(compact) < 200:
            return None
        try:
            decoded = base64.b64decode(compact, validate=True)
        except Exception:
            return None
        if decoded.startswith((b"\xff\xd8\xff", b"\x89PNG", b"RIFF", b"GIF")):
            return compact
        return None

    if isinstance(value, list):
        for item in value:
            found = find_base64_image(item)
            if found:
                return found
        return None

    if isinstance(value, dict):
        preferred_keys = ("b64_json", "base64", "image", "data", "artifact")
        for key in preferred_keys:
            if key in value:
                found = find_base64_image(value[key])
                if found:
                    return found
        for item in value.values():
            found = find_base64_image(item)
            if found:
                return found
    return None
