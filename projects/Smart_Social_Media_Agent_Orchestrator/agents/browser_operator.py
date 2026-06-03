from __future__ import annotations

import json
from pathlib import Path

from config import DEMO_UPLOAD_PAGE
from models import PostState


class BrowserOperatorAgent:
    """Uploads to the local demo page with Playwright, or simulates it for tests."""

    def upload_to_demo(self, state: PostState, output_dir: Path, *, use_playwright: bool = False) -> PostState:
        output_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = output_dir / "browser_upload_manifest.json"
        manifest = {
            "platform": state.platform or "local_demo",
            "caption": state.caption,
            "media_path": state.media_path,
            "demo_page": str(DEMO_UPLOAD_PAGE),
            "mode": "playwright" if use_playwright else "simulated",
        }
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

        if not use_playwright:
            state.browser_status = "success"
            state.browser_feedback = f"Simulated local demo upload. Manifest: {manifest_path}"
            state.add_log("browser", "success", state.browser_feedback)
            return state

        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            state.browser_status = "error"
            state.browser_feedback = "Playwright is not installed. Run pip install -r requirements.txt and playwright install."
            state.add_log("browser", "error", state.browser_feedback)
            return state

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
            state.add_log("browser", "error", state.browser_feedback)
            return state

        state.browser_status = "success" if "success" in status.lower() else "error"
        state.browser_feedback = status
        state.add_log("browser", state.browser_status, status)
        return state
