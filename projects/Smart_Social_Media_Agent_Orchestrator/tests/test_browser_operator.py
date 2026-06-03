import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents.browser_operator import BrowserOperatorAgent
from models import PostState


class BrowserOperatorTests(unittest.TestCase):
    def test_browser_operator_simulated_upload(self):
        with tempfile.TemporaryDirectory() as tmp:
            media = Path(tmp) / "image.jpg"
            media.write_bytes(b"fake")
            state = PostState(
                user_prompt="test",
                platform="local_demo",
                caption="Join my class!",
                media_path=str(media),
            )

            BrowserOperatorAgent().upload_to_demo(state, Path(tmp), use_playwright=False)

            self.assertEqual(state.browser_status, "success")
            self.assertTrue((Path(tmp) / "browser_upload_manifest.json").exists())


if __name__ == "__main__":
    unittest.main()
