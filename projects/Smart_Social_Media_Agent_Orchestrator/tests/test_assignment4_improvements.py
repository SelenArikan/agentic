import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents import ImprovedTaskManagerAgent, RequirementAwareQAAgent, RequestBriefVerifierAgent
from models import PostState


class Assignment4ImprovementTests(unittest.TestCase):
    def test_request_brief_marks_ambiguous_reference_low_confidence(self):
        state = PostState(user_prompt="Make a post about this and share it.")

        RequestBriefVerifierAgent().prepare(state)

        self.assertLess(state.request_confidence, 0.55)
        self.assertIn("ambiguous_reference", state.request_brief["ambiguities"])
        self.assertTrue(state.approval_required)

    def test_improved_manager_asks_for_topic_when_prompt_is_ambiguous(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = PostState(
                user_prompt="Make a post about this and share it.",
                platform="local_demo",
                visual_style="realistic",
            )

            result = ImprovedTaskManagerAgent(output_dir=tmp, image_provider="pillow").run(state, ask_user=None)

            self.assertTrue(result.needs_clarification)
            self.assertEqual(result.pending_clarification, "topic")
            self.assertFalse(result.caption)

    def test_improved_manager_keeps_outdoor_mat_pilates_constraints(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = PostState(
                user_prompt=(
                    "Make a Pilates post. The image must show outdoor mat Pilates in a park, "
                    "not an indoor studio."
                ),
                platform="local_demo",
                visual_style="fitness-focused",
            )

            result = ImprovedTaskManagerAgent(output_dir=tmp, image_provider="pillow").run(
                state,
                ask_user=lambda question: "yes" if "Approve" in question else "local demo",
            )

            prompt = (result.optimized_media_prompt or "").lower()
            self.assertEqual(result.qa_status, "approved")
            self.assertIn("outdoor", prompt)
            self.assertIn("mat pilates", prompt)
            self.assertNotIn("boutique pilates studio", prompt)

    def test_requirement_qa_rejects_missing_visual_constraint(self):
        state = PostState(
            user_prompt="Outdoor mat Pilates post.",
            topic="Pilates",
            caption="Fresh air and mindful movement.",
            media_prompt="warm Pilates wellness visual",
            optimized_media_prompt="premium boutique Pilates studio with reformer beds",
            routing_plan={"media_creator": True},
            request_brief={
                "visual_constraints": ["outdoor environment", "mat Pilates exercise"],
                "avoid_constraints": ["indoor studio"],
            },
        )
        image = Path(__file__)
        state.media_path = str(image)

        RequirementAwareQAAgent().review(state)

        self.assertEqual(state.qa_status, "rejected")
        self.assertIn("Visual requirement mismatch", state.qa_feedback)

    def test_human_approval_gate_blocks_publish_without_callback(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = PostState(
                user_prompt="Make a post about Pilates.",
                platform="local_demo",
                visual_style="fitness-focused",
                approval_required=True,
                approval_reason="Manual review requested.",
            )

            result = ImprovedTaskManagerAgent(output_dir=tmp, image_provider="pillow").run(state, ask_user=None)

            self.assertEqual(result.qa_status, "approved")
            self.assertEqual(result.browser_status, "awaiting_approval")
            self.assertFalse(result.human_approved)


if __name__ == "__main__":
    unittest.main()
