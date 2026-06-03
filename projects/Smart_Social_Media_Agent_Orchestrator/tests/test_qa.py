import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents.qa_agent import QAAgent
from models import PostState


class QATests(unittest.TestCase):
    def test_qa_rejects_banned_word(self):
        state = PostState(
            user_prompt="test",
            caption="This includes illegal content.",
            routing_plan={"media_creator": False},
        )

        QAAgent().review(state)

        self.assertEqual(state.qa_status, "rejected")
        self.assertIn("banned", state.qa_feedback)

    def test_qa_approves_caption_and_media(self):
        with tempfile.TemporaryDirectory() as tmp:
            media = Path(tmp) / "image.jpg"
            media.write_bytes(b"fake")
            state = PostState(
                user_prompt="test",
                topic="Pilates",
                caption="Join my class!",
                media_prompt="Pilates studio image",
                media_path=str(media),
                routing_plan={"media_creator": True},
            )

            QAAgent().review(state)

            self.assertEqual(state.qa_status, "approved")

    def test_qa_rejects_caption_that_copies_post_details(self):
        state = PostState(
            user_prompt="test",
            topic="Doğa sporları ekipmanları",
            post_details="mavi beyaz siyah tonlarında olsun daha çok cozy bir havası olsun",
            caption=(
                "Doğaya çıkmaya hazır mısın?\n\n"
                "mavi beyaz siyah tonlarında olsun daha çok cozy bir havası olsun"
            ),
            routing_plan={"media_creator": False},
        )

        QAAgent().review(state)

        self.assertEqual(state.qa_status, "rejected")
        self.assertIn("post details", state.qa_feedback.lower())


if __name__ == "__main__":
    unittest.main()
