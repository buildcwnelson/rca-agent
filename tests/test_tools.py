"""Tests for agent.tools — Agno toolkit wrapping Git forensics."""

from __future__ import annotations

import textwrap

import pytest
from git import Repo

from rca_agent.agent.tools import GitForensicsTools
from rca_agent.core.forensics import set_repo_path


@pytest.fixture()
def scratch_repo(tmp_path):
    """Minimal Git repo for tool integration tests."""
    repo = Repo.init(tmp_path)
    repo.config_writer().set_value("user", "name", "Test").release()
    repo.config_writer().set_value("user", "email", "test@test.com").release()

    f = tmp_path / "app.py"
    f.write_text(
        textwrap.dedent("""\
        def main():
            print("v1")
    """)
    )
    repo.index.add(["app.py"])
    c1 = repo.index.commit("feat: initial app")

    f.write_text(
        textwrap.dedent("""\
        def main():
            print("v2")
    """)
    )
    repo.index.add(["app.py"])
    c2 = repo.index.commit("fix: update to v2")

    set_repo_path(str(tmp_path))
    return {"commits": [c1, c2], "path": tmp_path}


@pytest.fixture()
def toolkit():
    return GitForensicsTools()


class TestGitForensicsToolkit:
    """Verify the toolkit methods delegate correctly."""

    def test_toolkit_has_three_functions(self, toolkit):
        assert len(toolkit.functions) == 3
        names = set(toolkit.functions.keys())
        assert names == {"get_commit_diff", "get_blame_context", "get_recent_logs"}

    def test_get_commit_diff_via_toolkit(self, scratch_repo, toolkit):
        c2 = scratch_repo["commits"][1]
        result = toolkit.get_commit_diff(c2.hexsha)
        assert "v2" in result

    def test_get_blame_context_via_toolkit(self, scratch_repo, toolkit):
        result = toolkit.get_blame_context("app.py", 1, 2)
        assert "main" in result

    def test_get_recent_logs_via_toolkit(self, scratch_repo, toolkit):
        c2 = scratch_repo["commits"][1]
        result = toolkit.get_recent_logs(c2.hexsha, limit=2)
        assert "app" in result.lower() or "v2" in result.lower()
