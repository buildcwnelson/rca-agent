# rca-agent

**Autonomous Root Cause Analysis generator powered by Agno.**

Generates blameless postmortems from Git forensics using AI-driven "5 Whys" investigation.

## Features

- **Autonomous Incident Triage** — Pinpoint culprit commits directly from crash logs, stack traces, or stdin pipes
- **Multi-Commit Bisection** — Scan release windows (`--between v1.0..v1.1`) and rank suspect commits against incident symptoms
- **LGTM Stack Support** — Ingest Grafana Loki log query exports and Grafana Alerting webhooks
- **Automated Guardrail Generator** — Generate executable pytest reproduction tests and preventative code guardrails
- **Multi-Provider AI** — Native support for OpenRouter, Google Gemini, OpenAI, and local Ollama
- **Git Forensics** — Deep commit diffs, blame tracking, and chronological decay reconstruction
- **Executive PDF Reports** — High-resolution postmortem PDF generation with custom typography and alert callouts
- **Team Collaboration** — Automated Slack incident card alerts and formatted GitHub PR comments
- **Plugin Architecture** — Pluggy-based hook system for integration with external analyzers

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

### 1. Autonomous Triage (From Error Logs or Stack Traces)

No commit SHA needed. `rca-agent` parses the trace, finds the culprit commit using `git blame`, and runs the investigation:

```bash
# Triage a crash log file
rca-agent triage --log ./crash.log --path /path/to/repo --pdf ./report.pdf

# Triage from piped terminal output (CI / Kubernetes / Docker logs)
cat production-error.log | rca-agent triage --path /path/to/repo

# Triage directly from Grafana Loki JSON or Alert Webhook payload
rca-agent triage --lgtm ./loki-export.json --path /path/to/repo
```

### 2. Multi-Commit Release Window Bisection

Scan a deployment window of commits and isolate the breaking change matching a symptom:

```bash
rca-agent investigate \
  --between v1.2.0..HEAD \
  --symptom "Payment gateway timeout on checkout" \
  --path /path/to/repo \
  --pdf ./report.pdf
```

### 3. Commit Investigation & Automated Guardrails

```bash
# Basic investigation
rca-agent investigate --commit <hash> --path /path/to/repo

# Full enterprise workflow: PDF + Automated Regression Test + Slack Alert
rca-agent investigate \
  --commit <hash> \
  --path /path/to/repo \
  --pdf ./report.pdf \
  --generate-test ./tests/ \
  --slack-webhook https://hooks.slack.com/services/... \
  --markdown-pr ./pr_comment.md
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
