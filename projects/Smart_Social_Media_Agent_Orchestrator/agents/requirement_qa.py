from __future__ import annotations

from typing import Iterable

from models import PostState

from .qa_agent import QAAgent


class RequirementAwareQAAgent(QAAgent):
    """Adds requirement alignment checks after the normal QA pass."""

    def review(self, state: PostState) -> PostState:
        super().review(state)
        if state.qa_status != "approved":
            return state

        issues = self._requirement_issues(state)
        if not issues:
            state.add_log("requirement_qa", "approved", "Structured request constraints are preserved.")
            return state

        state.qa_status = "rejected"
        state.qa_feedback = (
            "Visual requirement mismatch; output is not aligned with the structured request brief. "
            + " ".join(issues)
        )
        state.add_log("requirement_qa", "rejected", state.qa_feedback)
        return state

    def _requirement_issues(self, state: PostState) -> list[str]:
        brief = state.request_brief or {}
        constraints = list(brief.get("visual_constraints") or [])
        avoid_constraints = list(brief.get("avoid_constraints") or [])
        prompt = " ".join(part for part in (state.media_prompt or "", state.optimized_media_prompt or "") if part)
        lower_prompt = prompt.lower()
        positive_prompt = lower_prompt.split("avoid user constraint violations:", 1)[0]
        issues = []

        if is_generic_topic(state.topic):
            issues.append("Topic is too generic for publish.")

        if state.routing_plan.get("media_creator", False):
            for constraint in constraints:
                if not constraint_is_present(constraint, lower_prompt):
                    issues.append(f"Missing required visual constraint: {constraint}.")
            for avoid in avoid_constraints:
                if forbidden_constraint_is_present(avoid, positive_prompt):
                    issues.append(f"Forbidden visual direction is still present: {avoid}.")
        return issues


def is_generic_topic(topic: str | None) -> bool:
    return (topic or "").strip().lower() in {"", "this", "it", "that", "post", "image", "content", "your update"}


def constraint_is_present(constraint: str, lower_prompt: str) -> bool:
    aliases = {
        "outdoor environment": ("outdoor", "outside", "park", "garden", "open sky", "mountain", "trail", "nature"),
        "park setting": ("park", "garden", "grass", "trees"),
        "mat Pilates exercise": ("mat pilates", "pilates mat", "yoga mat", "mat exercise"),
        "close-up composition": ("close-up", "close up", "macro", "close portrait"),
        "earrings visible on a woman's ear": ("earring", "woman's ear", "womans ear", "ear wearing"),
        "three earrings": ("three earring", "3 earring"),
        "silver earrings": ("silver earring", "silver jewelry"),
        "mountain setting": ("mountain", "trail", "hills", "dağ"),
        "hiking subject": ("hiking", "hiker", "walking", "trekking", "yürüyüş"),
    }
    return contains_any(lower_prompt, aliases.get(constraint, (constraint,)))


def forbidden_constraint_is_present(constraint: str, lower_prompt: str) -> bool:
    aliases = {
        "indoor studio": ("indoor studio", "boutique pilates studio", "studio interior", "gym interior"),
        "text overlay": ("text overlay", "visible typography", "caption overlay"),
    }
    return contains_any(lower_prompt, aliases.get(constraint, (constraint,)))


def contains_any(value: str, terms: Iterable[str]) -> bool:
    return any(term.lower() in value for term in terms)
