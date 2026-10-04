"""Pluggy hook specifications for the rca-agent plugin interface.

Host applications (e.g. Pytrack) register these hook specs and then
load rca-agent's implementation via setuptools entry points.  This
establishes the contract between the host and the RCA plugin.
"""

from __future__ import annotations

import pluggy

hookspec = pluggy.HookspecMarker("rca_agent")


class RCAHookSpec:
    """Hook specification namespace for rca-agent plugins.

    Any host application wanting to integrate rca-agent should add this
    spec to its ``PluginManager`` and then call
    ``pm.load_setuptools_entrypoints("rca_agent")`` to discover
    implementations.
    """

    @hookspec
    def on_violation_detected(self, violation_payload: dict) -> dict:
        """Invoked when an architectural violation is detected.

        Parameters
        ----------
        violation_payload:
            A dictionary containing violation context.  Expected keys:

            - ``commit_hash`` (str): The SHA of the offending commit.
            - ``description`` (str): Human-readable description of the
              violation.
            - ``affected_files`` (list[str]): Files involved in the
              violation.
            - ``severity`` (str): One of ``"critical"``, ``"warning"``,
              ``"info"``.
            - ``context`` (str, optional): Additional context such as
              diff output or rule details that the agent can use
              directly, bypassing manual Git fetching.

        Returns
        -------
        dict
            A serialized ``BlamelessRCA`` postmortem containing:
            ``executive_summary``, ``incident_timeline``,
            ``root_cause_analysis``, ``blast_radius``, and
            ``preventative_action_items``.
        """
