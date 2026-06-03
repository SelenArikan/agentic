from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Callable, Optional

from config import (
    IMAGE_PROVIDER,
    MAX_CLARIFICATION_QUESTIONS,
    MISTRAL_API_KEY,
    MISTRAL_IMAGE_MODEL,
    MVP_DEMO_ONLY,
    NVIDIA_API_KEY,
    NVIDIA_BASE_URL,
    NVIDIA_IMAGE_BASE_URL,
    NVIDIA_IMAGE_CANDIDATES,
    NVIDIA_IMAGE_ENDPOINT,
    NVIDIA_IMAGE_MODEL,
    NVIDIA_MODEL,
    NVIDIA_QA_MODEL,
    NVIDIA_RESEARCH_MODEL,
    NVIDIA_WRITER_MODEL,
    OUTPUT_DIR,
)
from models import PostState
from providers import MistralImageClient, NvidiaBuildClient

from .browser_operator import BrowserOperatorAgent
from .media_creator import MediaCreatorAgent
from .qa_agent import QAAgent
from .researcher import TrendResearcherAgent
from .visual_prompt_engineer import VisualPromptEngineerAgent
from .writer import ContentWriterAgent, extract_english_topic, is_usable_english_topic, normalize_english_topic


AskUser = Callable[[str], str]


class TaskManagerAgent:
    """Central orchestrator for routing, validation, retry, and logs."""

    REAL_PLATFORMS = {"instagram", "tiktok", "facebook", "linkedin", "x", "twitter"}
    LOCAL_PLATFORMS = {"local", "local demo", "local_demo", "demo"}
    MEDIA_WORDS = {"picture", "image", "photo", "visual", "video", "reel", "media"}
    UPLOAD_WORDS = {"upload", "share", "publish"}

    def __init__(
        self,
        *,
        provider: str = "mock",
        image_provider: str = IMAGE_PROVIDER,
        output_dir: Path | str = OUTPUT_DIR,
        use_playwright: bool = False,
        max_clarifications: int = MAX_CLARIFICATION_QUESTIONS,
    ) -> None:
        self.provider = provider
        self.image_provider = image_provider
        self.output_dir = Path(output_dir)
        self.use_playwright = use_playwright
        self.max_clarifications = max_clarifications

        strict_api = provider == "nvidia"
        research_client = NvidiaBuildClient(model=NVIDIA_RESEARCH_MODEL) if provider == "nvidia" else None
        writer_client = NvidiaBuildClient(model=NVIDIA_WRITER_MODEL) if provider == "nvidia" else None
        visual_prompt_client = NvidiaBuildClient(model=NVIDIA_WRITER_MODEL) if provider == "nvidia" else None
        image_client = self._build_nvidia_image_client(provider, image_provider)
        mistral_image_client = self._build_mistral_image_client(image_provider)
        qa_client = NvidiaBuildClient(model=NVIDIA_QA_MODEL) if provider == "nvidia" else None
        self.researcher = TrendResearcherAgent(research_client, strict_api=strict_api)
        self.writer = ContentWriterAgent(writer_client, strict_api=False)
        self.visual_prompt_engineer = VisualPromptEngineerAgent(visual_prompt_client, strict_api=False)
        self.media_creator = MediaCreatorAgent(
            image_client,
            mistral_image_client,
            image_provider=image_provider,
            strict_api=strict_api and image_provider in {"nvidia", "mistral"},
        )
        self.qa_agent = QAAgent(qa_client, strict_api=strict_api)
        self.browser = BrowserOperatorAgent()

    def run(self, state: PostState, ask_user: Optional[AskUser] = None) -> PostState:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._clean_previous_media_outputs()
        state.add_log(
            "task_manager",
            "start",
            "Workflow started.",
            provider=self.provider,
            image_provider=self.image_provider,
            nvidia_default_chat_model=NVIDIA_MODEL if self.provider == "nvidia" else None,
            nvidia_research_model=NVIDIA_RESEARCH_MODEL if self.provider == "nvidia" else None,
            nvidia_writer_model=NVIDIA_WRITER_MODEL if self.provider == "nvidia" else None,
            nvidia_qa_model=NVIDIA_QA_MODEL if self.provider == "nvidia" else None,
            nvidia_chat_endpoint=f"{NVIDIA_BASE_URL.rstrip('/')}/chat/completions" if self.provider == "nvidia" else None,
            nvidia_image_endpoint=(
                NVIDIA_IMAGE_ENDPOINT or f"{NVIDIA_IMAGE_BASE_URL.rstrip('/')}/{NVIDIA_IMAGE_MODEL}"
                if self.image_provider in {"nvidia", "auto"}
                else None
            ),
            nvidia_image_candidates=NVIDIA_IMAGE_CANDIDATES if self.image_provider in {"nvidia", "auto"} else None,
            mistral_image_model=MISTRAL_IMAGE_MODEL if self.image_provider in {"mistral", "auto"} else None,
        )

        while True:
            self.analyze_prompt(state)
            if not state.needs_clarification:
                break

            state.add_log("task_manager", "clarification_needed", state.clarification_question or "")
            if ask_user is None:
                self._save_outputs(state)
                return state

            if state.clarification_count >= self.max_clarifications:
                state.can_continue = False
                state.add_log("task_manager", "blocked", "Maximum clarification question limit reached.")
                self._save_outputs(state)
                return state

            answer = ask_user(state.clarification_question or "Please clarify the request.")
            self.merge_clarification(state, answer)

        if not state.can_continue:
            self._save_outputs(state)
            return state

        self._execute_route(state)
        self._save_outputs(state)
        return state

    def analyze_prompt(self, state: PostState) -> PostState:
        prompt = self._combined_prompt(state)
        lower = prompt.lower()

        state.needs_clarification = False
        state.clarification_question = None
        state.pending_clarification = None
        state.can_continue = True

        self._extract_existing_media_path(state, prompt)
        if not state.caption:
            state.caption = self._extract_caption(prompt)
        if not state.media_prompt:
            state.media_prompt = self._extract_media_prompt(prompt)
        if not state.topic:
            state.topic = self._extract_topic(prompt, state)
        if not state.platform:
            state.platform = self._extract_platform(lower)

        exact_text_requested = "exact text" in lower or "use this exact text" in lower
        if exact_text_requested and not state.caption:
            return self._ask(state, "exact_text", "Please provide the exact text you want me to use.")

        if self._is_empty_post_request(lower, state):
            return self._ask(state, "topic", "What content or topic should I post?")

        caption_only = self._is_caption_only_request(lower)
        needs_upload = self._needs_upload(lower)
        needs_media = self._needs_media(lower, needs_upload, caption_only, state)
        needs_research = self._needs_research(prompt, state)
        needs_writer = not bool(state.caption)

        if needs_upload and not state.platform:
            return self._ask(
                state,
                "platform",
                "Which platform should I post to? Instagram, TikTok, LinkedIn, X, or local demo?",
            )

        if MVP_DEMO_ONLY and needs_upload and state.platform in self.REAL_PLATFORMS:
            return self._ask(
                state,
                "demo_confirm",
                "This prototype supports local demo upload only. Should I continue with the demo upload page?",
            )

        if needs_upload and "upload this" in lower and not state.caption and not state.has_media_file and not state.topic:
            return self._ask(state, "caption_or_media", "Do you want me to create the caption, the image, or both?")

        if needs_media and not state.visual_style and not state.media_prompt:
            return self._ask(
                state,
                "visual_style",
                "What visual style do you prefer? Minimal, realistic, colorful, luxury, or fitness-focused?",
            )

        if needs_media and not state.media_prompt and not needs_writer:
            state.media_prompt = f"{state.visual_style or 'clean'} image about {state.topic or 'the requested topic'}"

        state.routing_plan = {
            "researcher": needs_research,
            "writer": needs_writer,
            "visual_prompt_engineer": needs_media and not state.has_media_file,
            "media_creator": needs_media and not state.has_media_file,
            "qa": True,
            "browser": needs_upload,
        }
        state.add_log("task_manager", "success", "Routing plan created.", routing_plan=state.routing_plan)
        return state

    def _build_nvidia_image_client(self, provider: str, image_provider: str) -> Optional[NvidiaBuildClient]:
        if image_provider not in {"nvidia", "auto"}:
            return None
        if not NVIDIA_API_KEY:
            if provider == "nvidia" or image_provider == "nvidia":
                return NvidiaBuildClient(model=NVIDIA_WRITER_MODEL)
            return None
        try:
            return NvidiaBuildClient(model=NVIDIA_WRITER_MODEL)
        except Exception:
            if image_provider == "nvidia":
                raise
            return None

    def _build_mistral_image_client(self, image_provider: str) -> Optional[MistralImageClient]:
        if image_provider not in {"mistral", "auto"}:
            return None
        if not MISTRAL_API_KEY and image_provider == "auto":
            return None
        return MistralImageClient(model=MISTRAL_IMAGE_MODEL)

    def merge_clarification(self, state: PostState, answer: str) -> PostState:
        cleaned = answer.strip()
        state.clarification_answer = cleaned
        state.clarification_count += 1
        state.clarification_history.append(
            {
                "question": state.clarification_question or "",
                "answer": cleaned,
                "field": state.pending_clarification or "unknown",
            }
        )

        field = state.pending_clarification
        if field == "platform":
            state.platform = self._normalize_platform(cleaned)
        elif field == "demo_confirm":
            if cleaned.lower() in {"yes", "y", "ok", "continue", "sure", "evet"}:
                state.platform = "local_demo"
            else:
                state.can_continue = False
        elif field == "exact_text":
            state.caption = cleaned.strip("\"'")
        elif field == "topic":
            state.topic = cleaned
        elif field == "visual_style":
            state.visual_style = cleaned
        elif field == "caption_or_media":
            if "caption" in cleaned.lower() or "both" in cleaned.lower():
                state.caption = None
            if "image" in cleaned.lower() or "media" in cleaned.lower() or "both" in cleaned.lower():
                state.media_prompt = state.media_prompt or f"local demo image about {state.topic or 'the request'}"
        else:
            state.topic = state.topic or cleaned

        state.add_log("task_manager", "clarification_received", "Clarification merged.", field=field)
        return state

    def _execute_route(self, state: PostState) -> PostState:
        if state.routing_plan.get("researcher"):
            self._run_with_retry(state, "researcher", self.researcher.get_trends, self._validate_research)
        else:
            state.add_log("researcher", "skipped", "Research skipped by routing plan.")

        if state.routing_plan.get("writer"):
            self._run_with_retry(state, "writer", self.writer.write_content, self._validate_writer)
        else:
            state.add_log("writer", "skipped", "Writer skipped because caption is already available.")

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
            action = lambda current: self.browser.upload_to_demo(
                current,
                self.output_dir,
                use_playwright=self.use_playwright,
            )
            self._run_with_retry(state, "browser", action, self._validate_browser)
        else:
            state.add_log("browser", "skipped", "Browser upload skipped by routing plan.")

        state.add_log("task_manager", "success", "Workflow finished.")
        return state

    def _repair_until_qa_approved(self, state: PostState) -> None:
        for repair_attempt in range(1, 3):
            if state.qa_status == "approved":
                return
            if not self._repair_after_qa_rejection(state, repair_attempt):
                return
            self._run_with_retry(state, "qa", self.qa_agent.review, self._validate_qa)

    def _repair_after_qa_rejection(self, state: PostState, repair_attempt: int) -> bool:
        feedback = state.qa_feedback or "QA rejected the post."
        lower = feedback.lower()

        unsafe_issue = any(word in lower for word in ("hateful", "violent", "illegal", "unsafe", "banned words"))
        if unsafe_issue:
            state.add_log("task_manager", "blocked", "QA rejection is safety-related; automatic repair skipped.")
            return False

        caption_issue = any(
            phrase in lower
            for phrase in (
                "caption",
                "incoherent",
                "placeholder",
                "instructional",
                "not aligned",
                "too long",
                "empty",
                "marketing message",
            )
        )
        media_issue = any(
            phrase in lower
            for phrase in (
                "media",
                "image",
                "file",
                "does not exist",
                "missing",
                "visual",
            )
        )
        prompt_issue = any(phrase in lower for phrase in ("placeholder", "instructional", "not aligned", "topic"))

        if not caption_issue and not media_issue and not prompt_issue:
            state.add_log("task_manager", "blocked", "QA rejection is not repairable by the current prototype.", feedback=feedback)
            return False

        state.can_continue = True
        state.add_log(
            "task_manager",
            "qa_repair",
            "QA rejected the post; sending feedback back through the agents.",
            attempt=repair_attempt,
            feedback=feedback,
        )

        if caption_issue:
            state.caption = None

        if prompt_issue or self._looks_instructional(state.media_prompt) or self._looks_instructional(state.optimized_media_prompt):
            state.media_prompt = None
            state.optimized_media_prompt = None
            state.negative_media_prompt = None
            state.visual_prompt_template = None

        if caption_issue or prompt_issue:
            self._run_with_retry(state, "writer", self.writer.write_content, self._validate_writer)

        should_rebuild_visual = state.routing_plan.get("visual_prompt_engineer", False) and (
            prompt_issue or media_issue or state.optimized_media_prompt is None
        )
        if should_rebuild_visual:
            self._run_with_retry(
                state,
                "visual_prompt_engineer",
                self.visual_prompt_engineer.refine_prompt,
                self._validate_visual_prompt,
            )

        should_rebuild_media = state.routing_plan.get("media_creator", False) and (
            media_issue or prompt_issue or not state.media_path or not Path(state.media_path).exists()
        )
        if should_rebuild_media:
            action = lambda current: self.media_creator.create_media(current, self.output_dir)
            self._run_with_retry(state, "media_creator", action, self._validate_media)

        return True

    def _looks_instructional(self, value: Optional[str]) -> bool:
        if not value:
            return False
        lower = value.lower()
        markers = ("yapmanı", "istiyorum", "şirketim", "post requirements", "create a social media image")
        return any(marker in lower for marker in markers)

    def _run_with_retry(self, state: PostState, name: str, action, validator) -> None:
        for attempt in range(1, 3):
            before_errors = len(state.errors)
            try:
                action(state)
            except Exception as exc:
                state.errors.append(f"{name} failed on attempt {attempt}: {exc}")
                state.add_log(name, "error", str(exc), attempt=attempt)

            valid, message = validator(state)
            if valid:
                state.add_log("task_manager", "validated", f"{name} output validated.", attempt=attempt)
                return

            if len(state.errors) == before_errors:
                state.errors.append(f"{name} validation failed on attempt {attempt}: {message}")
            state.add_log("task_manager", "retry" if attempt == 1 else "failed", message, agent=name, attempt=attempt)

        state.can_continue = False

    def _validate_research(self, state: PostState) -> tuple[bool, str]:
        if len(state.keywords) >= 3 and len(state.hashtags) >= 2:
            return True, "Research output is valid."
        return False, "Researcher must return at least 3 keywords and 2 hashtags."

    def _validate_writer(self, state: PostState) -> tuple[bool, str]:
        if not state.caption:
            return False, "Writer must return a caption."
        if state.routing_plan.get("media_creator") and not state.media_prompt:
            return False, "Writer must return a media prompt when media is needed."
        return True, "Writer output is valid."

    def _validate_visual_prompt(self, state: PostState) -> tuple[bool, str]:
        if not state.routing_plan.get("media_creator"):
            return True, "Visual prompt output is not required."
        if not state.visual_prompt_template:
            return False, "Visual prompt engineer must return a JSON prompt template."
        if not state.optimized_media_prompt:
            return False, "Visual prompt engineer must return optimized_media_prompt."
        return True, "Visual prompt output is valid."

    def _validate_media(self, state: PostState) -> tuple[bool, str]:
        if not state.media_path:
            return False, "Media creator did not return media_path."
        if not Path(state.media_path).exists():
            return False, f"Media path does not exist: {state.media_path}"
        return True, "Media output is valid."

    def _validate_qa(self, state: PostState) -> tuple[bool, str]:
        if state.qa_status in {"approved", "rejected"}:
            return True, "QA output is valid."
        return False, "QA must return approved or rejected."

    def _validate_browser(self, state: PostState) -> tuple[bool, str]:
        if state.browser_status == "success":
            return True, "Browser upload is valid."
        return False, state.browser_feedback or "Browser upload failed."

    def _save_outputs(self, state: PostState) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / "logs.json").write_text(json.dumps(state.logs, indent=2), encoding="utf-8")
        (self.output_dir / "state.json").write_text(json.dumps(state.to_dict(), indent=2), encoding="utf-8")

    def _clean_previous_media_outputs(self) -> None:
        for name in (
            "generated_post.jpg",
            "generated_post.png",
            "generated_post.nvidia_response.json",
            "generated_post.mistral_response.json",
            "generated_post.prompt.json",
            "browser_upload_manifest.json",
        ):
            path = self.output_dir / name
            if path.exists():
                path.unlink()

    def _ask(self, state: PostState, field: str, question: str) -> PostState:
        state.needs_clarification = True
        state.clarification_question = question
        state.pending_clarification = field
        state.can_continue = False
        return state

    def _combined_prompt(self, state: PostState) -> str:
        parts = [state.user_prompt]
        parts.extend(item["answer"] for item in state.clarification_history if item.get("field") == "topic")
        return " ".join(part for part in parts if part).strip()

    def _extract_caption(self, prompt: str) -> Optional[str]:
        patterns = [
            r"(?:exact text|caption|post text|text)\s*:\s*['\"]([^'\"]{2,2200})['\"]",
            r"(?:use|share|post)\s+this\s+exact\s+text\s*['\"]([^'\"]{2,2200})['\"]",
        ]
        for pattern in patterns:
            match = re.search(pattern, prompt, flags=re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None

    def _extract_media_prompt(self, prompt: str) -> Optional[str]:
        turkish_match = re.search(
            r"(?:burada|burda|görselde|fotoğrafta)\s+(.+?)\s+olsun",
            prompt,
            flags=re.IGNORECASE,
        )
        if turkish_match:
            return turkish_match.group(1).strip()

        match = re.search(
            r"(?:picture|image|photo|visual|video|reel)\s+(?:of|showing|with)\s+(.+?)(?:\.|,|$)",
            prompt,
            flags=re.IGNORECASE,
        )
        if match:
            return match.group(1).strip()
        return None

    def _extract_topic(self, prompt: str, state: PostState) -> Optional[str]:
        turkish_topic = self._extract_turkish_topic(prompt)
        if turkish_topic:
            return turkish_topic

        product_topic = extract_english_topic(prompt)
        if product_topic:
            return product_topic

        for pattern in (
            r"\babout\s+(.+?)(?:\s+with\b|\.|,|$)",
            r"\bfor\s+(?:a|an)?\s*(.+?)\s+post\b",
        ):
            match = re.search(pattern, prompt, flags=re.IGNORECASE)
            if match:
                topic = normalize_english_topic(match.group(1))
                if is_usable_english_topic(topic):
                    return topic

        if state.media_prompt:
            media_topic = normalize_english_topic(state.media_prompt)
            if is_usable_english_topic(media_topic):
                return media_topic

        cleaned = re.sub(r"['\"].*?['\"]", " ", prompt)
        cleaned = re.sub(
            r"\b(make|create|write|post|share|publish|upload|this|exact|text|caption|picture|image|photo|video|with|of|a|an|the|instagram|insta|account|seller|selling|want|should|must|realistic)\b",
            " ",
            cleaned,
            flags=re.IGNORECASE,
        )
        fallback_topic = normalize_english_topic(cleaned)
        return fallback_topic if is_usable_english_topic(fallback_topic) else self._clean_topic(cleaned)

    def _extract_turkish_topic(self, prompt: str) -> Optional[str]:
        lower = prompt.lower()
        if not any(marker in lower for marker in ("şirket", " için ", " olsun", "doğa", "malzeme", "ürün")):
            return None
        if "doğa spor" in lower:
            return "doğa sporları ekipmanları"
        for pattern in (
            r"şirketim\s+(.+?)\s+(?:satıyor|satmakta|için)",
            r"(.+?)\s+ile ilgili\s+(?:malzemeler|ürünler|ekipmanlar)",
            r"(.+?)\s+için\s+bir\s+post",
        ):
            match = re.search(pattern, prompt, flags=re.IGNORECASE)
            if match:
                topic = self._clean_topic(match.group(1).replace("ile ilgili", ""))
                if topic:
                    return topic
        return None

    def _clean_topic(self, text: str) -> Optional[str]:
        cleaned = " ".join(text.replace(":", " ").strip(" .,!?'\"").split())
        if not cleaned or cleaned.lower() in {"post", "this", "caption", "image", "picture"}:
            return None
        return cleaned[:80]

    def _extract_platform(self, lower_prompt: str) -> Optional[str]:
        for platform in self.LOCAL_PLATFORMS:
            if platform in lower_prompt:
                return self._normalize_platform(platform)
        for platform in self.REAL_PLATFORMS - {"x"}:
            if re.search(rf"\b{re.escape(platform)}\b", lower_prompt):
                return self._normalize_platform(platform)
        if re.search(r"\bx\b", lower_prompt):
            return "x"
        return None

    def _normalize_platform(self, value: str) -> str:
        lower = value.lower().strip()
        if lower in {"x", "twitter"}:
            return "x"
        if lower in self.LOCAL_PLATFORMS:
            return "local_demo"
        for platform in self.REAL_PLATFORMS:
            if platform in lower:
                return "x" if platform == "twitter" else platform
        return lower.replace(" ", "_") or "local_demo"

    def _extract_existing_media_path(self, state: PostState, prompt: str) -> None:
        if state.media_path:
            state.has_media_file = Path(state.media_path).exists()
            return
        match = re.search(r"([^\s'\"]+\.(?:jpg|jpeg|png|mp4))", prompt, flags=re.IGNORECASE)
        if match:
            media_path = Path(match.group(1)).expanduser()
            state.media_path = str(media_path)
            state.has_media_file = media_path.exists()
            state.media_type = "video" if media_path.suffix.lower() == ".mp4" else "image"

    def _is_empty_post_request(self, lower: str, state: PostState) -> bool:
        simple = lower.strip(" .!?")
        return simple in {"post this", "share this", "upload this", "post"} and not any(
            [state.caption, state.topic, state.media_prompt, state.has_media_file]
        )

    def _is_caption_only_request(self, lower: str) -> bool:
        if "caption only" in lower or "only caption" in lower:
            return True
        return lower.startswith("write a caption") or lower.startswith("create a caption")

    def _needs_upload(self, lower: str) -> bool:
        if "do not upload" in lower or "draft only" in lower or "no upload" in lower:
            return False
        if any(word in lower for word in self.UPLOAD_WORDS):
            return True
        if "post" in lower and any(word in lower for word in ("yap", "paylaş", "hazırla", "oluştur")):
            return True
        if lower.startswith("post ") or "make a post" in lower or "create a post" in lower:
            return True
        return bool(re.search(r"\b(make|create|build|generate)\b.+\bpost\b", lower))

    def _needs_media(self, lower: str, needs_upload: bool, caption_only: bool, state: PostState) -> bool:
        if caption_only or "text only" in lower or "no image" in lower or "without image" in lower:
            return False
        if state.has_media_file:
            return False
        if any(word in lower for word in self.MEDIA_WORDS):
            return True
        if any(word in lower for word in ("görsel", "fotoğraf", "resim", "video")):
            return True
        if needs_upload and any(word in lower for word in ("olsun", "dağda", "yürüyüş", "adam", "kadın")):
            return True
        return needs_upload and not caption_only

    def _needs_research(self, prompt: str, state: PostState) -> bool:
        lower = prompt.lower()
        if state.caption or "#" in prompt:
            return False
        if "trend" in lower or "viral" in lower or "popular hashtag" in lower:
            return True
        return len(prompt.split()) < 10
