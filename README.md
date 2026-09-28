# rca-agent

**Autonomous Root Cause Analysis generator powered by Agno.**

Generates blameless postmortems from Git forensics using AI-driven "5 Whys" investigation.

## Features

- **Git Forensics** — Extracts commit diffs, blame context, and log timelines
- **5 Whys Investigation** — AI agent autonomously drills into root causes
- **Blameless Postmortems** — Structured output via Pydantic schema
- **Plugin Architecture** — Pluggy-based hook system for integration with external analyzers
- **Rich CLI** — Beautiful terminal output with color-coded blast radius and action items

## Installation

```bash
pip install -e ".[dev]"
```

## Usage

### Standalone CLI

```bash
rca-agent investigate --commit <hash> --path /path/to/repo
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
