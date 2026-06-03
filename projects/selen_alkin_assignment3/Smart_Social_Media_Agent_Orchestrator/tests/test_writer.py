import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents.writer import ContentWriterAgent
from models import PostState


class WriterTests(unittest.TestCase):
    def test_writer_does_not_overwrite_existing_caption(self):
        state = PostState(
            user_prompt="Share this exact text: 'Join my class!'",
            topic="Pilates",
            caption="Join my class!",
            routing_plan={"media_creator": True},
            hashtags=["#pilates"],
        )

        ContentWriterAgent().write_content(state)

        self.assertEqual(state.caption, "Join my class!")
        self.assertIsNotNone(state.media_prompt)

    def test_writer_handles_turkish_outdoor_request(self):
        state = PostState(
            user_prompt=(
                "şirketim doğa sporları ile ilgili malzemeler satıyor bunun için bir post yapmanı istiyorum "
                "burda dağda yürüyüş yapan bir adam olsun"
            ),
            post_details="mavi beyaz siyah tonlarında olsun daha çok cozy bir havası olsun",
            topic="şirketim doğa sporları ile ilgili malzemeler satıyor bunun için bir yapmanı isti",
            visual_style="realistic",
            routing_plan={"media_creator": True},
        )

        ContentWriterAgent().write_content(state)

        self.assertEqual(state.topic, "doğa sporları ekipmanları")
        self.assertIn("Doğaya", state.caption)
        self.assertNotIn("yapmanı", state.caption)
        self.assertNotIn("mavi", state.caption.lower())
        self.assertNotIn("cozy", state.caption.lower())
        self.assertIn("mountain trail", state.media_prompt)
        self.assertIn("blue", state.media_prompt)
        self.assertIn("cozy", state.media_prompt)

    def test_writer_handles_english_jewelry_prompt_with_turkish_keyboard_i(self):
        state = PostState(
            user_prompt=(
                "I am a seller on instagram account and ı am selling jewerly can you make a post "
                "for my insta account, in the image I want you to make closer photage of a woman's ear. "
                "There shoukld be 3 earings in her ear and they must be made of silver. can you make realistic."
            ),
            topic="my insta account, in the image I want you to make closer photage of a woman's ea",
            visual_style="realistic",
            routing_plan={"media_creator": True},
        )

        ContentWriterAgent().write_content(state)

        self.assertEqual(state.topic, "silver earrings")
        self.assertIn("Small details", state.caption)
        self.assertIn("#SilverJewelry", state.caption)
        self.assertNotIn("profesyonel", state.caption)
        self.assertNotIn("My Insta Account", state.caption)
        self.assertIn("woman's ear", state.media_prompt)
        self.assertIn("three silver earrings", state.media_prompt)


if __name__ == "__main__":
    unittest.main()
