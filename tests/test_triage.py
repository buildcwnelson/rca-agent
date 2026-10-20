"""Tests for core.triage — stack trace parsing and git blame culprit matching."""

from __future__ import annotations

import textwrap

from git import Repo

from rca_agent.core.triage import find_culprit_from_log, parse_trace_frames


def test_parse_python_traceback():
    sample_trace = textwrap.dedent("""
        Traceback (most recent call last):
          File "src/rca_agent/main.py", line 45, in investigate
            rca_result = run_investigation(commit_hash=commit)
          File "src/rca_agent/agent/investigator.py", line 125, in run_investigation
            agent = create_investigator()
        KeyError: 'api_key'
    """)
    frames = parse_trace_frames(sample_trace)
    assert len(frames) == 2
    # In reverse order (deepest crash site first)
    assert frames[0].filepath == "src/rca_agent/agent/investigator.py"
    assert frames[0].line_number == 125
    assert frames[1].filepath == "src/rca_agent/main.py"
    assert frames[1].line_number == 45


def test_parse_javascript_traceback():
    sample_trace = textwrap.dedent("""
        Error: Connection failed
            at queryDatabase (/app/src/db/connection.ts:88:14)
            at handleRequest (/app/src/server.js:42:10)
    """)
    frames = parse_trace_frames(sample_trace)
    assert len(frames) == 2
    assert frames[0].filepath == "/app/src/db/connection.ts"
    assert frames[0].line_number == 88


def test_find_culprit_from_log_matches_repo(tmp_path):
    repo = Repo.init(str(tmp_path))
    file_path = tmp_path / "payment.py"
    file_path.write_text("def process_payment():\n    return False\n", encoding="utf-8")
    repo.index.add(["payment.py"])
    repo.index.commit("feat: initial payment module")

    # Introduce bug on line 2
    file_path.write_text("def process_payment():\n    raise ValueError('Card expired')\n", encoding="utf-8")
    repo.index.add(["payment.py"])
    commit2 = repo.index.commit("fix: add payment expiration error")

    trace = textwrap.dedent(f"""
        Traceback (most recent call last):
          File "{file_path}", line 2, in process_payment
            raise ValueError('Card expired')
        ValueError: Card expired
    """)

    best_sha, candidates = find_culprit_from_log(log_text=trace, repo_path=str(tmp_path))
    assert best_sha == commit2.hexsha
    assert len(candidates) >= 1
    assert candidates[0].line_number == 2
    assert candidates[0].confidence_score >= 0.8
