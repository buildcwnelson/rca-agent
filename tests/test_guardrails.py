"""Tests for reports.guardrails — regression test generation."""

from __future__ import annotations

from rca_agent.models.schema import BlamelessRCA
from rca_agent.reports.guardrails import generate_regression_test_code, write_regression_test_file


def test_generate_regression_test_code():
    rca = BlamelessRCA(
        executive_summary="Database connection starvation during peak checkout load.",
        incident_timeline=["T+01 Connection pool max limit set to 5", "T+02 Spike exhausted pool"],
        root_cause_analysis="Pool size was too small for horizontal worker scaling.",
        blast_radius=["Checkout API returned HTTP 503", "Order processing halted"],
        preventative_action_items=[
            "Increase max_connections in pool configuration to 50",
            "Add health check timeout alert",
        ],
    )
    code = generate_regression_test_code(rca=rca, commit_hash="1234567890abcdef")
    assert "test_regression_12345678_guardrail" in code
    assert "Database connection starvation" in code
    assert "Increase max_connections in pool configuration to 50" in code
    assert "assert True" in code


def test_write_regression_test_file(tmp_path):
    rca = BlamelessRCA(
        executive_summary="Sample executive summary.",
        incident_timeline=["T+01 Initial decay", "T+02 Incident declared"],
        root_cause_analysis="Sample root cause 5 Whys analysis.",
        blast_radius=["Sample impact"],
        preventative_action_items=["Sample action 1", "Sample action 2"],
    )
    created_file = write_regression_test_file(
        rca=rca,
        commit_hash="deadbeef12345678",
        output_dir=tmp_path / "tests_output",
    )
    assert created_file.exists()
    assert created_file.name == "test_regression_deadbeef.py"
    assert "test_regression_deadbeef_guardrail" in created_file.read_text(encoding="utf-8")
