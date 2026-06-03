from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents import ImprovedTaskManagerAgent, TaskManagerAgent
from config import OUTPUT_DIR
from main import summary as multi_agent_summary
from models import PostState


EXPERIMENT_DIR = OUTPUT_DIR / "assignment4_experiment"


@dataclass(frozen=True)
class TestCase:
    case_id: str
    category: str
    prompt: str
    expected_topic_terms: tuple[str, ...]
    expected_language: str
    expected_action: str
    expects_media: bool
    expects_upload: bool
    required_visual_groups: tuple[tuple[str, ...], ...] = ()
    forbidden_visual_terms: tuple[str, ...] = ()
    expected_caption: str = ""
    visual_style: str = "realistic"
    post_details: str = ""


TEST_CASES = [
    TestCase(
        case_id="A4_T1_short_pilates",
        category="clear short prompt",
        prompt="Make a post about Pilates.",
        expected_topic_terms=("pilates",),
        expected_language="en",
        expected_action="complete",
        expects_media=True,
        expects_upload=True,
        visual_style="fitness-focused",
    ),
    TestCase(
        case_id="A4_T2_ambiguous_this",
        category="low-confidence topic",
        prompt="Make a post about this and share it.",
        expected_topic_terms=(),
        expected_language="en",
        expected_action="clarify",
        expects_media=False,
        expects_upload=False,
    ),
    TestCase(
        case_id="A4_T3_outdoor_mat_pilates",
        category="visual constraint preservation",
        prompt="Make a Pilates post. The image must show outdoor mat Pilates in a park, not an indoor studio.",
        expected_topic_terms=("pilates",),
        expected_language="en",
        expected_action="complete",
        expects_media=True,
        expects_upload=True,
        required_visual_groups=(("outdoor", "park", "garden", "open sky"), ("mat pilates", "pilates mat", "yoga mat")),
        forbidden_visual_terms=("boutique pilates studio", "studio interior", "reformer machine"),
        visual_style="fitness-focused",
    ),
    TestCase(
        case_id="A4_T4_jewelry_constraints",
        category="product visual requirements",
        prompt=(
            "I am a seller on Instagram and I sell jewelry. Make a realistic post. "
            "The image should be a close-up of a woman's ear with three silver earrings."
        ),
        expected_topic_terms=("silver", "earring"),
        expected_language="en",
        expected_action="complete",
        expects_media=True,
        expects_upload=True,
        required_visual_groups=(
            ("close-up", "close up", "macro"),
            ("three earring", "3 earring"),
            ("silver earring", "silver jewelry"),
        ),
    ),
    TestCase(
        case_id="A4_T5_exact_caption",
        category="mixed caption and media intent",
        prompt="Share this exact text: 'Join my class!' with a picture of a reformer bed.",
        expected_topic_terms=("reformer",),
        expected_language="en",
        expected_action="complete",
        expects_media=True,
        expects_upload=True,
        expected_caption="Join my class!",
        visual_style="fitness-focused",
    ),
    TestCase(
        case_id="A4_T6_turkish_outdoor",
        category="Turkish visual details",
        prompt=(
            "şirketim doğa sporları ile ilgili malzemeler satıyor bunun için bir post yapmanı istiyorum "
            "burda dağda yürüyüş yapan bir adam olsun"
        ),
        expected_topic_terms=("doğa", "spor"),
        expected_language="tr",
        expected_action="complete",
        expects_media=True,
        expects_upload=True,
        required_visual_groups=(("outdoor", "mountain", "trail"), ("hiking", "hiker", "trekking")),
        post_details="mavi beyaz siyah tonlarında olsun daha çok cozy bir havası olsun",
    ),
    TestCase(
        case_id="A4_T7_caption_only",
        category="efficiency text-only route",
        prompt="Write only a caption for a luxury jewelry launch. No image. Draft only.",
        expected_topic_terms=("jewelry",),
        expected_language="en",
        expected_action="complete",
        expects_media=False,
        expects_upload=False,
        visual_style="luxury",
    ),
]


def main() -> None:
    args = parse_args()
    run_id = time.strftime("%Y%m%d_%H%M%S")
    output_dir = Path(args.output_dir) / run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for repeat in range(1, args.repeats + 1):
        for case in TEST_CASES:
            rows.append(run_system("original_multi_agent", TaskManagerAgent, case, repeat, output_dir, args))
            rows.append(run_system("improved_multi_agent", ImprovedTaskManagerAgent, case, repeat, output_dir, args))

    write_outputs(rows, output_dir)
    print(json.dumps({"output_dir": str(output_dir.resolve()), "runs": len(rows)}, indent=2))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Assignment 4 original vs improved multi-agent experiment.")
    parser.add_argument("--provider", choices=["mock", "nvidia"], default="mock")
    parser.add_argument("--image-provider", choices=["pillow", "nvidia", "mistral", "auto"], default="pillow")
    parser.add_argument("--output-dir", default=str(EXPERIMENT_DIR))
    parser.add_argument("--repeats", type=int, default=1)
    return parser.parse_args()


def run_system(
    system_name: str,
    manager_cls: type[TaskManagerAgent],
    case: TestCase,
    repeat: int,
    output_dir: Path,
    args: argparse.Namespace,
) -> dict:
    run_dir = output_dir / f"repeat_{repeat}" / system_name / case.case_id
    run_dir.mkdir(parents=True, exist_ok=True)
    state = make_state(case)
    ask_user = None if case.expected_action == "clarify" else experiment_answer(case)

    started = time.perf_counter()
    error = None
    try:
        manager = manager_cls(provider=args.provider, image_provider=args.image_provider, output_dir=run_dir)
        state = manager.run(state, ask_user=ask_user)
        raw_summary = multi_agent_summary(state, str(run_dir), args.provider)
    except Exception as exc:
        error = str(exc)
        state.add_log(system_name, "error", error)
        raw_summary = state.to_dict()
    latency_ms = round((time.perf_counter() - started) * 1000, 2)

    metrics = score_state(system_name, case, repeat, state, latency_ms, error)
    (run_dir / "summary.json").write_text(json.dumps(raw_summary, indent=2), encoding="utf-8")
    (run_dir / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return metrics


def make_state(case: TestCase) -> PostState:
    state = PostState(user_prompt=case.prompt)
    state.platform = "local_demo" if case.expects_upload or case.expected_action == "clarify" else "draft"
    state.visual_style = case.visual_style
    state.post_details = case.post_details or None
    return state


def experiment_answer(case: TestCase) -> Callable[[str], str]:
    def answer(question: str) -> str:
        lower = question.lower()
        if "approve final" in lower:
            return "yes"
        if "which platform" in lower:
            return "local demo"
        if "demo upload page" in lower:
            return "yes"
        if "visual style" in lower:
            return case.visual_style
        if "topic" in lower:
            return case.expected_topic_terms[0] if case.expected_topic_terms else "Pilates"
        if "exact text" in lower:
            return case.expected_caption or "Join my class!"
        if "caption, the image, or both" in lower:
            return "both"
        return "yes"

    return answer


def score_state(
    system_name: str,
    case: TestCase,
    repeat: int,
    state: PostState,
    latency_ms: float,
    error: str | None,
) -> dict:
    caption = state.caption or ""
    positive_visual = strip_avoidance_text(state.optimized_media_prompt or state.media_prompt or "")
    media_exists = bool(state.media_path and Path(state.media_path).exists())
    upload_success = state.browser_status == "success"
    clarification_success = int(state.needs_clarification and state.pending_clarification == "topic")

    if case.expected_action == "clarify":
        topic_score = clarification_success
        requirement_score = exact_caption_score = media_score = upload_score = qa_score = 1
        action_score = clarification_success
        completeness_score = clarification_success
        correctness_score = clarification_success
        overall_score = float(clarification_success)
    else:
        action_score = int(not state.needs_clarification)
        topic_score = score_terms(state.topic or "", case.expected_topic_terms)
        requirement_score = score_visual_requirements(positive_visual, case)
        exact_caption_score = int(not case.expected_caption or caption == case.expected_caption)
        media_score = int(not case.expects_media or media_exists)
        upload_score = int(not case.expects_upload or upload_success)
        qa_score = int(state.qa_status == "approved")
        language_score = int(language_matches(caption, case.expected_language))
        completeness_score = round((bool(caption) + media_score + upload_score + qa_score) / 4, 2)
        correctness_score = round((topic_score + requirement_score + language_score + exact_caption_score + qa_score) / 5, 2)
        overall_score = round(
            (topic_score * 0.2)
            + (requirement_score * 0.25)
            + (exact_caption_score * 0.1)
            + (completeness_score * 0.2)
            + (qa_score * 0.1)
            + (media_score * 0.05)
            + (upload_score * 0.05)
            + (action_score * 0.05),
            2,
        )

    return {
        "system": system_name,
        "case_id": case.case_id,
        "category": case.category,
        "repeat": repeat,
        "expected_action": case.expected_action,
        "topic": state.topic,
        "qa_status": state.qa_status,
        "browser_status": state.browser_status,
        "needs_clarification": state.needs_clarification,
        "caption_chars": len(caption),
        "media_exists": media_exists,
        "latency_ms": latency_ms,
        "log_count": len(state.logs),
        "agent_step_count": len({log.get("step") for log in state.logs}),
        "llm_step_proxy": llm_step_proxy(state),
        "brief_count": sum(1 for log in state.logs if log.get("step") == "request_brief_verifier"),
        "qa_repair_count": sum(
            1
            for log in state.logs
            if log.get("status") in {"qa_repair", "requirement_repair"}
        ),
        "human_approval_count": sum(1 for log in state.logs if log.get("step") == "human_approval"),
        "topic_score": topic_score,
        "requirement_score": requirement_score,
        "exact_caption_score": exact_caption_score,
        "clarification_score": clarification_success if case.expected_action == "clarify" else 1,
        "completeness_score": completeness_score,
        "correctness_score": correctness_score,
        "overall_score": overall_score,
        "error": error,
    }


def score_terms(value: str, expected_terms: tuple[str, ...]) -> float:
    if not expected_terms:
        return 1.0
    lower = value.lower()
    hits = sum(1 for term in expected_terms if term.lower() in lower)
    return round(hits / len(expected_terms), 2)


def score_visual_requirements(prompt: str, case: TestCase) -> float:
    lower = prompt.lower()
    required_scores = [int(any(alias in lower for alias in group)) for group in case.required_visual_groups]
    forbidden_ok = int(not any(term in lower for term in case.forbidden_visual_terms))
    scores = required_scores + ([forbidden_ok] if case.forbidden_visual_terms else [])
    return round(sum(scores) / len(scores), 2) if scores else 1.0


def strip_avoidance_text(value: str) -> str:
    return value.lower().split("avoid user constraint violations:", 1)[0]


def language_matches(caption: str, expected_language: str) -> bool:
    lower = caption.lower()
    markers = ("ğ", "ü", "ş", "ı", "ö", "ç", " için ", " mısın", " hazır")
    looks_turkish = any(marker in lower for marker in markers)
    return looks_turkish if expected_language == "tr" else bool(caption) and not looks_turkish


def llm_step_proxy(state: PostState) -> int:
    plan = state.routing_plan or {}
    if not plan:
        return 0
    return sum(1 for key in ("researcher", "writer", "visual_prompt_engineer", "qa") if plan.get(key) or key == "qa")


def write_outputs(rows: list[dict], output_dir: Path) -> None:
    aggregates = aggregate(rows)
    (output_dir / "results.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    (output_dir / "aggregate_summary.json").write_text(json.dumps(aggregates, indent=2), encoding="utf-8")
    with (output_dir / "results.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    (output_dir / "results_table.md").write_text(markdown_table(rows, aggregates), encoding="utf-8")


def aggregate(rows: list[dict]) -> dict:
    metrics = (
        "overall_score",
        "correctness_score",
        "requirement_score",
        "completeness_score",
        "latency_ms",
        "log_count",
        "llm_step_proxy",
        "qa_repair_count",
        "human_approval_count",
    )
    summary = {}
    for system in sorted({row["system"] for row in rows}):
        subset = [row for row in rows if row["system"] == system]
        summary[system] = {"runs": len(subset)}
        for metric in metrics:
            summary[system][f"mean_{metric}"] = round(statistics.mean(row[metric] for row in subset), 2)
        summary[system]["failure_rate"] = round(
            sum(1 for row in subset if failed(row)) / len(subset),
            2,
        )
    return summary


def failed(row: dict) -> bool:
    if row["error"]:
        return True
    if row["expected_action"] == "clarify":
        return not row["needs_clarification"]
    return row["qa_status"] != "approved"


def markdown_table(rows: list[dict], aggregates: dict) -> str:
    lines = [
        "# Assignment 4 Experiment Results",
        "",
        "## Aggregate Summary",
        "",
        "| System | Mean Overall | Correctness | Requirement | Completeness | Latency ms | Logs | LLM Step Proxy | QA Repairs | Human Approvals | Failure Rate |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for system, values in aggregates.items():
        lines.append(
            "| {system} | {mean_overall_score} | {mean_correctness_score} | {mean_requirement_score} | "
            "{mean_completeness_score} | {mean_latency_ms} | {mean_log_count} | {mean_llm_step_proxy} | "
            "{mean_qa_repair_count} | {mean_human_approval_count} | {failure_rate} |".format(system=system, **values)
        )

    lines.extend(
        [
            "",
            "## Per-Test Results",
            "",
            "| Case | System | Overall | Topic | Requirement | Clarification | QA | Browser | Topic Value | Logs |",
            "|---|---|---:|---:|---:|---:|---|---|---|---:|",
        ]
    )
    for row in rows:
        topic = str(row["topic"] or "").replace("|", "/")
        lines.append(
            f"| {row['case_id']} | {row['system']} | {row['overall_score']} | {row['topic_score']} | "
            f"{row['requirement_score']} | {row['clarification_score']} | {row['qa_status']} | "
            f"{row['browser_status']} | {topic} | {row['log_count']} |"
        )
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    main()
