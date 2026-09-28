"""Tests for core.forensics — Git telemetry extraction utilities."""

from __future__ import annotations

import os
import textwrap

import pytest
from git import Repo

from rca_agent.core.forensics import (
    _get_repo,
    get_blame_context,
    get_commit_diff,
    get_recent_logs,
    set_repo_path,
)


@pytest.fixture()
def scratch_repo(tmp_path):
    """Create a throwaway Git repo with a few commits for testing."""
    repo = Repo.init(tmp_path)
    repo.config_writer().set_value("user", "name", "Test").release()
    repo.config_writer().set_value("user", "email", "test@test.com").release()

    # --- Commit 1: initial file ---
    hello = tmp_path / "hello.py"
    hello.write_text(textwrap.dedent("""\
        def greet():
            return "hello"
    """))
    repo.index.add(["hello.py"])
    c1 = repo.index.commit("feat: add greet function")

    # --- Commit 2: modify the file ---
    hello.write_text(textwrap.dedent("""\
        def greet(name: str = "world"):
            return f"hello {name}"
    """))
    repo.index.add(["hello.py"])
    c2 = repo.index.commit("refactor: greet accepts a name parameter")

    # --- Commit 3: add a second file ---
    utils = tmp_path / "utils.py"
    utils.write_text('MAGIC = 42\n')
    repo.index.add(["utils.py"])
    c3 = repo.index.commit("feat: add utils module")

    # Point the forensics module at this repo
    set_repo_path(str(tmp_path))

    return {"repo": repo, "path": tmp_path, "commits": [c1, c2, c3]}


class TestGetCommitDiff:
    """Tests for ``get_commit_diff``."""

    def test_returns_diff_for_valid_commit(self, scratch_repo):
        c2 = scratch_repo["commits"][1]
        diff = get_commit_diff(c2.hexsha)
        assert "greet" in diff
        assert "name" in diff

    def test_initial_commit_diff(self, scratch_repo):
        c1 = scratch_repo["commits"][0]
        diff = get_commit_diff(c1.hexsha)
        assert "hello" in diff

    def test_invalid_hash_returns_error_string(self, scratch_repo):
        result = get_commit_diff("0000000000000000000000000000000000000000")
        assert "[forensics error]" in result


class TestGetBlameContext:
    """Tests for ``get_blame_context``."""

    def test_blame_returns_content(self, scratch_repo):
        blame = get_blame_context("hello.py", 1, 2)
        assert "greet" in blame

    def test_blame_invalid_file(self, scratch_repo):
        result = get_blame_context("nonexistent.py", 1, 5)
        assert "[forensics error]" in result


class TestGetRecentLogs:
    """Tests for ``get_recent_logs``."""

    def test_returns_preceding_commits(self, scratch_repo):
        c3 = scratch_repo["commits"][2]
        logs = get_recent_logs(c3.hexsha, limit=2)
        # Should include at least one preceding commit message
        assert "greet" in logs or "utils" in logs

    def test_handles_first_commit_gracefully(self, scratch_repo):
        c1 = scratch_repo["commits"][0]
        logs = get_recent_logs(c1.hexsha, limit=5)
        # Should not crash — may return the commit itself via fallback
        assert "[forensics error]" not in logs or "greet" in logs


class TestSetRepoPath:
    """Tests for ``set_repo_path`` and ``_get_repo``."""

    def test_set_repo_path_updates_internal_state(self, scratch_repo):
        repo = _get_repo()
        assert str(scratch_repo["path"]) in str(repo.working_dir)
