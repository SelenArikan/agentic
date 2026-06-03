import sys
import time
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from web_app import app


class WebAppTests(unittest.TestCase):
    def test_index_loads(self):
        client = app.test_client()
        response = client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Initialize Generation", response.data)
        self.assertIn(b"Content Directives", response.data)

    def test_generate_mock_post(self):
        client = app.test_client()
        response = client.post(
            "/generate",
            data={
                "provider": "mock",
                "image_provider": "pillow",
                "prompt": "Make a post about Pilates.",
                "post_details": "Use a calm studio tone.",
                "platform": "local_demo",
                "visual_style": "fitness-focused",
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
        self.assertIn(b"Live Orchestration", run_response.data)
        self.assertIn(b"Visual Prompt Engineer", run_response.data)

        run_id = response.headers["Location"].rstrip("/").split("/")[-1]
        for _ in range(20):
            api_response = client.get(f"/api/run/{run_id}")
            self.assertEqual(api_response.status_code, 200)
            payload = api_response.get_json()
            if payload["status"] in {"finished", "error"}:
                break
            time.sleep(0.05)
        self.assertEqual(payload["status"], "finished")
        self.assertTrue(any(agent["key"] == "visual_prompt_engineer" for agent in payload["agents"]))
        self.assertTrue(any(agent["key"] == "media_creator" for agent in payload["agents"]))
        self.assertNotIn("calm studio tone", payload["caption"])

        final_response = client.get(f"/result/{run_id}")
        self.assertEqual(final_response.status_code, 200)
        self.assertIn(b"Output Gallery", final_response.data)
        self.assertIn(b"Agent timeline", final_response.data)


if __name__ == "__main__":
    unittest.main()
