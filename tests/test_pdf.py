"""Tests for reports.pdf — Executive Blameless RCA PDF generation."""

from __future__ import annotations

import pytest

from rca_agent.models.schema import BlamelessRCA
from rca_agent.reports.pdf import generate_rca_pdf


@pytest.fixture()
def sample_rca() -> BlamelessRCA:
    return BlamelessRCA(
        executive_summary="Payment gateway timeout triggered cascaded failures in order processing.",
        incident_timeline=[
            "2026-09-01 10:00 UTC - commit a1b2c3d merged removing retry jitter",
            "2026-09-01 10:15 UTC - upstream API had 500ms latency spike",
            "2026-09-01 10:16 UTC - connection pool exhaustion across 4 worker pods",
        ],
        root_cause_analysis=(
            "1. Why did orders fail? HTTP 504 gateway timeout.\n"
            "2. Why did timeout occur? Connection pool exhausted.\n"
            "3. Why was pool exhausted? Retry storm without exponential backoff.\n"
            "4. Why was retry storm possible? Jitter logic removed in PR #128.\n"
            "5. Why was PR #128 approved? Missing CI lint rule for network client configs."
        ),
        blast_radius=[
            "orders-service: 100% order creation failed for 15 minutes",
            "notifications-service: 15,000 delayed customer SMS alerts",
        ],
        preventative_action_items=[
            "Enforce exponential backoff and jitter with static analyzer check in CI",
            "Implement circuit breaker pattern on upstream payment client",
            "Add load testing step in staging deployment pipeline",
        ],
    )


def test_generate_rca_pdf_creates_valid_file(tmp_path, sample_rca):
    pdf_path = tmp_path / "postmortem.pdf"
    result_path = generate_rca_pdf(
        rca=sample_rca,
        output_path=pdf_path,
        commit_hash="deadbeef12345678",
        repo_name="my-org/core-service",
        model_name="Gemini 2.5 Flash",
    )

    assert result_path.exists()
    assert result_path.is_file()
    assert result_path.stat().st_size > 1000
    # Check PDF magic header
    with open(result_path, "rb") as f:
        header = f.read(4)
        assert header == b"%PDF"


def test_generate_rca_pdf_handles_nested_dirs(tmp_path, sample_rca):
    pdf_path = tmp_path / "nested" / "reports" / "rca.pdf"
    result_path = generate_rca_pdf(
        rca=sample_rca,
        output_path=pdf_path,
        commit_hash="abc12345",
    )

    assert result_path.exists()
    assert result_path.stat().st_size > 1000
