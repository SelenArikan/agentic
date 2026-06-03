from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

SINGLE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = SINGLE_ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import IMAGE_PROVIDER
from models import PostState
from single_agent import SINGLE_OUTPUT_DIR, SingleSocialMediaAgent, single_agent_summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Single-agent social media post generator")
    parser.add_argument("prompt", nargs="*", help="User prompt, for example: Make a post about Pilates.")
    parser.add_argument("--provider", choices=["mock", "nvidia"], default="mock")
    parser.add_argument("--image-provider", choices=["nvidia", "mistral", "pillow", "auto"], default=IMAGE_PROVIDER)
    parser.add_argument("--output-dir", default=str(SINGLE_OUTPUT_DIR))
    parser.add_argument("--platform", default="local_demo")
    parser.add_argument("--visual-style", default="realistic")
    parser.add_argument("--post-details", default="")
    parser.add_argument("--use-playwright", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    prompt = " ".join(args.prompt).strip() or input("User prompt: ").strip()
    state = PostState(user_prompt=prompt)
    state.platform = args.platform or "local_demo"
    state.visual_style = args.visual_style or None
    state.post_details = args.post_details or None

    agent = SingleSocialMediaAgent(
        provider=args.provider,
        image_provider=args.image_provider,
        output_dir=Path(args.output_dir),
        use_playwright=args.use_playwright,
    )
    state = agent.run(state)
    print(json.dumps(single_agent_summary(state, args.output_dir, args.provider), indent=2))


if __name__ == "__main__":
    main()
