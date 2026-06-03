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

from agents import TaskManagerAgent
from config import OUTPUT_DIR
from models import PostState
from single_agent_version.single_agent import SingleSocialMediaAgent, single_agent_summary
from main import summary as multi_agent_summary


EXPERIMENT_DIR = OUTPUT_DIR / "assignment3_experiment"


@dataclass(frozen=True)
class TestCase:
    case_id: str
    category: str
    prompt: str
    expected_topic_terms: tuple[str, ...]
    expected_language: str
    expects_media: bool
    expects_upload: bool
    visual_style: str = "realistic"
    post_details: str = ""


TEST_CASES = [
    TestCase(
        case_id="T1_short_pilates",
        category="short vague prompt",
        prompt="Make a post about Pilates.",
        expected_topic_terms=("pilates",),
        expected_language="en",
        expects_media=True,
        expects_upload=True,
        visual_style="fitness-focused",
    ),
    TestCase(
        case_id="T2_jewelry_detail",
        category="detailed English product prompt",
        prompt=(
            "I am a seller on instagram account and ı am selling jewerly can you make a post "
            "for my insta account, in the image I want you to make closer photage of a woman's ear. "
            "There shoukld be 3 earings in her ear and they must be made of silver. can you make realistic."
        ),
        expected_topic_terms=("silver", "earring"),
        expected_language="en",
        expects_media=True,
        expects_upload=True,
    ),
    TestCase(
        case_id="T3_turkish_outdoor",
        category="Turkish product prompt",
        prompt=(
            "şirketim doğa sporları ile ilgili malzemeler satıyor bunun için bir post yapmanı istiyorum "
            "burda dağda yürüyüş yapan bir adam olsun"
        ),
        expected_topic_terms=("doğa", "spor"),
        expected_language="tr",
        expects_media=True,
        expects_upload=True,
        post_details="mavi beyaz siyah tonlarında olsun daha çok cozy bir havası olsun",
    ),
    TestCase(
        case_id="T4_exact_caption",
        category="exact caption with image",
        prompt="Share this exact text: 'Join my class!' with a picture of a reformer bed.",
        expected_topic_terms=("reformer", "pilates"),
        expected_language="en",
        expects_media=True,
        expects_upload=True,
        visual_style="fitness-focused",
    ),
    TestCase(
        case_id="T5_text_only",
        category="text-only draft",
        prompt="Write only a caption for a luxury jewelry launch. No image. Draft only.",
        expected_topic_terms=("jewelry", "luxury"),
        expected_language="en",
        expects_media=False,
        expects_upload=False,
        visual_style="luxury",
    ),
]


class SimplifiedTaskManagerAgent(TaskManagerAgent):
    """Ablation: remove Researcher and Visual Prompt Engineer from the multi-agent pipeline."""

    def analyze_prompt(self, state: PostState) -> PostState:
        super().analyze_prompt(state)
        if state.routing_plan:
            state.routing_plan["researcher"] = False
            state.routing_plan["visual_prompt_engineer"] = False
            state.add_log(
                "task_manager",
                "ablation",
                "Ablation active: Researcher and Visual Prompt Engineer removed.",
                routing_plan=state.routing_plan,
            )
        return state


def main() -> None:
    args = parse_args()
    run_id = time.strftime("%Y%m%d_%H%M%S")
    output_dir = Path(args.output_dir) / run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for repeat in range(1, args.repeats + 1):
        for case in TEST_CASES:
            rows.append(run_system("multi_agent_full", case, repeat, output_dir, args.provider, args.image_provider))
            rows.append(run_system("multi_agent_simplified", case, repeat, output_dir, args.provider, args.image_provider))
            rows.append(run_system("single_agent", case, repeat, output_dir, args.provider, args.image_provider))

    write_outputs(rows, output_dir)
    print(json.dumps({"output_dir": str(output_dir.resolve()), "runs": len(rows)}, indent=2))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Assignment 3 single-agent vs multi-agent experiment.")
    parser.add_argument("--provider", choices=["mock", "nvidia"], default="mock")
    parser.add_argument("--image-provider", choices=["pillow", "nvidia", "mistral", "auto"], default="pillow")
    parser.add_argument("--output-dir", default=str(EXPERIMENT_DIR))
    parser.add_argument("--repeats", type=int, default=1)
    return parser.parse_args()


def run_system(
    system_name: str,
    case: TestCase,
    repeat: int,
    base_output_dir: Path,
    provider: str,
    image_provider: str,
) -> dict:
    run_dir = base_output_dir / f"repeat_{repeat}" / system_name / case.case_id
    run_dir.mkdir(parents=True, exist_ok=True)
    state = make_state(case)

    started_at = time.perf_counter()
    error = None
    try:
        if system_name == "single_agent":
            agent = SingleSocialMediaAgent(provider=provider, image_provider=image_provider, output_dir=run_dir)
            state = agent.run(state)
            raw_summary = single_agent_summary(state, str(run_dir), provider)
        else:
            manager_cls: type[TaskManagerAgent] = (
                SimplifiedTaskManagerAgent if system_name == "multi_agent_simplified" else TaskManagerAgent
            )
            manager = manager_cls(provider=provider, image_provider=image_provider, output_dir=run_dir)
            state = manager.run(state, ask_user=experiment_default_answer(case))
            raw_summary = multi_agent_summary(state, str(run_dir), provider)
    except Exception as exc:
        error = str(exc)
        state.add_log(system_name, "error", error)
        raw_summary = state.to_dict()
    latency_ms = round((time.perf_counter() - started_at) * 1000, 2)

    metrics = score_state(state, case, latency_ms, error, system_name, repeat)
    (run_dir / "summary.json").write_text(json.dumps(raw_summary, indent=2), encoding="utf-8")
    (run_dir / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return metrics


def make_state(case: TestCase) -> PostState:
    state = PostState(user_prompt=case.prompt)
    state.platform = "local_demo" if case.expects_upload else "draft"
    state.visual_style = case.visual_style
    state.post_details = case.post_details or None
    return state


def experiment_default_answer(case: TestCase) -> Callable[[str], str]:
    def answer(question: str) -> str:
        lower = question.lower()
        if "which platform" in lower:
            return "local demo"
        if "demo upload page" in lower:
            return "yes"
        if "visual style" in lower:
            return case.visual_style
        if "topic" in lower:
            return case.expected_topic_terms[0] if case.expected_topic_terms else "social media post"
        if "exact text" in lower:
            return "Join my class!"
        if "caption, the image, or both" in lower:
            return "both"
        return "local demo"

    return answer


def score_state(
    state: PostState,
    case: TestCase,
    latency_ms: float,
    error: str | None,
    system_name: str,
    repeat: int,
) -> dict:
    caption = state.caption or ""
    topic = state.topic or ""
    media_prompt = state.optimized_media_prompt or state.media_prompt or ""
    media_exists = bool(state.media_path and Path(state.media_path).exists())
    upload_success = state.browser_status == "success"

    topic_score = score_topic(topic, caption, media_prompt, case.expected_topic_terms)
    language_score = 1 if language_matches(caption, case.expected_language) else 0
    media_score = 1 if (not case.expects_media or media_exists) else 0
    upload_score = 1 if (not case.expects_upload or upload_success) else 0
    qa_score = 1 if state.qa_status == "approved" else 0
    consistency_score = 1 if is_consistent(topic, caption, media_prompt, case.expected_topic_terms) else 0
    completeness_score = round((bool(caption) + media_score + upload_score + qa_score) / 4, 2)
    correctness_score = round((topic_score + language_score + qa_score) / 3, 2)
    overall_score = round(
        (correctness_score * 0.35)
        + (completeness_score * 0.25)
        + (consistency_score * 0.2)
        + (media_score * 0.1)
        + (upload_score * 0.1),
        2,
    )

    return {
        "system": system_name,
        "case_id": case.case_id,
        "category": case.category,
        "repeat": repeat,
        "expected_language": case.expected_language,
        "expected_media": case.expects_media,
        "expected_upload": case.expects_upload,
        "topic": topic,
        "caption_chars": len(caption),
        "media_exists": media_exists,
        "qa_status": state.qa_status,
        "browser_status": state.browser_status,
        "latency_ms": latency_ms,
        "log_count": len(state.logs),
        "agent_step_count": len({log.get("step") for log in state.logs}),
        "llm_step_proxy": llm_step_proxy(system_name, state),
        "error": error,
        "topic_score": topic_score,
        "language_score": language_score,
        "media_score": media_score,
        "upload_score": upload_score,
        "qa_score": qa_score,
        "consistency_score": consistency_score,
        "completeness_score": completeness_score,
        "correctness_score": correctness_score,
        "overall_score": overall_score,
    }


def score_topic(topic: str, caption: str, media_prompt: str, expected_terms: tuple[str, ...]) -> float:
    haystack = f"{topic} {caption} {media_prompt}".lower()
    if not expected_terms:
        return 1.0
    hits = sum(1 for term in expected_terms if term.lower() in haystack)
    return round(hits / len(expected_terms), 2)


def language_matches(caption: str, expected_language: str) -> bool:
    lower = caption.lower()
    turkish_markers = ("ğ", "ü", "ş", "ı", "ö", "ç", " için ", " mısın", " hazır")
    looks_turkish = any(marker in lower for marker in turkish_markers)
    return looks_turkish if expected_language == "tr" else not looks_turkish


def is_consistent(topic: str, caption: str, media_prompt: str, expected_terms: tuple[str, ...]) -> bool:
    combined = f"{topic} {caption} {media_prompt}".lower()
    if not topic or not caption:
        return False
    return any(term.lower() in combined for term in expected_terms)


def llm_step_proxy(system_name: str, state: PostState) -> int:
    if system_name == "single_agent":
        return 1
    plan = state.routing_plan or {}
    return sum(
        1
        for key in ("researcher", "writer", "visual_prompt_engineer", "qa")
        if plan.get(key, False) or key == "qa"
    )


def write_outputs(rows: list[dict], output_dir: Path) -> None:
    json_path = output_dir / "results.json"
    csv_path = output_dir / "results.csv"
    md_path = output_dir / "results_table.md"
    summary_path = output_dir / "aggregate_summary.json"

    json_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    aggregates = aggregate(rows)
    summary_path.write_text(json.dumps(aggregates, indent=2), encoding="utf-8")
    md_path.write_text(markdown_table(rows, aggregates), encoding="utf-8")


def aggregate(rows: list[dict]) -> dict:
    systems = sorted({row["system"] for row in rows})
    data = {}
    for system in systems:
        subset = [row for row in rows if row["system"] == system]
        data[system] = {
            "runs": len(subset),
            "mean_overall_score": round(statistics.mean(row["overall_score"] for row in subset), 2),
            "mean_correctness_score": round(statistics.mean(row["correctness_score"] for row in subset), 2),
            "mean_completeness_score": round(statistics.mean(row["completeness_score"] for row in subset), 2),
            "mean_consistency_score": round(statistics.mean(row["consistency_score"] for row in subset), 2),
            "mean_latency_ms": round(statistics.mean(row["latency_ms"] for row in subset), 2),
            "mean_log_count": round(statistics.mean(row["log_count"] for row in subset), 2),
            "mean_llm_step_proxy": round(statistics.mean(row["llm_step_proxy"] for row in subset), 2),
            "failure_rate": round(sum(1 for row in subset if row["error"] or row["qa_status"] != "approved") / len(subset), 2),
        }
    return data


def markdown_table(rows: list[dict], aggregates: dict) -> str:
    lines = [
        "# Assignment 3 Experiment Results",
        "",
        "## Aggregate Summary",
        "",
        "| System | Mean Overall | Mean Correctness | Mean Completeness | Mean Consistency | Mean Latency ms | Mean Logs | LLM Step Proxy | Failure Rate |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for system, values in aggregates.items():
        lines.append(
            "| {system} | {mean_overall_score} | {mean_correctness_score} | {mean_completeness_score} | "
            "{mean_consistency_score} | {mean_latency_ms} | {mean_log_count} | {mean_llm_step_proxy} | {failure_rate} |".format(
                system=system,
                **values,
            )
        )

    lines.extend(
        [
            "",
            "## Per-Test Results",
            "",
            "| Case | System | Overall | Correctness | Completeness | Consistency | Latency ms | Logs | QA | Browser | Topic |",
            "|---|---|---:|---:|---:|---:|---:|---:|---|---|---|",
        ]
    )
    for row in rows:
        topic = str(row["topic"]).replace("|", "/")
        lines.append(
            f"| {row['case_id']} | {row['system']} | {row['overall_score']} | {row['correctness_score']} | "
            f"{row['completeness_score']} | {row['consistency_score']} | {row['latency_ms']} | {row['log_count']} | "
            f"{row['qa_status']} | {row['browser_status']} | {topic} |"
        )
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    main()
