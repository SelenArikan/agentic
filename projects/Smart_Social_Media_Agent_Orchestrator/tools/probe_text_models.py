from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from providers import NvidiaBuildClient


DEFAULT_MODELS = [
    "google/gemma-4-31b-it",
    "google/gemma-3-27b-it",
    "google/gemma-3n-e4b-it",
    "google/gemma-3n-e2b-it",
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Probe NVIDIA text/chat models.")
    parser.add_argument("--models", default=",".join(DEFAULT_MODELS))
    args = parser.parse_args()

    results = []
    for model in [item.strip() for item in args.models.split(",") if item.strip()]:
        client = NvidiaBuildClient(model=model)
        try:
            text = client.chat_text(
                [{"role": "user", "content": "Reply with exactly: ok"}],
                temperature=0,
                max_tokens=16,
            )
            results.append({"model": model, "status": "success", "response": text.strip()})
        except Exception as exc:
            results.append({"model": model, "status": "error", "error": str(exc)})

    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
