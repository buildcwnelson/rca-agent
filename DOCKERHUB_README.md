# RCA-Agent: Autonomous Git Root Cause Analysis

RCA-Agent is an AI-powered Root Cause Analysis tool for developers, DevOps, and SRE teams. When a commit breaks your build or causes a production incident, RCA-Agent inspects the commit diff, runs forensics on the code changes, and writes an executive, blameless postmortem report.

---

## Supported Providers & Models

Set `RCA_LLM_PROVIDER` to one of the following exact provider values:

| Provider (`RCA_LLM_PROVIDER`) | Required API Key Variable | Recommended Model (`RCA_AGENT_MODEL` or `GEMINI_MODEL`) |
| :--- | :--- | :--- |
| `gemini` | `GEMINI_API_KEY` | `gemini-2.0-flash` (or `gemini-1.5-flash`) |
| `openrouter` | `OPENROUTER_API_KEY` | `anthropic/claude-3.5-sonnet` |
| `openai` | `OPENAI_API_KEY` | `gpt-4o` or `gpt-4o-mini` |
| `ollama` | *(None / Local)* | `qwen2.5-coder:7b` or `llama3.2` |

---

## Quickstart

Run RCA-Agent directly using Docker without installing Python, Git tools, or local dependencies.

### Step 1: Pull the Image
docker pull buildcwnelson/rca-agent:0.1.0

### Step 2: Create a .env File
Create a `.env` file in your working folder:

For Google Gemini (Free tier at aistudio.google.com):
```env
RCA_LLM_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.0-flash
```

For OpenRouter:
```env
RCA_LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=your_openrouter_api_key_here
OPENROUTER_MODEL=anthropic/claude-3.5-sonnet
```

For OpenAI:
```env
RCA_LLM_PROVIDER=openai
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o
```

---

### Step 3: Run an Investigation

Mount your target git repository into `/repo`:

```bash
docker run --rm \
  --env-file .env \
  -v /path/to/your/git-repo:/repo \
  buildcwnelson/rca-agent:0.1.0 \
  investigate <COMMIT_SHA> --path /repo
```

Replace `<COMMIT_SHA>` with the commit hash you want to analyze (or use `HEAD`, `HEAD~1`, etc.).

---

## Generating an Executive Blameless PDF Report

To export an executive-ready PDF report onto your host machine, mount a local output directory to `/output`:

```bash
docker run --rm \
  --env-file .env \
  -v /path/to/your/git-repo:/repo \
  -v $(pwd)/output:/output \
  buildcwnelson/rca-agent:0.1.0 \
  investigate <COMMIT_SHA> \
    --path /repo \
    --pdf /output/postmortem.pdf
```

The resulting PDF includes:
- **Executive Incident Summary**: High-level impact and blast radius.
- **Root Cause Analysis**: Line-by-line inspection of the breaking code logic.
- **Blameless 5 Whys**: Systemic breakdown focused on process and test gaps rather than human error.
- **Remediation & Action Items**: Short-term hotfix advice and long-term prevention measures.

---

## Multi-Architecture Support
Pre-built multi-architecture images are provided for:
- `linux/amd64` (Intel/AMD servers, CI/CD runners, cloud instances)
- `linux/arm64` (Apple Silicon M1/M2/M3/M4, AWS Graviton)

---

## Links
- **GitHub Repository**: https://github.com/buildcwnelson/rca-agent
- **Issue Tracker**: https://github.com/buildcwnelson/rca-agent/issues
