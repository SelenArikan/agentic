from __future__ import annotations

import json
from typing import Optional

from models import PostState
from providers import NvidiaBuildClient


class TrendResearcherAgent:
    """Returns trend keywords and hashtags."""

    def __init__(self, llm_client: Optional[NvidiaBuildClient] = None, *, strict_api: bool = False) -> None:
        self.llm_client = llm_client
        self.strict_api = strict_api

    def get_trends(self, state: PostState) -> PostState:
        if self.llm_client:
            try:
                data = self.llm_client.chat_json(
                    [
                        {
                            "role": "user",
                            "content": json.dumps(
                                {
                                    "task": "Act as a social media trend researcher.",
                                    "topic": state.topic,
                                    "user_prompt": state.user_prompt,
                                    "rules": [
                                        "Return current-sounding but safe social media keywords.",
                                        "Return 4 to 6 keywords.",
                                        "Return 4 to 8 hashtags.",
                                        "Do not include unsafe or political content unless requested.",
                                    ],
                                    "schema": {"keywords": ["string"], "hashtags": ["#string"]},
                                }
                            ),
                        }
                    ],
                    temperature=0.2,
                )
                state.keywords = _string_list(data.get("keywords"))
                state.hashtags = _normalize_hashtags(_string_list(data.get("hashtags")))
                if len(state.keywords) < 3 or len(state.hashtags) < 2:
                    raise ValueError("NVIDIA trend response did not include enough keywords/hashtags.")
                state.add_log("researcher", "success", "Trend keywords and hashtags generated with NVIDIA NIM.")
                return state
            except Exception as exc:
                state.add_log("researcher", "error", f"NVIDIA trend research failed: {exc}")
                if self.strict_api:
                    raise

        topic = (state.topic or "social media").lower()

        if "pilates" in topic:
            state.keywords = ["pilates", "reformer pilates", "wellness", "core strength"]
            state.hashtags = ["#pilates", "#reformerpilates", "#wellness", "#fitness"]
        elif "yoga" in topic:
            state.keywords = ["yoga", "morning routine", "mindfulness", "flexibility"]
            state.hashtags = ["#yoga", "#morningroutine", "#mindfulness", "#wellness"]
        elif "food" in topic or "restaurant" in topic:
            state.keywords = ["local food", "fresh menu", "community favorite", "behind the scenes"]
            state.hashtags = ["#localeats", "#foodie", "#freshmenu", "#community"]
        else:
            compact_topic = topic.replace(" ", "")
            state.keywords = [topic, "social media post", "audience engagement", "brand story"]
            state.hashtags = [f"#{compact_topic[:30] or 'post'}", "#socialmedia", "#community", "#storytelling"]

        state.add_log("researcher", "success", "Mock trend keywords and hashtags generated.")
        return state


def _string_list(value) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return []


def _normalize_hashtags(values: list[str]) -> list[str]:
    normalized = []
    for value in values:
        tag = value.strip()
        if not tag:
            continue
        if not tag.startswith("#"):
            tag = "#" + "".join(part.capitalize() for part in tag.split())
        normalized.append(tag)
    return normalized[:8]
