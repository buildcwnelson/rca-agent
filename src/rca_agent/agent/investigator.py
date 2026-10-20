"""The "5 Whys" Investigator Agent.

Configures an Agno ``Agent`` backed by Google Gemini (Google AI Studio),
bound to Git forensics tools, and constrained to produce output conforming
to the ``BlamelessRCA`` Pydantic schema.
"""

from __future__ import annotations

from agno.agent import Agent
from dotenv import load_dotenv
from pydantic import ValidationError

from rca_agent.agent.factory import create_model_instance, resolve_provider_and_key
from rca_agent.agent.tools import GitForensicsTools
from rca_agent.models.schema import BlamelessRCA

# Load environment variables from .env automatically
load_dotenv()

# ---------------------------------------------------------------------------
# System instructions for the investigator
# ---------------------------------------------------------------------------

SYSTEM_INSTRUCTIONS = """\
You are an expert Site Reliability Engineer conducting a blameless postmortem.

Given an architectural fault or failing commit, use your Git forensics tools
to investigate the timeline, identify the root cause using the "5 Whys"
framework, and generate actionable preventative guardrails.

## Investigation Protocol

1. **Gather Evidence** — Use `get_commit_diff` to inspect the changes
   introduced by the suspect commit.  Use `get_recent_logs` to understand
   the surrounding commit context.

2. **Trace the Timeline** — If the diff reveals affected files, use
   `get_blame_context` on critical code regions to reconstruct who
   changed what and when.

3. **Apply the "5 Whys"** — Starting from the observed symptom, ask
   "Why?" iteratively (at least 5 levels deep) until you reach the
   fundamental systemic cause — not just the proximate trigger.

4. **Assess Blast Radius** — Identify every downstream component,
   service, or module that was or could be affected.

5. **Prescribe Prevention** — Formulate concrete, ticket-ready action
   items: CI/CD guardrails, automated checks, refactoring tasks, or
   process changes.

## Important Guidelines

- This is a **blameless** postmortem.  Focus on systems and processes,
  never on individual people.
- Be specific and evidence-based.  Reference actual commit SHAs, file
  paths, and line numbers from your tool output.
- Every field in the output schema must be populated with substantive
  content.
"""


def create_investigator(
    model_id: str | None = None,
    api_key: str | None = None,
    provider: str | None = None,
) -> Agent:
    """Create and return a configured investigator agent.

    Parameters
    ----------
    model_id:
        Model identifier (e.g. ``gemini-3.6-flash``, ``anthropic/claude-3.5-sonnet``, ``gpt-4o``).
    api_key:
        Optional API key. Defaults to the respective environment variable.
    provider:
        Optional provider override (``gemini``, ``openrouter``, ``openai``, ``ollama``).

    Returns
    -------
    Agent
        A fully configured Agno agent ready to run investigations.
    """
    resolved_provider, resolved_model, resolved_api_key = resolve_provider_and_key(
        provider=provider, model=model_id, api_key=api_key
    )
    model = create_model_instance(
        provider=resolved_provider,
        model_id=resolved_model,
        api_key=resolved_api_key,
    )

    return Agent(
        model=model,
        tools=[GitForensicsTools()],
        instructions=SYSTEM_INSTRUCTIONS,
        output_schema=BlamelessRCA,
        description="Blameless RCA investigator using the 5 Whys framework",
        markdown=True,
    )


def run_investigation(
    commit_hash: str,
    model_id: str | None = None,
    api_key: str | None = None,
    provider: str | None = None,
) -> BlamelessRCA:
    """Run a full investigation and return the structured postmortem.

    Parameters
    ----------
    commit_hash:
        The Git SHA of the suspect commit to investigate.
    model_id:
        Model identifier.
    api_key:
        Optional API key.
    provider:
        Optional provider override (gemini, openrouter, openai, ollama).

    Returns
    -------
    BlamelessRCA
        The structured blameless postmortem.
    """
    agent = create_investigator(model_id=model_id, api_key=api_key, provider=provider)
    result = agent.run(
        f"Investigate commit {commit_hash}. Retrieve its diff, examine the "
        f"surrounding commit history, and if needed use blame to trace the "
        f"timeline.  Produce a complete blameless postmortem."
    )
    # When output_schema is set, result.content holds the parsed model
    if isinstance(result.content, BlamelessRCA):
        return result.content

    # Fallback: attempt to parse from raw content string
    if isinstance(result.content, str):
        try:
            return BlamelessRCA.model_validate_json(result.content)
        except (ValidationError, ValueError):
            raise RuntimeError(f"Agent response could not be parsed as RCA schema: {result.content}")

    # Final fallback: try dict-based construction
    try:
        return BlamelessRCA.model_validate(result.content)
    except Exception as exc:
        raise RuntimeError(
            f"Failed to generate structured postmortem (provider response: {result.content})"
        ) from exc
