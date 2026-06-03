# Single-Agent Baseline

This folder implements the Assignment 3 single-agent baseline for the same social media automation task solved by the multi-agent system.

## What is different?

- Multi-agent version: Task Manager routes work through Researcher, Writer, Visual Prompt Engineer, Media Creator, QA, and Browser Operator.
- Single-agent version: one `SingleSocialMediaAgent` performs planning, writing, media prompt generation, image generation/tool use, QA, repair, and local demo upload.

Both versions use the same `PostState` data model and comparable inputs/outputs, which makes response quality, latency, failure rate, and step count easier to compare.

## CLI

```bash
python3 projects/Smart_Social_Media_Agent_Orchestrator/single_agent_version/main.py \
  --provider mock \
  --image-provider pillow \
  "Make a post about Pilates."
```

## Web UI

```bash
python3 projects/Smart_Social_Media_Agent_Orchestrator/single_agent_version/web_app.py
```

Default URL:

```text
http://127.0.0.1:5052
```

The web UI reuses the same AetherFlow visual system as the multi-agent app, but the tracker shows only one agent.
