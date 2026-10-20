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

Set your Google AI Studio API key in a `.env` file (or export it in your environment):

```bash
cp .env.example .env
# Edit .env with your key:
# GEMINI_API_KEY=your_key_here
# GEMINI_MODEL=gemini-3.6-flash
```

## Installation

```bash
pip install -e ".[dev]"
```

## Usage

### Standalone CLI

```bash
# Terminal investigation
rca-agent investigate --commit <hash> --path /path/to/repo

# Investigation with Executive PDF Report
rca-agent investigate --commit <hash> --path /path/to/repo --pdf ./report.pdf
```

### Docker Quickstart (Zero-Install)

Run investigations on any local repository using Docker without needing Python or local dependencies:

```bash
docker run --rm \
  -e GEMINI_API_KEY="your-gemini-api-key" \
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
