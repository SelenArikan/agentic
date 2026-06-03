import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents import TaskManagerAgent
from models import PostState


class TaskManagerTests(unittest.TestCase):
    def test_post_this_requires_topic_clarification(self):
        with tempfile.TemporaryDirectory() as tmp:
            manager = TaskManagerAgent(output_dir=tmp, image_provider="pillow")
            state = manager.run(PostState(user_prompt="Post this."), ask_user=None)

            self.assertTrue(state.needs_clarification)
            self.assertEqual(state.pending_clarification, "topic")
            self.assertIn("topic", state.clarification_question.lower())

    def test_short_prompt_full_route_with_demo_defaults(self):
        answers = iter(["local demo", "fitness-focused"])

        with tempfile.TemporaryDirectory() as tmp:
            manager = TaskManagerAgent(output_dir=tmp, image_provider="pillow")
            state = manager.run(
                PostState(user_prompt="Make a post about Pilates."),
                ask_user=lambda _question: next(answers),
            )

            self.assertEqual(state.routing_plan["researcher"], True)
            self.assertEqual(state.routing_plan["writer"], True)
            self.assertEqual(state.routing_plan["visual_prompt_engineer"], True)
            self.assertEqual(state.routing_plan["media_creator"], True)
            self.assertEqual(state.routing_plan["browser"], True)
            self.assertIsNotNone(state.optimized_media_prompt)
            self.assertEqual(state.qa_status, "approved")
            self.assertEqual(state.browser_status, "success")
            self.assertTrue(Path(state.media_path).exists())

    def test_exact_text_skips_research_and_writer(self):
        with tempfile.TemporaryDirectory() as tmp:
            manager = TaskManagerAgent(output_dir=tmp, image_provider="pillow")
            state = manager.run(
                PostState(user_prompt="Share this exact text: 'Join my class!' with a picture of a reformer bed."),
                ask_user=lambda _question: "local demo",
            )

            self.assertFalse(state.routing_plan["researcher"])
            self.assertFalse(state.routing_plan["writer"])
            self.assertTrue(state.routing_plan["visual_prompt_engineer"])
            self.assertTrue(state.routing_plan["media_creator"])
            self.assertEqual(state.caption, "Join my class!")
            self.assertEqual(state.qa_status, "approved")

    def test_qa_rejection_triggers_repair_cycle(self):
        with tempfile.TemporaryDirectory() as tmp:
            manager = TaskManagerAgent(output_dir=tmp, image_provider="pillow")
            calls = {"count": 0}

            def fake_review(state):
                calls["count"] += 1
                if calls["count"] == 1:
                    state.qa_status = "rejected"
                    state.qa_feedback = "Caption is incoherent and contains instructional text instead of a polished marketing message."
                    state.add_log("qa", "rejected", state.qa_feedback)
                else:
                    state.qa_status = "approved"
                    state.qa_feedback = "Caption and media are ready for demo upload."
                    state.add_log("qa", "approved", state.qa_feedback)
                return state

            manager.qa_agent.review = fake_review
            state = manager.run(
                PostState(
                    user_prompt=(
                        "Share this exact text: 'şirketim doğa sporları ile ilgili malzemeler satıyor bunun için "
                        "bir post yapmanı istiyorum' with a picture of a man hiking on a mountain."
                    )
                ),
                ask_user=lambda _question: "local demo",
            )

            self.assertEqual(state.qa_status, "approved")
            self.assertEqual(state.browser_status, "success")
            self.assertTrue(any(log["status"] == "qa_repair" for log in state.logs))
            self.assertNotIn("yapmanı", state.caption)

    def test_turkish_post_request_routes_media_and_browser(self):
        with tempfile.TemporaryDirectory() as tmp:
            manager = TaskManagerAgent(output_dir=tmp, image_provider="pillow")
            state = manager.run(
                PostState(
                    user_prompt=(
                        "şirketim doğa sporları ile ilgili malzemeler satıyor bunun için bir post yapmanı istiyorum "
                        "burda dağda yürüyüş yapan bir adam olsun"
                    )
                ),
                ask_user=lambda _question: "local demo",
            )

            self.assertTrue(state.routing_plan["media_creator"])
            self.assertTrue(state.routing_plan["browser"])
            self.assertEqual(state.qa_status, "approved")
            self.assertEqual(state.browser_status, "success")

    def test_english_jewelry_request_extracts_product_topic(self):
        with tempfile.TemporaryDirectory() as tmp:
            manager = TaskManagerAgent(output_dir=tmp, image_provider="pillow")
            state = PostState(
                user_prompt=(
                    "I am a seller on instagram account and ı am selling jewerly can you make a post "
                    "for my insta account, in the image I want you to make closer photage of a woman's ear. "
                    "There shoukld be 3 earings in her ear and they must be made of silver. can you make realistic."
                ),
                platform="local_demo",
                visual_style="realistic",
            )

            manager.analyze_prompt(state)

            self.assertEqual(state.topic, "silver earrings")
            self.assertTrue(state.routing_plan["writer"])
            self.assertTrue(state.routing_plan["media_creator"])

    def test_web_prompt_boilerplate_does_not_pollute_topic(self):
        with tempfile.TemporaryDirectory() as tmp:
            manager = TaskManagerAgent(output_dir=tmp, image_provider="pillow")
            state = PostState(
                user_prompt=(
                    "Make a pilates post. This post has to be about outdoor pilates exercises "
                    "Create a social media image for this post. Share this to the local demo upload page."
                ),
                platform="local_demo",
                visual_style="fitness-focused",
            )

            manager.analyze_prompt(state)

            self.assertEqual(state.topic, "outdoor pilates exercises")
            self.assertTrue(state.routing_plan["media_creator"])


if __name__ == "__main__":
    unittest.main()
