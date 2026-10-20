"""Autonomous triage utilities for stack traces, log files, and error symptoms.

Extracts file paths, line numbers, and error signatures from raw logs
and uses Git blame / pickaxe forensics to isolate culprit commit SHAs.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from git import Repo

# Regular expressions for common stack trace file-line patterns
# Python: File "/path/to/file.py", line 123, in func_name
PYTHON_TRACE_RE = re.compile(r'File\s+["\']([^"\']+\.py)["\'],\s+line\s+(\d+)(?:,\s+in\s+([a-zA-Z0-9_<>]+))?')

# JavaScript/TypeScript: at funcName (/path/to/file.ts:123:45) or at /path/to/file.js:123:45
JS_TRACE_RE = re.compile(r'at\s+(?:([a-zA-Z0-9_$.<>]+)\s+\()?(?:file:\/\/)?([^:()]+?\.[jt]sx?):(\d+)(?::\d+)?\)?')

# Generic: path/to/file.ext:123 or path/to/file.ext line 123
GENERIC_FILE_LINE_RE = re.compile(r'([a-zA-Z0-9_./\\-]+\.[a-zA-Z0-9_]+)[:\s]+(?:line\s+)?(\d+)')


@dataclass
class TraceFrame:
    """Represents a file location extracted from an error log or stack trace."""

    filepath: str
    line_number: int
    function_name: str | None = None
    snippet: str | None = None


@dataclass
class CulpritCandidate:
    """A commit suspected of introducing the defect."""

    commit_sha: str
    author: str
    authored_date: str
    summary: str
    file_path: str
    line_number: int
    confidence_score: float
    reason: str


def parse_trace_frames(log_text: str) -> list[TraceFrame]:
    """Parse stack trace lines and file references from raw log text.

    Returns frames in reverse order (deepest / most specific error frame first).
    """
    frames: list[TraceFrame] = []
    seen: set[tuple[str, int]] = set()

    # 1. Match Python tracebacks
    for match in PYTHON_TRACE_RE.finditer(log_text):
        path_str, line_str, func_str = match.groups()
        line_num = int(line_str)
        key = (path_str, line_num)
        if key not in seen:
            seen.add(key)
            frames.append(TraceFrame(filepath=path_str, line_number=line_num, function_name=func_str))

    # 2. Match JS/TS tracebacks
    for match in JS_TRACE_RE.finditer(log_text):
        func_str, path_str, line_str = match.groups()
        line_num = int(line_str)
        key = (path_str, line_num)
        if key not in seen:
            seen.add(key)
            frames.append(TraceFrame(filepath=path_str, line_number=line_num, function_name=func_str))

    # 3. Match generic file:line patterns if none found yet
    if not frames:
        for match in GENERIC_FILE_LINE_RE.finditer(log_text):
            path_str, line_str = match.groups()
            line_num = int(line_str)
            key = (path_str, line_num)
            if key not in seen:
                seen.add(key)
                frames.append(TraceFrame(filepath=path_str, line_number=line_num))

    is_python_trace = bool(PYTHON_TRACE_RE.search(log_text))
    # Python puts deepest crash site last; JS/Node/Java puts deepest crash site first
    return list(reversed(frames)) if is_python_trace else frames


def find_culprit_from_log(
    log_text: str,
    repo_path: str = ".",
) -> tuple[str | None, list[CulpritCandidate]]:
    """Analyze a crash log against Git forensics to find the culprit commit.

    Parameters
    ----------
    log_text:
        Raw log, exception stack trace, or error output.
    repo_path:
        Path to the target Git repository root.

    Returns
    -------
    tuple[str | None, list[CulpritCandidate]]
        Best culprit commit SHA (or None if no match), and full list of candidates.
    """
    repo = Repo(repo_path, search_parent_directories=True)
    repo_root = Path(repo.working_tree_dir).resolve()
    frames = parse_trace_frames(log_text)

    candidates: list[CulpritCandidate] = []
    seen_commits: set[str] = set()

    for index, frame in enumerate(frames):
        # Resolve frame file path relative to repository root
        raw_path = Path(frame.filepath)
        target_path: Path | None = None

        if raw_path.is_absolute():
            try:
                rel = raw_path.resolve().relative_to(repo_root)
                target_path = rel
            except ValueError:
                # File is outside repo root (e.g. system python lib)
                continue
        else:
            # Check relative paths
            candidate_file = repo_root / raw_path
            if candidate_file.exists():
                target_path = raw_path
            else:
                # Search for filename in repository
                matches = list(repo_root.glob(f"**/{raw_path.name}"))
                if matches:
                    target_path = matches[0].relative_to(repo_root)

        if not target_path:
            continue

        rel_path_str = str(target_path)
        try:
            # Run git blame on the specific line
            blame_entries = repo.blame("HEAD", rel_path_str, L=f"{frame.line_number},{frame.line_number}")
            for commit_obj, line_contents in blame_entries:
                sha = commit_obj.hexsha
                if sha in seen_commits:
                    continue
                seen_commits.add(sha)

                # Weight confidence: deepest frame gets higher score
                base_score = 0.90 if index == 0 else max(0.50, 0.90 - (index * 0.10))

                candidate = CulpritCandidate(
                    commit_sha=sha,
                    author=str(commit_obj.author),
                    authored_date=commit_obj.authored_datetime.isoformat(),
                    summary=commit_obj.summary,
                    file_path=rel_path_str,
                    line_number=frame.line_number,
                    confidence_score=round(base_score, 2),
                    reason=(
                        f"Direct git blame match at {rel_path_str}:{frame.line_number} "
                        f"(Frame #{index + 1} of traceback: {commit_obj.summary})"
                    ),
                )
                candidates.append(candidate)
        except Exception:
            continue

    if not candidates:
        # Fallback: Extract words that look like identifiers or exception messages and search recent commits
        return None, []

    # Sort candidates by confidence score descending
    candidates.sort(key=lambda c: c.confidence_score, reverse=True)
    best_sha = candidates[0].commit_sha if candidates else None

    return best_sha, candidates
