import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents.visual_prompt_engineer import VisualPromptEngineerAgent
from models import PostState


class VisualPromptEngineerTests(unittest.TestCase):
    def test_local_prompt_engineer_creates_professional_json(self):
        state = PostState(
            user_prompt="Make a post about Pilates.",
            topic="Pilates",
            visual_style="luxury",
            media_prompt="Pilates reformer studio image",
            routing_plan={"media_creator": True},
        )

        VisualPromptEngineerAgent().refine_prompt(state)

        self.assertIsInstance(state.visual_prompt_template, dict)
        self.assertIn("camera", state.visual_prompt_template)
        self.assertIn("lighting", state.visual_prompt_template)
        self.assertIn("negative_prompt", state.visual_prompt_template)
        self.assertIn("premium", state.optimized_media_prompt.lower())
        self.assertIn("watermark", state.negative_media_prompt.lower())

    def test_local_prompt_engineer_uses_post_details_as_visual_constraints(self):
        state = PostState(
            user_prompt="Outdoor post",
            topic="doğa sporları ekipmanları",
            post_details="mavi beyaz siyah tonlarında olsun daha çok cozy bir havası olsun",
            media_prompt="dağda yürüyüş yapan bir adam",
            routing_plan={"media_creator": True},
        )

        VisualPromptEngineerAgent().refine_prompt(state)

        self.assertIn("deep blue", state.optimized_media_prompt)
        self.assertIn("clean white", state.optimized_media_prompt)
        self.assertIn("matte black", state.optimized_media_prompt)
        self.assertIn("cozy", state.optimized_media_prompt.lower())

    def test_outdoor_pilates_stays_outdoors(self):
        state = PostState(
            user_prompt="Make a pilates post. This post has to be about outdoor pilates exercises.",
            topic="outdoor pilates exercises",
            visual_style="fitness-focused",
            media_prompt="fitness-focused image about outdoor pilates exercises",
            routing_plan={"media_creator": True},
        )

        VisualPromptEngineerAgent().refine_prompt(state)

        prompt = state.optimized_media_prompt.lower()
        self.assertIn("outdoor", prompt)
        self.assertIn("mat pilates", prompt)
        self.assertNotIn("reformer", prompt)
        self.assertNotIn("studio", prompt)


if __name__ == "__main__":
    unittest.main()
