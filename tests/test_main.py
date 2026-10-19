"""Tests for main.py — Standalone Typer CLI and Rich console rendering."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from rich.console import Console
from typer.testing import CliRunner

from rca_agent.main import app, render_postmortem
from rca_agent.models.schema import BlamelessRCA

runner = CliRunner()


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


class TestRenderPostmortem:
    """Test rich rendering of BlamelessRCA."""

    def test_render_postmortem_to_console(self, sample_rca):
        test_console = Console(record=True, width=120)
        render_postmortem(sample_rca, custom_console=test_console)
        output = test_console.export_text()

        assert "BLAMELESS ROOT CAUSE ANALYSIS POSTMORTEM" in output
        assert "Executive Summary" in output
        assert "Payment gateway timeout" in output
        assert "Incident Timeline" in output
        assert "T+01" in output
        assert "Root Cause Analysis (5 Whys Framework)" in output
        assert "Blast Radius" in output
        assert "IMPACT" in output
        assert "Preventative Guardrails" in output
        assert "circuit breaker" in output


class TestInvestigateCLI:
    """Test the investigate command via Typer CliRunner."""

    def test_cli_help(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "Autonomous Root Cause Analysis generator" in result.output

    def test_investigate_help(self):
        result = runner.invoke(app, ["investigate", "--help"])
        assert result.exit_code == 0
        assert "--commit" in result.output
        assert "--path" in result.output

    def test_investigate_missing_commit(self):
        result = runner.invoke(app, ["investigate"])
        assert result.exit_code != 0
        assert "Missing option" in result.output or "commit" in result.output.lower()

    def test_investigate_nonexistent_path(self):
        result = runner.invoke(
            app, ["investigate", "--commit", "abc1234", "--path", "/nonexistent/path/xyz"]
        )
        assert result.exit_code == 1
        assert "does not exist" in result.output

    def test_investigate_successful_run(self, tmp_path, sample_rca):
        with (
            patch("rca_agent.main.set_repo_path") as mock_set_path,
            patch("rca_agent.main.run_investigation", return_value=sample_rca) as mock_investigate,
        ):
            result = runner.invoke(
                app,
                [
                    "investigate",
                    "--commit",
                    "deadbeef",
                    "--path",
                    str(tmp_path),
                    "--model",
                    "gemini-2.5-pro",
                    "--api-key",
                    "custom-cli-key",
                ],
            )

            assert result.exit_code == 0
            mock_set_path.assert_called_once_with(str(tmp_path.resolve()))
            mock_investigate.assert_called_once_with(
                commit_hash="deadbeef", model_id="gemini-2.5-pro", api_key="custom-cli-key"
            )
            assert "BLAMELESS ROOT CAUSE ANALYSIS POSTMORTEM" in result.output
            assert "Payment gateway timeout" in result.output
            assert "IMPACT" in result.output
            assert "Preventative Guardrails" in result.output

    def test_investigate_handles_agent_failure(self, tmp_path):
        with (
            patch("rca_agent.main.set_repo_path"),
            patch(
                "rca_agent.main.run_investigation",
                side_effect=RuntimeError("Ollama connection refused"),
            ),
        ):
            result = runner.invoke(
                app,
                [
                    "investigate",
                    "--commit",
                    "deadbeef",
                    "--path",
                    str(tmp_path),
                ],
            )

            assert result.exit_code == 1
            assert "Investigation Failed" in result.output
            assert "Ollama connection refused" in result.output

    def test_investigate_generates_pdf(self, tmp_path, sample_rca):
        pdf_out = tmp_path / "output_report.pdf"
        with (
            patch("rca_agent.main.set_repo_path"),
            patch("rca_agent.main.run_investigation", return_value=sample_rca),
        ):
            result = runner.invoke(
                app,
                [
                    "investigate",
                    "--commit",
                    "deadbeef",
                    "--path",
                    str(tmp_path),
                    "--pdf",
                    str(pdf_out),
                ],
            )

            assert result.exit_code == 0
            assert "Executive PDF report generated" in result.output
            assert pdf_out.exists()
            assert pdf_out.stat().st_size > 1000
