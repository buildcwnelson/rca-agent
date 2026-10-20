"""Multi-commit release window analysis utilities.

Scans commit ranges (e.g. v1.0.0..v1.1.0 or SHA1..SHA2), extracts modified files
and diff churn, and correlates commit messages against reported incident symptoms.
"""

from __future__ import annotations

from dataclasses import dataclass

from git import Repo


@dataclass
class RangeCommitMatch:
    """A commit in the release window scored against the reported incident symptom."""

    commit_sha: str
    author: str
    authored_date: str
    summary: str
    files_changed: list[str]
    score: float
    matched_keywords: list[str]


def parse_commit_range(
    repo_path: str,
    commit_range: str,
    symptom: str | None = None,
    limit: int = 30,
) -> list[RangeCommitMatch]:
    """Inspect all commits in a revision range and rank them against a symptom.

    Parameters
    ----------
    repo_path:
        Path to the target Git repository root.
    commit_range:
        Standard Git revision range (e.g. ``v1.0.0..HEAD`` or ``abc123..def456``).
    symptom:
        Optional error message, subsystem name, or incident keyword string.
    limit:
        Maximum number of commits to analyze in the range.

    Returns
    -------
    list[RangeCommitMatch]
        Ranked list of suspect commits in the range.
    """
    repo = Repo(repo_path, search_parent_directories=True)

    # Resolve commits in range
    try:
        commits = list(repo.iter_commits(commit_range, max_count=limit))
    except Exception:
        # If range fails, try triple-dot or fallback
        commits = []

    if not commits:
        return []

    symptom_tokens: set[str] = set()
    if symptom:
        # Tokenize symptom string (lowercase, ignore common stop words)
        raw_words = symptom.lower().replace(":", " ").replace("/", " ").replace(".", " ").split()
        stop_words = {"the", "a", "an", "in", "on", "at", "to", "for", "of", "and", "or", "is", "was"}
        symptom_tokens = {w for w in raw_words if len(w) > 2 and w not in stop_words}

    results: list[RangeCommitMatch] = []

    for commit in commits:
        # Collect touched files
        files_touched: list[str] = []
        try:
            if commit.parents:
                diffs = commit.parents[0].diff(commit)
                files_touched = [d.b_path or d.a_path for d in diffs if (d.b_path or d.a_path)]
            else:
                files_touched = list(commit.stats.files.keys())
        except Exception:
            files_touched = []

        # Calculate keyword match score
        score = 0.10  # Baseline presence score
        matched: list[str] = []

        summary_lower = commit.summary.lower()
        message_lower = commit.message.lower()

        for token in symptom_tokens:
            if token in summary_lower:
                score += 0.40
                matched.append(token)
            elif token in message_lower:
                score += 0.20
                matched.append(token)

            # Check if file path matches keyword
            for f in files_touched:
                if token in f.lower():
                    score += 0.30
                    matched.append(f)
                    break

        results.append(
            RangeCommitMatch(
                commit_sha=commit.hexsha,
                author=str(commit.author),
                authored_date=commit.authored_datetime.isoformat(),
                summary=commit.summary,
                files_changed=files_touched,
                score=round(min(score, 1.0), 2),
                matched_keywords=list(set(matched)),
            )
        )

    # Sort highest relevance first
    results.sort(key=lambda r: r.score, reverse=True)
    return results
