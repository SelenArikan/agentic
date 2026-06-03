from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PROJECT_ROOT.parents[1]

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

if load_dotenv:
    load_dotenv(REPO_ROOT / ".env")
    load_dotenv(PROJECT_ROOT / ".env", override=True)

OUTPUT_DIR = Path(os.getenv("SOCIAL_AGENT_OUTPUT_DIR", PROJECT_ROOT / "outputs"))
BROWSER_DIR = PROJECT_ROOT / "browser"
DEMO_UPLOAD_PAGE = BROWSER_DIR / "demo_upload_page.html"

NVIDIA_BASE_URL = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")
NVIDIA_MODEL = os.getenv("NVIDIA_MODEL", "google/gemma-4-31b-it")
NVIDIA_RESEARCH_MODEL = os.getenv("NVIDIA_RESEARCH_MODEL", NVIDIA_MODEL)
NVIDIA_WRITER_MODEL = os.getenv("NVIDIA_WRITER_MODEL", NVIDIA_MODEL)
NVIDIA_QA_MODEL = os.getenv("NVIDIA_QA_MODEL", NVIDIA_MODEL)
NVIDIA_IMAGE_BASE_URL = os.getenv("NVIDIA_IMAGE_BASE_URL", "https://ai.api.nvidia.com/v1/genai")
NVIDIA_IMAGE_MODEL = os.getenv("NVIDIA_IMAGE_MODEL", "auto")
NVIDIA_IMAGE_CANDIDATES = [
    item.strip()
    for item in os.getenv(
        "NVIDIA_IMAGE_CANDIDATES",
        ",".join(
            [
                "black-forest-labs/flux.1-schnell",
                "stabilityai/stable-diffusion-3-medium",
                "stabilityai/stable-diffusion-xl",
                "briaai/bria-2.3",
                "nvidia/consistory",
            ]
        ),
    ).split(",")
    if item.strip()
]
NVIDIA_IMAGE_ENDPOINT = os.getenv("NVIDIA_IMAGE_ENDPOINT")
NVIDIA_IMAGE_STEPS = int(os.getenv("NVIDIA_IMAGE_STEPS", "50"))
NVIDIA_IMAGE_CFG_SCALE = float(os.getenv("NVIDIA_IMAGE_CFG_SCALE", "5"))
NVIDIA_IMAGE_ASPECT_RATIO = os.getenv("NVIDIA_IMAGE_ASPECT_RATIO", "1:1")
NVIDIA_IMAGE_NEGATIVE_PROMPT = os.getenv(
    "NVIDIA_IMAGE_NEGATIVE_PROMPT",
    "blurry, distorted anatomy, low resolution, watermark, text overlay",
)

MAX_CLARIFICATION_QUESTIONS = int(os.getenv("MAX_CLARIFICATION_QUESTIONS", "2"))
MVP_DEMO_ONLY = os.getenv("MVP_DEMO_ONLY", "true").lower() in {"1", "true", "yes"}
NVIDIA_IMAGE_FALLBACK_TO_PILLOW = os.getenv("NVIDIA_IMAGE_FALLBACK_TO_PILLOW", "false").lower() in {"1", "true", "yes"}
NVIDIA_QA_FALLBACK_TO_RULES = os.getenv("NVIDIA_QA_FALLBACK_TO_RULES", "true").lower() in {"1", "true", "yes"}

IMAGE_PROVIDER = os.getenv("IMAGE_PROVIDER", "nvidia")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
MISTRAL_BASE_URL = os.getenv("MISTRAL_BASE_URL", "https://api.mistral.ai/v1")
MISTRAL_IMAGE_MODEL = os.getenv("MISTRAL_IMAGE_MODEL", "mistral-medium-latest")
MISTRAL_IMAGE_FALLBACK_TO_PILLOW = os.getenv("MISTRAL_IMAGE_FALLBACK_TO_PILLOW", "false").lower() in {"1", "true", "yes"}
