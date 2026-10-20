"""Git forensics utilities for repository telemetry extraction.

Provides functions to extract commit diffs, blame context, and recent log
history — the raw evidence the investigator agent uses to reconstruct the
timeline of an architectural fault.
"""

from __future__ import annotations

import os
from pathlib import Path

from git import Repo
from git.exc import GitCommandError

# ---------------------------------------------------------------------------
# Module-level repo handle
# ---------------------------------------------------------------------------

_repo: Repo | None = None


def _get_repo(repo_path: str | None = None) -> Repo:
    """Return a cached ``Repo`` instance, initializing on first call.

    Parameters
    ----------
    repo_path:
        Absolute or relative path to the Git repository root.  Falls back to
        the ``RCA_REPO_PATH`` environment variable, then to the current
        working directory.

    Raises
    ------
    InvalidGitRepositoryError
        If the resolved path is not inside a valid Git repository.
    """
    global _repo

    if _repo is not None and repo_path is None:
        return _repo

    resolved = repo_path or os.getenv("RCA_REPO_PATH", ".")
    resolved = str(Path(resolved).expanduser().resolve())

    _repo = Repo(resolved)
    return _repo


def set_repo_path(repo_path: str) -> None:
    """Explicitly (re-)set the repository path used by all forensics helpers.

    This is the preferred way to configure the repo path at application
    start-up so that every downstream call uses the same repository.
    """
    _get_repo(repo_path)


# ---------------------------------------------------------------------------
# Public forensics functions
# ---------------------------------------------------------------------------


def get_commit_diff(commit_hash: str) -> str:
    """Return the raw unified diff introduced by *commit_hash*.

    For merge commits the diff is computed against the first parent so that
    only the changes introduced by the merge are shown.

    Parameters
    ----------
    commit_hash:
        Full or abbreviated SHA of the target commit.

    Returns
    -------
    str
        The unified diff text.  Returns an error description string (never
        raises) when the commit cannot be found so the agent can reason
        about the failure.
    """
    try:
        repo = _get_repo()
        commit = repo.commit(commit_hash)

        if commit.parents:
            diff_text = repo.git.diff(commit.parents[0].hexsha, commit.hexsha)
        else:
            # Initial commit — use `git show` to get the patch
            diff_text = repo.git.show(commit.hexsha, "--format=", "--patch")

        return diff_text or "(empty diff)"
    except GitCommandError as exc:
        return f"[forensics error] Failed to retrieve diff for {commit_hash}: {exc}"
    except Exception as exc:
        return f"[forensics error] Unexpected error: {exc}"


def get_blame_context(filepath: str, line_start: int, line_end: int) -> str:
    """Return ``git blame`` output for a specific line range in *filepath*.

    Useful for identifying *who* last touched a code block and *when*,
    which helps the investigator reconstruct the timeline of structural
    decay.

    Parameters
    ----------
    filepath:
        Repository-relative path to the file (e.g. ``src/app/service.py``).
    line_start:
        First line of the region of interest (1-indexed, inclusive).
    line_end:
        Last line of the region of interest (1-indexed, inclusive).

    Returns
    -------
    str
        Raw blame output with commit SHAs, author, date, and line content.
    """
    try:
        repo = _get_repo()
        blame_output = repo.git.blame(
            f"-L{line_start},{line_end}",
            "--date=short",
            filepath,
        )
        return blame_output or "(no blame data)"
    except GitCommandError as exc:
        return f"[forensics error] Blame failed for {filepath}:{line_start}-{line_end}: {exc}"
    except Exception as exc:
        return f"[forensics error] Unexpected error: {exc}"


def get_recent_logs(target_hash: str, limit: int = 5) -> str:
    """Retrieve the *limit* commit messages immediately preceding *target_hash*.

    This gives the investigator agent temporal context — what was happening
    in the repository right before the fault was introduced.

    Parameters
    ----------
    target_hash:
        Full or abbreviated SHA of the commit to look back from.
    limit:
        Maximum number of preceding commits to include.

    Returns
    -------
    str
        Formatted log entries (hash, author, date, message) for the
        commits leading up to *target_hash*.
    """
    try:
        repo = _get_repo()
        log_output = repo.git.log(
            f"{target_hash}~{limit}..{target_hash}",
            "--oneline",
            "--no-merges",
            "--format=%h | %an | %ad | %s",
            "--date=short",
        )
        return log_output or "(no preceding commits found)"
    except GitCommandError:
        # Fallback: if the range is invalid (e.g. fewer commits exist),
        # just grab the last `limit` commits ending at target_hash.
        try:
            repo = _get_repo()
            log_output = repo.git.log(
                target_hash,
                f"-n{limit}",
                "--oneline",
                "--no-merges",
                "--format=%h | %an | %ad | %s",
                "--date=short",
            )
            return log_output or "(no preceding commits found)"
        except GitCommandError as exc:
            return f"[forensics error] Log retrieval failed for {target_hash}: {exc}"
    except Exception as exc:
        return f"[forensics error] Unexpected error: {exc}"
