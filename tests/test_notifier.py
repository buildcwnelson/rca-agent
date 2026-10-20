"""Tests for reports.notifier — PR comment formatting and Slack notification payload."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from rca_agent.models.schema import BlamelessRCA
from rca_agent.reports.notifier import format_github_pr_markdown, send_slack_notification


def test_format_github_pr_markdown():
    rca = BlamelessRCA(
        executive_summary="Executive overview of payment gateway outage.",
        incident_timeline=["T+01 Configuration applied", "T+02 Outage observed"],
        root_cause_analysis="Timeout threshold was reduced below network latency.",
        blast_radius=["Checkout flow disrupted", "Retry queue filled up"],
        preventative_action_items=["Increase timeout to 30s", "Add circuit breaker"],
    )
    md = format_github_pr_markdown(rca=rca, commit_hash="abcdef1234567890", repo_name="payments-svc")
    assert "Blameless Root Cause Analysis (RCA) Postmortem" in md
    assert "Executive overview of payment gateway outage." in md
    assert "payments-svc" in md
    assert "abcdef12" in md
    assert "Increase timeout to 30s" in md


def test_send_slack_notification_success():
    rca = BlamelessRCA(
        executive_summary="Sample incident summary.",
        incident_timeline=["T+01 Step 1"],
        root_cause_analysis="Sample root cause.",
        blast_radius=["Sample blast radius"],
        preventative_action_items=["Action item 1", "Action item 2"],
    )
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        success = send_slack_notification(
            webhook_url="https://hooks.slack.com/services/TEST/TOKEN",
            rca=rca,
            commit_hash="deadbeef1234",
            repo_name="my-repo",
        )
        assert success is True
