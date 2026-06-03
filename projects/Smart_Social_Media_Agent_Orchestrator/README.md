# Smart Social Media Agent Orchestrator

PRD-based MVP for a multi-agent social media post automation system.

The system uses a central `TaskManagerAgent` and six specialist agents:

- `TrendResearcherAgent`
- `ContentWriterAgent`
- `VisualPromptEngineerAgent`
- `MediaCreatorAgent`
- `QAAgent`
- `BrowserOperatorAgent`

The MVP is free by default: custom Python routing, mock trends, Pillow placeholder image generation, QA checks, and a local browser demo page. Real Instagram, TikTok, Facebook, LinkedIn, or X automation is intentionally out of scope for the MVP.

## Install

```bash
pip install -r projects/Smart_Social_Media_Agent_Orchestrator/requirements.txt
playwright install
```

`playwright install` is only needed when running with `--use-playwright`. The default CLI uses safe simulated demo upload.

## Run

Short prompt scenario:

```bash
python3 projects/Smart_Social_Media_Agent_Orchestrator/main.py \
  --demo-defaults \
  "Make a post about Pilates."
```

Detailed exact-caption scenario:

```bash
python3 projects/Smart_Social_Media_Agent_Orchestrator/main.py \
  --demo-defaults \
  "Share this exact text: 'Join my class!' with a picture of a reformer bed."
```

Ask clarification interactively:

```bash
python3 projects/Smart_Social_Media_Agent_Orchestrator/main.py "Post this."
```

Return the first clarification question without prompting:

```bash
python3 projects/Smart_Social_Media_Agent_Orchestrator/main.py --no-interactive "Post this."
```

## Web Frontend

Start the web UI:

```bash
python3 projects/Smart_Social_Media_Agent_Orchestrator/web_app.py
```

Open:

```text
http://127.0.0.1:5050
```

The frontend supports:

- Prompt and detailed post requirements.
- Provider selection: NVIDIA NIM or local mock.
- Platform and visual style selection.
- Image provider selection: NVIDIA FLUX candidates, Mistral `image_generation`, automatic fallback chain, or local Pillow placeholder.
- Optional exact caption.
- Optional reference image upload.
- Media mode: generate a new image, use uploaded image as final media, or text-only.
- Result view with caption, generated media, route plan, and agent timeline.
- Live orchestration screen that shows each agent moving from waiting to working to done while the pipeline runs.

The `VisualPromptEngineerAgent` runs between Writer and Media Creator. It converts rough media prompts into a professional JSON photo brief with subject, environment, composition, camera, lighting, style, quality modifiers, negative prompt, and final optimized prompt. This is written to `generated_post.prompt.json` for inspection.

Reference image note: the current hosted NVIDIA FLUX endpoint is text-to-image. Uploaded reference images are used as style/composition context in the media prompt unless you choose “Use uploaded image as final media”.

## NVIDIA Build / NIM

`--provider nvidia` uses NVIDIA NIM APIs for trend research, caption/media prompt writing, image generation, and QA. The Browser Operator still uploads to the local demo page because the PRD explicitly avoids real social media automation in MVP.

Create a project-local `.env` file so you do not need to export variables every terminal session:

```bash
cp projects/Smart_Social_Media_Agent_Orchestrator/.env.example \
  projects/Smart_Social_Media_Agent_Orchestrator/.env
```

Then edit:

```bash
nano projects/Smart_Social_Media_Agent_Orchestrator/.env
```

Put your real key in `NVIDIA_API_KEY`. The `.env` file is gitignored.

```bash
export NVIDIA_API_KEY="nvapi-..."
export NVIDIA_BASE_URL="https://integrate.api.nvidia.com/v1"
export NVIDIA_MODEL="google/gemma-4-31b-it"
export NVIDIA_RESEARCH_MODEL="google/gemma-4-31b-it"
export NVIDIA_WRITER_MODEL="google/gemma-4-31b-it"
export NVIDIA_QA_MODEL="google/gemma-4-31b-it"
export NVIDIA_IMAGE_BASE_URL="https://ai.api.nvidia.com/v1/genai"
export NVIDIA_IMAGE_MODEL="auto"
export NVIDIA_IMAGE_STEPS="50"

python3 projects/Smart_Social_Media_Agent_Orchestrator/main.py \
  --provider nvidia \
  --demo-defaults \
  "Make a post about Pilates."
```

Implemented NVIDIA NIM endpoints:

- Chat / text agents: `POST https://integrate.api.nvidia.com/v1/chat/completions`
- Text agent model defaults: `google/gemma-4-31b-it`
- Image generation default: `auto`, trying configured hosted candidates until one returns an image.

Default image candidates:

1. `black-forest-labs/flux.1-schnell`
2. `stabilityai/stable-diffusion-3-medium`
3. `stabilityai/stable-diffusion-xl`
4. `briaai/bria-2.3`
5. `nvidia/consistory`

NVIDIA Build labels change and some accounts can access endpoints that appear downloadable/deprecated in search results. The app now probes candidates in order and records the selected image model in `generated_post.nvidia_response.json`.

When `--provider nvidia` is used, NVIDIA failures are strict: the system logs the error instead of silently falling back to local Pillow generation.

QA exception: if NVIDIA QA is unavailable or degraded, local rule-based QA runs by default so a temporary model outage does not block the whole post pipeline. Disable this only when you want strict provider-only QA:

```bash
export NVIDIA_QA_FALLBACK_TO_RULES="false"
```

If you want a local Pillow image when the NVIDIA image endpoint is unavailable for your account, opt in explicitly:

```bash
export NVIDIA_IMAGE_FALLBACK_TO_PILLOW="true"
```

By default this is `false` so missing NVIDIA image access is visible during testing.

For lower latency or lower token use, switch the text agents to a smaller hosted Gemma endpoint:

```bash
export NVIDIA_MODEL="google/gemma-3n-e4b-it"
export NVIDIA_RESEARCH_MODEL="google/gemma-3n-e4b-it"
export NVIDIA_WRITER_MODEL="google/gemma-3n-e4b-it"
export NVIDIA_QA_MODEL="google/gemma-3n-e4b-it"
```

## Mistral Image Generation

Mistral does not expose a Stable-Diffusion-style standalone text-to-image model ID in this integration. The documented path is the Studio Conversations API with the built-in `image_generation` tool. The app sends `POST https://api.mistral.ai/v1/conversations` with `tools=[{"type":"image_generation"}]`, then downloads the generated PNG from `GET https://api.mistral.ai/v1/files/{file_id}/content`.

Use Mistral only for the media creator while keeping NVIDIA Gemma for the text agents:

```bash
export MISTRAL_API_KEY="..."
export IMAGE_PROVIDER="mistral"
export MISTRAL_IMAGE_MODEL="mistral-medium-latest"

python3 projects/Smart_Social_Media_Agent_Orchestrator/main.py \
  --provider nvidia \
  --image-provider mistral \
  --demo-defaults \
  "Make a post about Pilates."
```

You can also select `Mistral image_generation` from the web UI image-provider dropdown. If you want the system to try NVIDIA first and Mistral second, use:

```bash
python3 projects/Smart_Social_Media_Agent_Orchestrator/main.py \
  --provider nvidia \
  --image-provider auto \
  --demo-defaults \
  "Make a post about Pilates."
```

Mistral failures are strict by default, so missing API access is visible during testing. To allow local placeholder fallback:

```bash
export MISTRAL_IMAGE_FALLBACK_TO_PILLOW="true"
```

### Stable Diffusion 3.5 Large NIM

`stabilityai/stable-diffusion-3_5-large` is listed by NVIDIA Build as a downloadable NIM, not a hosted Free Endpoint. It must be run as a local container on supported NVIDIA GPU hardware first. After the container is running, point the app to the local NIM endpoint:

```bash
export NVIDIA_IMAGE_MODEL="stabilityai/stable-diffusion-3.5-large"
export NVIDIA_IMAGE_ENDPOINT="http://localhost:8000/v1/infer"
export NVIDIA_IMAGE_STEPS="30"

python3 projects/Smart_Social_Media_Agent_Orchestrator/main.py \
  --provider nvidia \
  --demo-defaults \
  "Make a post about Pilates."
```

The local SD 3.5 NIM endpoint returns `artifacts[0].base64`, which the app decodes into `outputs/generated_post.jpg`.

### FLUX.2 Klein 4B NIM

`black-forest-labs/flux.2-klein-4b` is also listed by NVIDIA Build as a downloadable NIM. After running the NIM locally, point the app to its local endpoint:

```bash
export NVIDIA_IMAGE_MODEL="black-forest-labs/flux.2-klein-4b"
export NVIDIA_IMAGE_ENDPOINT="http://localhost:8000/v1/infer"
export NVIDIA_IMAGE_STEPS="4"

python3 projects/Smart_Social_Media_Agent_Orchestrator/main.py \
  --provider nvidia \
  --demo-defaults \
  "Make a post about Pilates."
```

The FLUX.2 Klein local NIM payload uses `prompt`, `seed`, and `steps`, and returns `artifacts[0].base64`.

## Outputs

The system writes to `outputs/`:

- `logs.json`: step-by-step agent logs.
- `state.json`: full `PostState`.
- `generated_post.jpg` or `generated_post.png`: generated image. NVIDIA currently writes JPG-compatible output, Mistral writes PNG, and Pillow writes JPG.
- `generated_post.prompt.json`: original media prompt, optimized visual prompt, negative prompt, and professional prompt JSON template.
- `generated_post.nvidia_response.json`: raw NVIDIA image response, when image generation uses NVIDIA.
- `generated_post.mistral_response.json`: raw Mistral conversation response, when image generation uses Mistral.
- `browser_upload_manifest.json`: local demo upload payload.

## PRD Traceability

- Phase 1: project structure, requirements, README, outputs, agents, browser, tests.
- Phase 2: `PostRequest` and `PostState` dataclasses.
- Phase 3: Task Manager routing, validation, retry, clarification limit.
- Phase 4: mock Trend Researcher locally, NVIDIA NIM Trend Researcher in provider mode.
- Phase 5: Writer with local rules locally, NVIDIA NIM Writer in provider mode.
- Phase 6: Visual Prompt Engineer converts rough prompts into professional image JSON templates.
- Phase 7: Pillow Media Creator locally, NVIDIA FLUX NIM image generation, and optional Mistral `image_generation` media provider.
- Phase 7: QA Agent with local rules locally, NVIDIA NIM QA in provider mode plus media-file existence check.
- Phase 8: local demo page and optional Playwright upload.
- Phase 9: CLI main program.
- Phase 10: unit tests for routing, writing, QA, media creation, and pipeline scenarios.
