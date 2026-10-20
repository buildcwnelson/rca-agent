# rca-agent

**Autonomous Root Cause Analysis generator powered by Agno.**

Generates blameless postmortems from Git forensics using AI-driven "5 Whys" investigation.

## Features

- **Git Forensics** — Extracts commit diffs, blame context, and log timelines
- **5 Whys Investigation** — AI agent autonomously drills into root causes using Google Gemini
- **Blameless Postmortems** — Structured output via Pydantic schema
- **Executive PDF Reports** — High-resolution postmortem PDF generation with custom typography and alert callouts
- **Plugin Architecture** — Pluggy-based hook system for integration with external analyzers
- **Rich CLI** — Beautiful terminal output with color-coded blast radius and action items

## Configuration

`rca-agent` automatically auto-detects whichever provider API key is present in your environment or `.env` file:

```bash
cp .env.example .env
```

| Provider | Environment Variable | Default Model | Description |
|---|---|---|---|
| **OpenRouter** | `OPENROUTER_API_KEY` | `anthropic/claude-3.5-sonnet` | Universal router: Claude, Llama 3, DeepSeek, Mistral |
| **Google Gemini** | `GEMINI_API_KEY` | `gemini-3.6-flash` | Fast, high-token Google AI Studio reasoning |
| **OpenAI** | `OPENAI_API_KEY` | `gpt-4o-mini` | GPT-4o / o-series |
| **Ollama** | `OLLAMA_HOST` | `qwen2.5-coder:7b` | Air-gapped / local offline execution |

## Installation

```bash
pip install -e ".[dev]"
```

## Usage

### Standalone CLI

```bash
# Auto-detects provider from your active environment variables
rca-agent investigate --commit <hash> --path /path/to/repo

# Use OpenRouter explicitly with any model:
rca-agent investigate --commit <hash> --provider openrouter --model meta-llama/llama-3.3-70b-instruct

# Generate an Executive PDF Report
rca-agent investigate --commit <hash> --path /path/to/repo --pdf ./report.pdf
```

### Docker Quickstart (Zero-Install)

Run investigations on any local repository using Docker without needing Python or local dependencies:

```bash
# Using OpenRouter:
docker run --rm \
  -e OPENROUTER_API_KEY="sk-or-v1-..." \
  -v /path/to/target/repo:/repo \
  -v $(pwd)/output:/output \
  buildcwnelson/rca-agent:latest \
  investigate --commit <hash> --path /repo --pdf /output/report.pdf

# Using Google Gemini:
docker run --rm \
  -e GEMINI_API_KEY="AIzaSy..." \
  -v /path/to/target/repo:/repo \
  -v $(pwd)/output:/output \
  buildcwnelson/rca-agent:latest \
  investigate --commit <hash> --path /repo --pdf /output/report.pdf

# Using your existing .env file:
docker run --rm \
  --env-file .env \
  -v /path/to/target/repo:/repo \
  -v $(pwd)/output:/output \
  buildcwnelson/rca-agent:latest \
  investigate --commit <hash> --path /repo --pdf /output/report.pdf
```

### As a Plugin

```python
import pluggy
from rca_agent.plugin.hookspecs import RCAHookSpec

pm = pluggy.PluginManager("rca_agent")
pm.add_hookspecs(RCAHookSpec)
pm.load_setuptools_entrypoints("rca_agent")

result = pm.hook.on_violation_detected(violation_payload=payload)
```

## License

MIT
