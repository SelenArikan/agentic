from __future__ import annotations

from typing import Optional

from models import PostState

from .requirement_brief import RequestBriefVerifierAgent
from .requirement_qa import RequirementAwareQAAgent
from .task_manager import AskUser, TaskManagerAgent


class ImprovedTaskManagerAgent(TaskManagerAgent):
    """Assignment 4 Task Manager with requirement verification and approval gates."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.request_brief_agent = RequestBriefVerifierAgent()
        self.qa_agent = RequirementAwareQAAgent(
            self.qa_agent.llm_client,
            strict_api=self.qa_agent.strict_api,
        )
        self._approval_callback: Optional[AskUser] = None

    def run(self, state: PostState, ask_user: Optional[AskUser] = None) -> PostState:
        self._approval_callback = ask_user
        try:
            return super().run(state, ask_user=ask_user)
        finally:
            self._approval_callback = None

    def analyze_prompt(self, state: PostState) -> PostState:
        self.request_brief_agent.prepare(state)
        if self.request_brief_agent.needs_topic_clarification(state):
            return self._ask(
                state,
                "topic",
                "I could not identify a reliable post topic. What specific topic or product should the post cover?",
            )
        return super().analyze_prompt(state)

    def _execute_route(self, state: PostState) -> PostState:
        if state.routing_plan.get("researcher"):
            self._run_with_retry(state, "researcher", self.researcher.get_trends, self._validate_research)
        else:
            state.add_log("researcher", "skipped", "Research skipped by routing plan.")

        if state.routing_plan.get("writer"):
            self._run_with_retry(state, "writer", self.writer.write_content, self._validate_writer)
        else:
            state.add_log("writer", "skipped", "Writer skipped because caption is already available.")

        self.request_brief_agent.enforce_visual_constraints(state)

        if state.routing_plan.get("visual_prompt_engineer"):
            self._run_with_retry(
                state,
                "visual_prompt_engineer",
                self.visual_prompt_engineer.refine_prompt,
                self._validate_visual_prompt,
            )
        else:
            state.add_log("visual_prompt_engineer", "skipped", "Visual prompt engineer skipped by routing plan.")

        if state.routing_plan.get("media_creator"):
            action = lambda current: self.media_creator.create_media(current, self.output_dir)
            self._run_with_retry(state, "media_creator", action, self._validate_media)
        elif state.has_media_file:
            state.add_log("media_creator", "skipped", "Media creator skipped because media file already exists.")
        else:
            state.add_log("media_creator", "skipped", "Media creator skipped by routing plan.")

        self._run_with_retry(state, "qa", self.qa_agent.review, self._validate_qa)
        if state.qa_status == "rejected":
            self._repair_until_qa_approved(state)

        if state.qa_status != "approved":
            state.can_continue = False
            state.add_log("task_manager", "blocked", "QA rejected the post; browser step skipped.")
            return state

        if state.routing_plan.get("browser"):
            if not self._approve_before_publish(state):
                return state
            action = lambda current: self.browser.upload_to_demo(
                current,
                self.output_dir,
                use_playwright=self.use_playwright,
            )
            self._run_with_retry(state, "browser", action, self._validate_browser)
        else:
            state.add_log("browser", "skipped", "Browser upload skipped by routing plan.")

        state.add_log("task_manager", "success", "Improved workflow finished.")
        return state

    def _repair_after_qa_rejection(self, state: PostState, repair_attempt: int) -> bool:
        feedback = (state.qa_feedback or "").lower()
        if "visual requirement mismatch" not in feedback and "required visual constraint" not in feedback:
            return super()._repair_after_qa_rejection(state, repair_attempt)

        state.can_continue = True
        state.approval_required = True
        state.approval_reason = "Requirement-aware QA repaired visual constraints before publish."
        state.optimized_media_prompt = None
        state.negative_media_prompt = None
        state.visual_prompt_template = None
        state.has_media_file = False
        state.add_log(
            "task_manager",
            "requirement_repair",
            "Requirement-aware QA returned visual feedback; rebuilding the visual route.",
            attempt=repair_attempt,
            feedback=state.qa_feedback,
        )
        self.request_brief_agent.enforce_visual_constraints(state)

        if state.routing_plan.get("visual_prompt_engineer"):
            self._run_with_retry(
                state,
                "visual_prompt_engineer",
                self.visual_prompt_engineer.refine_prompt,
                self._validate_visual_prompt,
            )
        if state.routing_plan.get("media_creator"):
            action = lambda current: self.media_creator.create_media(current, self.output_dir)
            self._run_with_retry(state, "media_creator", action, self._validate_media)
        return True

    def _approve_before_publish(self, state: PostState) -> bool:
        if not state.approval_required or state.human_approved:
            return True
        reason = state.approval_reason or "Human review requested before publish."
        if self._approval_callback is None:
            state.can_continue = False
            state.browser_status = "awaiting_approval"
            state.browser_feedback = reason
            state.add_log("human_approval", "pending", reason)
            return False

        answer = self._approval_callback(f"{reason} Approve final local demo upload? yes or no")
        if answer.strip().lower() not in {"yes", "y", "approve", "approved", "ok", "evet"}:
            state.can_continue = False
            state.browser_status = "approval_rejected"
            state.browser_feedback = "Human approval rejected before publish."
            state.add_log("human_approval", "rejected", state.browser_feedback)
            return False

        state.human_approved = True
        state.add_log("human_approval", "approved", reason)
        return True
