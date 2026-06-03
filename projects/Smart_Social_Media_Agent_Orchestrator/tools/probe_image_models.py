from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import NVIDIA_IMAGE_BASE_URL, NVIDIA_IMAGE_CANDIDATES
from providers import NvidiaBuildClient


def main() -> None:
    parser = argparse.ArgumentParser(description="Probe NVIDIA image generation endpoints.")
    parser.add_argument("--prompt", default="A clean Pilates studio social media image, natural light, no text overlay")
    parser.add_argument("--output-dir", default=str(PROJECT_ROOT / "outputs" / "image_probe"))
    parser.add_argument("--models", default=",".join(NVIDIA_IMAGE_CANDIDATES))
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    models = [item.strip() for item in args.models.split(",") if item.strip()]
    results = []

    for model in models:
        client = NvidiaBuildClient(image_model=model)
        target = output_dir / f"{safe_name(model)}.jpg"
        endpoint = f"{NVIDIA_IMAGE_BASE_URL.rstrip('/')}/{model}"
        try:
            data = client.generate_image(args.prompt, target)
            results.append(
                {
                    "model": model,
                    "endpoint": endpoint,
                    "status": "success",
                    "image_path": str(target),
                    "selection": data.get("_nvidia_image_selection"),
                }
            )
        except Exception as exc:
            results.append(
                {
                    "model": model,
                    "endpoint": endpoint,
                    "status": "error",
                    "error": str(exc),
                }
            )

    print(json.dumps(results, indent=2))


def safe_name(model: str) -> str:
    return model.replace("/", "__").replace(".", "_")


if __name__ == "__main__":
    main()
