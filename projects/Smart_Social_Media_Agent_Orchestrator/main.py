from __future__ import annotations

import argparse
import json
from pathlib import Path

from agents import TaskManagerAgent
from config import (
    IMAGE_PROVIDER,
    MAX_CLARIFICATION_QUESTIONS,
    MISTRAL_BASE_URL,
    MISTRAL_IMAGE_MODEL,
    NVIDIA_BASE_URL,
    NVIDIA_IMAGE_BASE_URL,
    NVIDIA_IMAGE_CANDIDATES,
    NVIDIA_IMAGE_ENDPOINT,
    NVIDIA_IMAGE_MODEL,
    NVIDIA_MODEL,
    NVIDIA_QA_MODEL,
    NVIDIA_RESEARCH_MODEL,
    NVIDIA_WRITER_MODEL,
    OUTPUT_DIR,
)
from models import PostState


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smart Social Media Agent Orchestrator")
    parser.add_argument("prompt", nargs="*", help="User prompt, for example: Make a post about Pilates.")
    parser.add_argument("--provider", choices=["mock", "nvidia"], default="mock")
    parser.add_argument("--image-provider", choices=["nvidia", "mistral", "pillow", "auto"], default=IMAGE_PROVIDER)
    parser.add_argument("--output-dir", default=str(OUTPUT_DIR))
    parser.add_argument("--use-playwright", action="store_true", help="Use Playwright against browser/demo_upload_page.html.")
    parser.add_argument("--demo-defaults", action="store_true", help="Answer clarification questions with safe demo defaults.")
    parser.add_argument("--no-interactive", action="store_true", help="Return the first clarification question instead of prompting.")
    parser.add_argument("--max-clarifications", type=int, default=MAX_CLARIFICATION_QUESTIONS)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    prompt = " ".join(args.prompt).strip()
    if not prompt:
        prompt = input("User prompt: ").strip()

    manager = TaskManagerAgent(
        provider=args.provider,
        image_provider=args.image_provider,
        output_dir=Path(args.output_dir),
        use_playwright=args.use_playwright,
        max_clarifications=args.max_clarifications,
    )
    state = PostState(user_prompt=prompt)

    ask_user = None
    if args.demo_defaults:
        ask_user = demo_default_answer
    elif not args.no_interactive:
        ask_user = lambda question: input(f"{question}\n> ").strip()

    state = manager.run(state, ask_user=ask_user)
    print(json.dumps(summary(state, args.output_dir, args.provider), indent=2))


def demo_default_answer(question: str) -> str:
    lower = question.lower()
    if "which platform" in lower:
        return "local demo"
    if "demo upload page" in lower:
        return "yes"
    if "visual style" in lower:
        return "fitness-focused"
    if "exact text" in lower:
        return "Join my class!"
    if "topic" in lower:
        return "Pilates"
    if "caption, the image, or both" in lower:
        return "both"
    return "local demo"


def summary(state: PostState, output_dir: str, provider: str) -> dict:
    data = {
        "can_continue": state.can_continue,
        "needs_clarification": state.needs_clarification,
        "clarification_question": state.clarification_question,
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
            "research_model": NVIDIA_RESEARCH_MODEL,
            "writer_model": NVIDIA_WRITER_MODEL,
            "qa_model": NVIDIA_QA_MODEL,
            "chat_endpoint": f"{NVIDIA_BASE_URL.rstrip('/')}/chat/completions",
            "image_model": NVIDIA_IMAGE_MODEL,
            "image_endpoint": NVIDIA_IMAGE_ENDPOINT or f"{NVIDIA_IMAGE_BASE_URL.rstrip('/')}/{NVIDIA_IMAGE_MODEL}",
            "image_candidates": NVIDIA_IMAGE_CANDIDATES,
        }
    if state.image_provider == "mistral":
        data["mistral"] = {
            "image_model": MISTRAL_IMAGE_MODEL,
            "conversation_endpoint": f"{MISTRAL_BASE_URL.rstrip('/')}/conversations",
            "files_endpoint": f"{MISTRAL_BASE_URL.rstrip('/')}/files/{{file_id}}/content",
        }
    return data


if __name__ == "__main__":
    main()
