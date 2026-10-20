"""Tests for agent.investigator — agent configuration and wiring.

These tests validate the agent's configuration without requiring a
running Ollama instance.  They verify that the agent is correctly
wired with the expected tools, schema, and instructions.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from rca_agent.agent.investigator import (
    SYSTEM_INSTRUCTIONS,
    create_investigator,
    run_investigation,
)
from rca_agent.models.schema import BlamelessRCA


class TestCreateInvestigator:
    """Verify agent factory configuration."""

    def test_agent_has_correct_model(self):
        agent = create_investigator(model_id="gemini-2.5-pro")
        assert agent.model.id == "gemini-2.5-pro"
        assert agent.model.provider == "Google"

    def test_agent_has_forensics_tools(self):
        agent = create_investigator()
        tool_names = set()
        for toolkit in agent.tools:
            tool_names.update(toolkit.functions.keys())
        assert "get_commit_diff" in tool_names
        assert "get_blame_context" in tool_names
        assert "get_recent_logs" in tool_names

    def test_agent_has_output_schema(self):
        agent = create_investigator()
        assert agent.output_schema is BlamelessRCA

    def test_agent_has_system_instructions(self):
        agent = create_investigator()
        assert "5 Whys" in agent.instructions
        assert "blameless" in agent.instructions.lower()

    def test_system_instructions_contain_protocol(self):
        assert "Gather Evidence" in SYSTEM_INSTRUCTIONS
        assert "Trace the Timeline" in SYSTEM_INSTRUCTIONS
        assert "Assess Blast Radius" in SYSTEM_INSTRUCTIONS
        assert "Prescribe Prevention" in SYSTEM_INSTRUCTIONS

    def test_default_model_is_gemini(self):
        agent = create_investigator()
        assert agent.model.id in ("gemini-2.0-flash", "gemini-1.5-flash", "gemini-2.5-flash", "gemini-3.6-flash")
        assert agent.model.provider == "Google"

    def test_agent_uses_custom_api_key(self):
        agent = create_investigator(api_key="custom-gemini-key")
        assert agent.model.api_key == "custom-gemini-key"


class TestRunInvestigation:
    """Verify ``run_investigation`` correctly processes agent output."""

    @pytest.fixture()
    def mock_rca(self) -> BlamelessRCA:
        return BlamelessRCA(
            executive_summary="Test summary",
            incident_timeline=["Event 1"],
            root_cause_analysis="Why? Because. Why? Because. Why? Root cause.",
            blast_radius=["component-a"],
            preventative_action_items=["Add test coverage"],
        )

    def test_returns_blameless_rca_from_parsed_content(self, mock_rca):
        mock_result = MagicMock()
        mock_result.content = mock_rca

        with patch("rca_agent.agent.investigator.create_investigator") as mock_create:
            mock_agent = MagicMock()
            mock_agent.run.return_value = mock_result
            mock_create.return_value = mock_agent

            result = run_investigation("abc123")
            assert isinstance(result, BlamelessRCA)
            assert result.executive_summary == "Test summary"

    def test_returns_blameless_rca_from_json_string(self, mock_rca):
        mock_result = MagicMock()
        mock_result.content = mock_rca.model_dump_json()

        with patch("rca_agent.agent.investigator.create_investigator") as mock_create:
            mock_agent = MagicMock()
            mock_agent.run.return_value = mock_result
            mock_create.return_value = mock_agent

            result = run_investigation("abc123")
            assert isinstance(result, BlamelessRCA)
            assert result.executive_summary == "Test summary"

    def test_returns_blameless_rca_from_dict(self, mock_rca):
        mock_result = MagicMock()
        mock_result.content = mock_rca.model_dump()

        with patch("rca_agent.agent.investigator.create_investigator") as mock_create:
            mock_agent = MagicMock()
            mock_agent.run.return_value = mock_result
            mock_create.return_value = mock_agent

            result = run_investigation("abc123")
            assert isinstance(result, BlamelessRCA)
            assert result.executive_summary == "Test summary"
