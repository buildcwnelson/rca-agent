"""Tests for core.range_analyzer — release window scanning and symptom scoring."""

from __future__ import annotations

from git import Repo

from rca_agent.core.range_analyzer import parse_commit_range


def test_parse_commit_range_scoring(tmp_path):
    repo = Repo.init(str(tmp_path))
    file_path = tmp_path / "app.py"

    file_path.write_text("print('v1.0')\n", encoding="utf-8")
    repo.index.add(["app.py"])
    commit1 = repo.index.commit("chore: release v1.0")

    file_path.write_text("print('v1.1')\n# Database pool update\n", encoding="utf-8")
    repo.index.add(["app.py"])
    commit2 = repo.index.commit("feat: optimize database connection pool")

    file_path.write_text("print('v1.2')\n# Docs update\n", encoding="utf-8")
    repo.index.add(["app.py"])
    commit3 = repo.index.commit("docs: update developer readme")

    range_str = f"{commit1.hexsha}..{commit3.hexsha}"
    results = parse_commit_range(
        repo_path=str(tmp_path),
        commit_range=range_str,
        symptom="Database connection pool timeout",
    )

    assert len(results) == 2
    # commit2 should rank first because of 'database' and 'connection' keywords
    assert results[0].commit_sha == commit2.hexsha
    assert results[0].score > results[1].score
    assert "database" in results[0].matched_keywords
