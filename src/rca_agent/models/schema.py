"""Pydantic schema for a blameless Root Cause Analysis postmortem.

The ``BlamelessRCA`` model enforces a structured, repeatable format for
every incident investigation — ensuring nothing critical is missed and
that output is machine-parseable for downstream automation.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class BlamelessRCA(BaseModel):
    """Structured blameless postmortem produced by the investigator agent.

    This schema maps directly to the "5 Whys" investigation methodology
    and includes all sections expected in a production-grade postmortem
    document.
    """

    executive_summary: str = Field(
        ...,
        description=(
            "A concise 2–3 sentence summary of the incident: what broke, "
            "the user-visible impact, and the high-level root cause."
        ),
    )

    incident_timeline: list[str] = Field(
        ...,
        description=(
            "Chronological list of events mapping the structural decay — "
            "from the earliest contributing commit to the moment the fault "
            "became observable. Each entry should include a timestamp or "
            "commit reference."
        ),
        min_length=1,
    )

    root_cause_analysis: str = Field(
        ...,
        description=(
            "Deep-dive root cause analysis using the '5 Whys' methodology. "
            "Start from the observed symptom and iteratively ask 'Why?' "
            "until the fundamental systemic cause is identified."
        ),
    )

    blast_radius: list[str] = Field(
        ...,
        description=(
            "List of downstream components, services, or modules affected "
            "by this incident. Each entry should describe the component "
            "and how it was impacted."
        ),
    )

    preventative_action_items: list[str] = Field(
        ...,
        description=(
            "Concrete, actionable items to prevent recurrence. These should "
            "include CI/CD guardrails, automated checks, refactoring tasks, "
            "or process changes — each specific enough to be filed as a "
            "ticket."
        ),
        min_length=1,
    )
