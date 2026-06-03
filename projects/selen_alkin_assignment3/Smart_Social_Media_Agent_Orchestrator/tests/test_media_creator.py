import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents.media_creator import MediaCreatorAgent
from models import PostState


class MediaCreatorTests(unittest.TestCase):
    def test_media_creator_writes_image(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = PostState(
                user_prompt="Make a post about Pilates.",
                topic="Pilates",
                media_prompt="Pilates studio image",
                hashtags=["#pilates"],
            )

            MediaCreatorAgent(image_provider="pillow").create_media(state, Path(tmp))

            self.assertTrue(Path(state.media_path).exists())
            self.assertEqual(state.media_type, "image")


if __name__ == "__main__":
    unittest.main()
