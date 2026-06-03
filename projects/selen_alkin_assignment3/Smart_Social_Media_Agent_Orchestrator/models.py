from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class PostRequest:
    user_prompt: str
    provider: str = "mock"
    use_playwright: bool = False
    output_dir: str = "outputs"
    max_clarifications: int = 2


@dataclass
class PostState:
    user_prompt: str
    clarification_answer: Optional[str] = None

    topic: Optional[str] = None
    post_details: Optional[str] = None
    platform: Optional[str] = None
    visual_style: Optional[str] = None
    caption: Optional[str] = None
    media_prompt: Optional[str] = None
    optimized_media_prompt: Optional[str] = None
    negative_media_prompt: Optional[str] = None
    visual_prompt_template: Optional[Dict[str, Any]] = None
    media_path: Optional[str] = None
    media_type: Optional[str] = None
    has_media_file: bool = False
    reference_image_path: Optional[str] = None
    reference_image_note: Optional[str] = None
    use_reference_as_final_media: bool = False
    image_provider: Optional[str] = None

    keywords: List[str] = field(default_factory=list)
    hashtags: List[str] = field(default_factory=list)

    routing_plan: Dict[str, bool] = field(default_factory=dict)

    needs_clarification: bool = False
    clarification_question: Optional[str] = None
    pending_clarification: Optional[str] = None
    clarification_count: int = 0
    clarification_history: List[Dict[str, str]] = field(default_factory=list)
    can_continue: bool = True

    qa_status: Optional[str] = None
    qa_feedback: Optional[str] = None
    browser_status: Optional[str] = None
    browser_feedback: Optional[str] = None

    logs: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def add_log(self, step: str, status: str, message: str, **details: Any) -> None:
        entry: Dict[str, Any] = {
            "step": step,
            "status": status,
            "message": message,
        }
        if details:
            entry["details"] = details
        self.logs.append(entry)

    def to_dict(self) -> Dict[str, Any]:
        return _jsonable(asdict(self))


def _jsonable(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    return value
