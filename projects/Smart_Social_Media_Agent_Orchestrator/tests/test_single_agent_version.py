import sys
import tempfile
import time
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from models import PostState
from single_agent_version.single_agent import SingleSocialMediaAgent
from single_agent_version.web_app import app


JEWELRY_PROMPT = (
    "I am a seller on instagram account and ı am selling jewerly can you make a post "
    "for my insta account, in the image I want you to make closer photage of a woman's ear. "
    "There shoukld be 3 earings in her ear and they must be made of silver. can you make realistic."
)


class SingleAgentVersionTests(unittest.TestCase):
    def test_single_agent_generates_comparable_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = PostState(
                user_prompt=f"{JEWELRY_PROMPT} Create a social media image for this post. Share this to the local demo upload page.",
                platform="local_demo",
                visual_style="realistic",
            )

            result = SingleSocialMediaAgent(provider="mock", image_provider="pillow", output_dir=tmp).run(state)

            self.assertEqual(result.topic, "silver earrings")
            self.assertIn("Small details", result.caption)
            self.assertIn("woman's ear", result.media_prompt)
            self.assertEqual(result.qa_status, "approved")
            self.assertEqual(result.browser_status, "success")
            self.assertTrue(Path(result.media_path).exists())
            self.assertTrue(all(log["step"] == "single_agent" for log in result.logs))

    def test_single_agent_web_flow_finishes(self):
        client = app.test_client()
        response = client.post(
            "/generate",
            data={
                "provider": "mock",
                "image_provider": "pillow",
                "prompt": "Make a post about Pilates.",
                "post_details": "Use a calm studio tone.",
                "platform": "local_demo",
                "visual_style": "realistic",
                "upload_mode": "local_demo",
                "media_mode": "generate",
            },
            content_type="multipart/form-data",
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("/run/", response.headers["Location"])

        run_response = client.get(response.headers["Location"])
        self.assertEqual(run_response.status_code, 200)
        self.assertIn(b"Single-Agent Orchestration", run_response.data)
        self.assertIn(b"Single Social Agent", run_response.data)

        run_id = response.headers["Location"].rstrip("/").split("/")[-1]
        payload = None
        for _ in range(20):
            api_response = client.get(f"/api/run/{run_id}")
            self.assertEqual(api_response.status_code, 200)
            payload = api_response.get_json()
            if payload["status"] in {"finished", "error"}:
                break
            time.sleep(0.05)

        self.assertIsNotNone(payload)
        self.assertEqual(payload["status"], "finished")
        self.assertEqual(len(payload["agents"]), 1)
        self.assertEqual(payload["agents"][0]["key"], "single_agent")

        final_response = client.get(f"/result/{run_id}")
        self.assertEqual(final_response.status_code, 200)
        self.assertIn(b"Single Agent Output", final_response.data)


if __name__ == "__main__":
    unittest.main()
