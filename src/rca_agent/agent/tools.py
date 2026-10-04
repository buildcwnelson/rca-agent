"""Agno tool wrappers for Git forensics functions.

Wraps the raw forensics utilities from ``core.forensics`` as an Agno
``Toolkit`` so the investigator agent can autonomously invoke them
during its "5 Whys" investigation.
"""

from __future__ import annotations

from agno.tools import Toolkit

from rca_agent.core.forensics import (
    get_blame_context as _get_blame_context,
)
from rca_agent.core.forensics import (
    get_commit_diff as _get_commit_diff,
)
from rca_agent.core.forensics import (
    get_recent_logs as _get_recent_logs,
)


class GitForensicsTools(Toolkit):
    """Agno toolkit exposing Git forensics capabilities to the agent.

    Usage::

        from rca_agent.agent.tools import GitForensicsTools
        agent = Agent(tools=[GitForensicsTools()])
    """

    def __init__(self) -> None:
        super().__init__(name="git_forensics")
        self.register(self.get_commit_diff)
        self.register(self.get_blame_context)
        self.register(self.get_recent_logs)

    def get_commit_diff(self, commit_hash: str) -> str:
        """Retrieve the raw unified diff for the specified commit.

        Use this tool to inspect exactly what code changes a commit
        introduced. Useful for identifying the specific lines that
        caused an architectural fault.

        Args:
            commit_hash: Full or abbreviated SHA of the target commit.

        Returns:
            The unified diff text for the commit.
        """
        return _get_commit_diff(commit_hash)

    def get_blame_context(self, filepath: str, line_start: int, line_end: int) -> str:
        """Get git blame output for a specific line range in a file.

        Use this tool to discover *who* last modified a block of code
        and *when*, helping reconstruct the timeline of structural
        decay leading to the incident.

        Args:
            filepath: Repository-relative path (e.g. ``src/app/service.py``).
            line_start: First line of the region (1-indexed, inclusive).
            line_end: Last line of the region (1-indexed, inclusive).

        Returns:
            Raw blame output with commit SHAs, author, date, and line content.
        """
        return _get_blame_context(filepath, line_start, line_end)

    def get_recent_logs(self, target_hash: str, limit: int = 5) -> str:
        """Retrieve commit messages immediately preceding the target commit.

        Use this tool to understand the temporal context — what was
        happening in the repository right before the fault was introduced.

        Args:
            target_hash: Full or abbreviated SHA to look back from.
            limit: Maximum number of preceding commits to include.

        Returns:
            Formatted log entries (hash, author, date, message).
        """
        return _get_recent_logs(target_hash, limit)
