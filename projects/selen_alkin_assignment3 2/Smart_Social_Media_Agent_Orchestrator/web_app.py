from __future__ import annotations

from datetime import datetime
from pathlib import Path
import copy
import sys
import threading

from flask import Flask, jsonify, redirect, render_template, request, send_from_directory, url_for
from werkzeug.utils import secure_filename

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents import TaskManagerAgent
from config import OUTPUT_DIR
from main import summary
from models import PostState


app = Flask(__name__, template_folder="web/templates", static_folder="web/static")
app.config["MAX_CONTENT_LENGTH"] = 12 * 1024 * 1024

WEB_RUNS_DIR = OUTPUT_DIR / "web_runs"
ALLOWED_UPLOAD_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
AGENT_ORDER = [
    ("task_manager", "Task Manager", "Analyzing request and routing agents"),
    ("researcher", "Trend Researcher", "Finding keywords and hashtags"),
    ("writer", "Content Writer", "Writing caption and image prompt"),
    ("visual_prompt_engineer", "Visual Prompt Engineer", "Structuring a professional photo brief"),
    ("media_creator", "Media Creator", "Generating or preparing visual"),
    ("qa", "QA Agent", "Checking quality and safety"),
    ("browser", "Browser Operator", "Preparing local demo upload"),
]

RUNS: dict[str, dict] = {}
RUNS_LOCK = threading.Lock()


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/generate", methods=["POST"])
def generate():
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    run_dir = WEB_RUNS_DIR / run_id
    upload_dir = run_dir / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)

    provider = request.form.get("provider", "nvidia")
    image_provider = request.form.get("image_provider", "nvidia")
    prompt = request.form.get("prompt", "").strip()
    post_details = request.form.get("post_details", "").strip()
    platform = request.form.get("platform", "local_demo").strip() or "local_demo"
    visual_style = request.form.get("visual_style", "").strip()
    exact_caption = request.form.get("exact_caption", "").strip()
    media_mode = request.form.get("media_mode", "generate")
    upload_mode = request.form.get("upload_mode", "local_demo")
    use_playwright = request.form.get("use_playwright") == "on"

    final_prompt = build_prompt(prompt, media_mode, upload_mode)
    state = PostState(user_prompt=final_prompt)
    state.post_details = post_details or None
    state.image_provider = image_provider
    state.platform = "local_demo" if upload_mode == "local_demo" else None
    state.visual_style = visual_style or None
    state.caption = exact_caption or None

    reference_path = save_reference_image(request.files.get("reference_image"), upload_dir)
    if reference_path:
        state.reference_image_path = str(reference_path)
        state.reference_image_note = (
            "The user uploaded a reference image. Use it as style/composition inspiration "
            "when writing the media prompt; do not copy logos or identifiable people."
        )
        if media_mode == "use_uploaded":
            state.media_path = str(reference_path)
            state.media_type = "image"
            state.has_media_file = True
            state.use_reference_as_final_media = True

    register_run(run_id, run_dir, state, provider)
    thread = threading.Thread(
        target=run_pipeline_background,
        args=(run_id, state, provider, image_provider, run_dir, use_playwright, prompt, visual_style, platform),
        daemon=True,
    )
    thread.start()
    return redirect(url_for("run_status", run_id=run_id))


@app.route("/run/<run_id>", methods=["GET"])
def run_status(run_id: str):
    with RUNS_LOCK:
        run = RUNS.get(run_id)
    if not run:
        return "Run not found", 404
    return render_template("run.html", run_id=run_id, agent_order=AGENT_ORDER)


@app.route("/api/run/<run_id>", methods=["GET"])
def api_run(run_id: str):
    with RUNS_LOCK:
        run = copy.deepcopy(RUNS.get(run_id))
    if not run:
        return jsonify({"error": "Run not found"}), 404
    return jsonify(public_run_payload(run_id, run))


@app.route("/result/<run_id>", methods=["GET"])
def result(run_id: str):
    with RUNS_LOCK:
        run = copy.deepcopy(RUNS.get(run_id))
    if not run:
        return "Run not found", 404

    state = run["state"]
    run_dir = Path(run["run_dir"])
    provider = run["provider"]
    result_data = summary(state, str(run_dir), provider)
    return render_template(
        "result.html",
        run_id=run_id,
        state=state,
        result=result_data,
        logs=state.logs,
        error=run.get("error"),
        generated_media_url=asset_url(state.media_path, run_dir, run_id),
        reference_image_url=asset_url(state.reference_image_path, run_dir, run_id),
    )


@app.route("/runs/<run_id>/<path:filename>", methods=["GET"])
def run_file(run_id: str, filename: str):
    return send_from_directory(WEB_RUNS_DIR / run_id, filename)


def register_run(run_id: str, run_dir: Path, state: PostState, provider: str) -> None:
    with RUNS_LOCK:
        RUNS[run_id] = {
            "status": "queued",
            "run_dir": str(run_dir),
            "provider": provider,
            "state": state,
            "error": None,
        }


def run_pipeline_background(
    run_id: str,
    state: PostState,
    provider: str,
    image_provider: str,
    run_dir: Path,
    use_playwright: bool,
    prompt: str,
    visual_style: str,
    platform: str,
) -> None:
    update_run(run_id, status="running", state=state)
    try:
        manager = TaskManagerAgent(provider=provider, image_provider=image_provider, output_dir=run_dir, use_playwright=use_playwright)
        state = manager.run(state, ask_user=web_default_answer(prompt, visual_style, platform))
        update_run(run_id, status="finished", state=state)
    except Exception as exc:
        state.add_log("web", "error", str(exc))
        update_run(run_id, status="error", state=state, error=str(exc))


def update_run(run_id: str, **changes) -> None:
    with RUNS_LOCK:
        if run_id not in RUNS:
            return
        RUNS[run_id].update(changes)


def public_run_payload(run_id: str, run: dict) -> dict:
    state: PostState = run["state"]
    run_dir = Path(run["run_dir"])
    return {
        "run_id": run_id,
        "status": run["status"],
        "error": run.get("error"),
        "logs": state.logs,
        "agents": agent_statuses(state.logs, run["status"]),
        "caption": state.caption,
        "topic": state.topic,
        "qa_status": state.qa_status,
        "qa_feedback": state.qa_feedback,
        "browser_status": state.browser_status,
        "image_provider": state.image_provider,
        "media_url": asset_url(state.media_path, run_dir, run_id),
        "reference_url": asset_url(state.reference_image_path, run_dir, run_id),
        "result_url": url_for("result", run_id=run_id) if run["status"] in {"finished", "error"} else None,
    }


def agent_statuses(logs: list[dict], run_status: str) -> list[dict]:
    statuses = []
    active = current_active_agent(logs, run_status)
    for key, label, description in AGENT_ORDER:
        related = [log for log in logs if log.get("step") == key]
        status = "waiting"
        message = description
        if related:
            last = related[-1]
            message = last.get("message", description)
            if last.get("status") in {"success", "approved", "validated"}:
                status = "done"
            elif last.get("status") in {"error", "rejected", "failed"}:
                status = "error"
            elif last.get("status") in {"skipped"}:
                status = "skipped"
            else:
                status = "active"
        if key == active and status not in {"done", "error", "skipped"}:
            status = "active"
        statuses.append({"key": key, "label": label, "description": description, "status": status, "message": message})
    return statuses


def current_active_agent(logs: list[dict], run_status: str) -> str | None:
    if run_status not in {"queued", "running"}:
        return None
    completed = set()
    for log in logs:
        step = log.get("step")
        if log.get("status") in {"success", "approved", "validated", "skipped"}:
            completed.add(step)
    for key, _label, _description in AGENT_ORDER:
        if key not in completed:
            return key
    return None


def build_prompt(prompt: str, media_mode: str, upload_mode: str) -> str:
    parts = [ensure_sentence_boundary(prompt)]
    if media_mode == "none":
        parts.append("No image. Text only.")
    elif media_mode == "use_uploaded":
        parts.append("Use the uploaded image as the final post media.")
    else:
        parts.append("Create a social media image for this post.")
    if upload_mode == "draft":
        parts.append("Draft only. Do not upload.")
    else:
        parts.append("Share this to the local demo upload page.")
    return " ".join(part for part in parts if part).strip()


def ensure_sentence_boundary(text: str) -> str:
    cleaned = text.strip()
    if cleaned and cleaned[-1] not in ".!?":
        return f"{cleaned}."
    return cleaned


def save_reference_image(file_storage, upload_dir: Path) -> Path | None:
    if not file_storage or not file_storage.filename:
        return None
    suffix = Path(file_storage.filename).suffix.lower()
    if suffix not in ALLOWED_UPLOAD_EXTENSIONS:
        raise ValueError("Reference image must be .jpg, .jpeg, .png, or .webp.")
    filename = secure_filename(file_storage.filename)
    target = upload_dir / filename
    file_storage.save(target)
    return target


def web_default_answer(prompt: str, visual_style: str, platform: str):
    def answer(question: str) -> str:
        lower = question.lower()
        if "which platform" in lower:
            return platform or "local demo"
        if "visual style" in lower:
            return visual_style or "fitness-focused"
        if "demo upload page" in lower:
            return "yes"
        if "topic" in lower:
            return prompt or "social media post"
        if "exact text" in lower:
            return "Use the caption provided in the web form."
        if "caption, the image, or both" in lower:
            return "both"
        return "local demo"

    return answer


def asset_url(path_value: str | None, run_dir: Path, run_id: str) -> str | None:
    if not path_value:
        return None
    path = Path(path_value)
    try:
        relative = path.resolve().relative_to(run_dir.resolve())
    except ValueError:
        return None
    return url_for("run_file", run_id=run_id, filename=str(relative))


if __name__ == "__main__":
    app.run(debug=True, port=5050)
