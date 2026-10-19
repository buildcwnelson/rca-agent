"""Pluggy hook implementation for rca-agent.

This module implements the ``on_violation_detected`` hook.  When invoked
by a host application (e.g. Pytrack), it feeds the provided violation
context directly to the Agno investigator agent — bypassing manual Git
fetching — and returns the serialized ``BlamelessRCA`` postmortem.
"""

from __future__ import annotations

import json
import logging

import pluggy
from pydantic import ValidationError

from rca_agent.agent.investigator import create_investigator
from rca_agent.core.forensics import set_repo_path
from rca_agent.models.schema import BlamelessRCA

log = logging.getLogger(__name__)

hookimpl = pluggy.HookimplMarker("rca_agent")


class RCAPlugin:
    """Pluggy hook implementation that bridges external tools to the agent.

    Registered as a setuptools entry point under the ``rca_agent``
    namespace so host applications can discover it automatically via
    ``pm.load_setuptools_entrypoints("rca_agent")``.
    """

    @hookimpl
    def on_violation_detected(self, violation_payload: dict) -> dict:
        """Accept a violation payload and return a blameless RCA.

        The implementation bypasses manual Git fetching when a ``context``
        key is present in the payload — feeding the pre-assembled context
        directly to the investigator agent.  When no context is provided,
        it falls back to using the commit hash with Git forensics tools.

        Parameters
        ----------
        violation_payload:
            Dictionary conforming to the ``RCAHookSpec`` contract.

        Returns
        -------
        dict
            Serialized ``BlamelessRCA`` model.
        """
        commit_hash = violation_payload.get("commit_hash", "unknown")
        description = violation_payload.get("description", "")
        affected_files = violation_payload.get("affected_files", [])
        severity = violation_payload.get("severity", "warning")
        pre_assembled_context = violation_payload.get("context", "")
        repo_path = violation_payload.get("repo_path")
        model_id = violation_payload.get("model_id", "gemini-2.5-flash")
        api_key = violation_payload.get("api_key")

        log.info(
            "RCA plugin invoked for commit %s (severity=%s, files=%d)",
            commit_hash,
            severity,
            len(affected_files),
        )

        # If the host supplies a repo path, configure forensics to use it
        if repo_path:
            set_repo_path(repo_path)

        # Build the investigation prompt
        prompt_parts = [
            f"Investigate the following architectural violation (severity: {severity}).",
            f"Commit: {commit_hash}",
        ]

        if description:
            prompt_parts.append(f"Description: {description}")

        if affected_files:
            prompt_parts.append(f"Affected files: {', '.join(affected_files)}")

        if pre_assembled_context:
            # Bypass manual Git fetching — feed context directly
            prompt_parts.append(
                "The following pre-assembled context has been provided by the "
                "host system.  Use this as your primary evidence source, and "
                "only call Git forensics tools if you need additional detail."
            )
            prompt_parts.append(
                f"--- BEGIN CONTEXT ---\n{pre_assembled_context}\n--- END CONTEXT ---"
            )
        else:
            prompt_parts.append(
                "Use your Git forensics tools to gather evidence: retrieve "
                "the commit diff, examine the surrounding log history, and "
                "run blame on critical code regions."
            )

        prompt_parts.append(
            "Produce a complete blameless postmortem following the 5 Whys framework."
        )

        prompt = "\n\n".join(prompt_parts)

        # Run the investigator
        agent = create_investigator(model_id=model_id, api_key=api_key)
        result = agent.run(prompt)

        # Parse and serialize the output
        if isinstance(result.content, BlamelessRCA):
            return result.content.model_dump()

        if isinstance(result.content, str):
            try:
                rca = BlamelessRCA.model_validate_json(result.content)
                return rca.model_dump()
            except (ValidationError, ValueError):
                # Attempt dict-based parsing
                try:
                    data = json.loads(result.content)
                    rca = BlamelessRCA.model_validate(data)
                    return rca.model_dump()
                except (ValidationError, ValueError, json.JSONDecodeError):
                    log.warning("Could not parse agent output as BlamelessRCA")
                    return {
                        "executive_summary": result.content,
                        "incident_timeline": [f"Commit {commit_hash} flagged"],
                        "root_cause_analysis": "Agent output could not be parsed into structured format.",
                        "blast_radius": affected_files,
                        "preventative_action_items": ["Review raw agent output manually"],
                    }

        if isinstance(result.content, dict):
            rca = BlamelessRCA.model_validate(result.content)
            return rca.model_dump()

        return BlamelessRCA.model_validate(result.content).model_dump()
