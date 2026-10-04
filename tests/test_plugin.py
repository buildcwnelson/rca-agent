"""Tests for plugin — hookspecs, implementation, and pluggy integration.

Tests validate the pluggy wiring, hook contract, and the plugin's
ability to process violation payloads and return structured RCA output.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pluggy
import pytest

from rca_agent.models.schema import BlamelessRCA
from rca_agent.plugin.hookspecs import RCAHookSpec
from rca_agent.plugin.implementation import RCAPlugin


@pytest.fixture()
def sample_rca() -> BlamelessRCA:
    return BlamelessRCA(
        executive_summary="Service crashed due to null pointer in auth middleware.",
        incident_timeline=[
            "commit abc123 removed null-check",
            "staging deploy passed without catching edge case",
            "production crash at 14:32 UTC",
        ],
        root_cause_analysis=(
            "Why crash? Null pointer. Why null? Missing header. "
            "Why missing? LB config change. Why not caught? No test. "
            "Why no test? Assumed immutable."
        ),
        blast_radius=["auth-service", "billing-api"],
        preventative_action_items=[
            "Add integration test for header propagation",
            "Null-safe access in auth middleware",
        ],
    )


@pytest.fixture()
def violation_payload() -> dict:
    return {
        "commit_hash": "abc123",
        "description": "Circular dependency detected between auth and billing",
        "affected_files": ["src/auth/service.py", "src/billing/client.py"],
        "severity": "critical",
        "context": "diff --git a/src/auth/service.py ...\n+from billing.client import BillingClient",
    }


class TestRCAHookSpec:
    """Verify the hook specification is correctly defined."""

    def test_hookspec_has_on_violation_detected(self):
        pm = pluggy.PluginManager("rca_agent")
        pm.add_hookspecs(RCAHookSpec)
        # The hook should be registered
        assert hasattr(pm.hook, "on_violation_detected")

    def test_plugin_manager_accepts_implementation(self):
        pm = pluggy.PluginManager("rca_agent")
        pm.add_hookspecs(RCAHookSpec)
        plugin = RCAPlugin()
        pm.register(plugin)
        # Should not raise — implementation conforms to spec
        assert pm.is_registered(plugin)


class TestRCAPlugin:
    """Verify the hook implementation processes payloads correctly."""

    def test_on_violation_detected_returns_dict(self, violation_payload, sample_rca):
        """Plugin should return a dict with all BlamelessRCA keys."""
        mock_result = MagicMock()
        mock_result.content = sample_rca

        with patch("rca_agent.plugin.implementation.create_investigator") as mock_create:
            mock_agent = MagicMock()
            mock_agent.run.return_value = mock_result
            mock_create.return_value = mock_agent

            plugin = RCAPlugin()
            result = plugin.on_violation_detected(violation_payload=violation_payload)

            assert isinstance(result, dict)
            assert "executive_summary" in result
            assert "incident_timeline" in result
            assert "root_cause_analysis" in result
            assert "blast_radius" in result
            assert "preventative_action_items" in result

    def test_prompt_includes_pre_assembled_context(self, violation_payload, sample_rca):
        """When context is provided, the prompt should include it."""
        mock_result = MagicMock()
        mock_result.content = sample_rca

        with patch("rca_agent.plugin.implementation.create_investigator") as mock_create:
            mock_agent = MagicMock()
            mock_agent.run.return_value = mock_result
            mock_create.return_value = mock_agent

            plugin = RCAPlugin()
            plugin.on_violation_detected(violation_payload=violation_payload)

            # Check that the agent was called with the pre-assembled context
            call_args = mock_agent.run.call_args[0][0]
            assert "BEGIN CONTEXT" in call_args
            assert "billing.client" in call_args

    def test_prompt_uses_git_tools_when_no_context(self, sample_rca):
        """When no context is provided, prompt should instruct to use tools."""
        payload = {
            "commit_hash": "def456",
            "description": "Breaking change",
            "affected_files": ["main.py"],
            "severity": "warning",
        }
        mock_result = MagicMock()
        mock_result.content = sample_rca

        with patch("rca_agent.plugin.implementation.create_investigator") as mock_create:
            mock_agent = MagicMock()
            mock_agent.run.return_value = mock_result
            mock_create.return_value = mock_agent

            plugin = RCAPlugin()
            plugin.on_violation_detected(violation_payload=payload)

            call_args = mock_agent.run.call_args[0][0]
            assert "Git forensics tools" in call_args
            assert "BEGIN CONTEXT" not in call_args

    def test_handles_json_string_response(self, violation_payload, sample_rca):
        """Plugin should handle agent returning a JSON string."""
        mock_result = MagicMock()
        mock_result.content = sample_rca.model_dump_json()

        with patch("rca_agent.plugin.implementation.create_investigator") as mock_create:
            mock_agent = MagicMock()
            mock_agent.run.return_value = mock_result
            mock_create.return_value = mock_agent

            plugin = RCAPlugin()
            result = plugin.on_violation_detected(violation_payload=violation_payload)

            assert isinstance(result, dict)
            assert result["executive_summary"] == sample_rca.executive_summary

    def test_handles_dict_response(self, violation_payload, sample_rca):
        """Plugin should handle agent returning a dict."""
        mock_result = MagicMock()
        mock_result.content = sample_rca.model_dump()

        with patch("rca_agent.plugin.implementation.create_investigator") as mock_create:
            mock_agent = MagicMock()
            mock_agent.run.return_value = mock_result
            mock_create.return_value = mock_agent

            plugin = RCAPlugin()
            result = plugin.on_violation_detected(violation_payload=violation_payload)

            assert isinstance(result, dict)
            assert result["executive_summary"] == sample_rca.executive_summary


class TestPluggyIntegration:
    """End-to-end pluggy registration and invocation."""

    def test_full_pluggy_lifecycle(self, violation_payload, sample_rca):
        """Simulate a host app loading and invoking the plugin."""
        mock_result = MagicMock()
        mock_result.content = sample_rca

        with patch("rca_agent.plugin.implementation.create_investigator") as mock_create:
            mock_agent = MagicMock()
            mock_agent.run.return_value = mock_result
            mock_create.return_value = mock_agent

            # Simulate host application
            pm = pluggy.PluginManager("rca_agent")
            pm.add_hookspecs(RCAHookSpec)
            pm.register(RCAPlugin())

            results = pm.hook.on_violation_detected(violation_payload=violation_payload)

            assert len(results) == 1
            rca_dict = results[0]
            assert rca_dict["executive_summary"] == sample_rca.executive_summary
            assert len(rca_dict["blast_radius"]) == 2
