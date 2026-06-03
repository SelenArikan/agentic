from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents.browser_operator import BrowserOperatorAgent
from models import PostState


def main() -> None:
    parser = argparse.ArgumentParser(description="Upload a saved state to the local demo page.")
    parser.add_argument("state_json", help="Path to outputs/state.json")
    parser.add_argument("--use-playwright", action="store_true")
    args = parser.parse_args()

    data = json.loads(Path(args.state_json).read_text(encoding="utf-8"))
    state = PostState(**{key: value for key, value in data.items() if key in PostState.__dataclass_fields__})
    output_dir = Path(args.state_json).resolve().parent
    BrowserOperatorAgent().upload_to_demo(state, output_dir, use_playwright=args.use_playwright)
    print(json.dumps({"browser_status": state.browser_status, "browser_feedback": state.browser_feedback}, indent=2))


if __name__ == "__main__":
    main()
