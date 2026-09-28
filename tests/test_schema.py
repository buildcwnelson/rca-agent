"""Tests for models.schema — BlamelessRCA Pydantic model."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from rca_agent.models.schema import BlamelessRCA


class TestBlamelessRCA:
    """Validate schema constraints and serialization."""

    @pytest.fixture()
    def valid_payload(self) -> dict:
        return {
            "executive_summary": "Service X returned 500s due to a null-pointer in the auth middleware.",
            "incident_timeline": [
                "2024-03-01 — commit abc123 removed null-check in auth.py",
                "2024-03-02 — staging deploy passed (no integration tests for edge case)",
                "2024-03-03 — production traffic triggered the fault at 14:32 UTC",
            ],
            "root_cause_analysis": (
                "Why did the service crash? The auth middleware dereferenced a null token. "
                "Why was the token null? The upstream header was missing. "
                "Why was it missing? A load-balancer config change dropped the header. "
                "Why was the config not caught? No integration test covers header propagation. "
                "Why not? Testing gaps — the header was assumed immutable."
            ),
            "blast_radius": [
                "auth-service: 100% of authenticated endpoints returned 500",
                "billing-api: cascading timeout due to auth dependency",
            ],
            "preventative_action_items": [
                "Add integration test for header propagation through the LB",
                "Implement null-safe access in auth middleware with explicit error logging",
                "Add a CI gate that fails on null-safety lint warnings",
            ],
        }

    def test_valid_payload_roundtrips(self, valid_payload):
        rca = BlamelessRCA(**valid_payload)
        data = rca.model_dump()
        assert data["executive_summary"] == valid_payload["executive_summary"]
        assert len(data["incident_timeline"]) == 3
        assert len(data["preventative_action_items"]) == 3

    def test_json_serialization(self, valid_payload):
        rca = BlamelessRCA(**valid_payload)
        json_str = rca.model_dump_json()
        roundtripped = BlamelessRCA.model_validate_json(json_str)
        assert roundtripped == rca

    def test_missing_required_field_raises(self, valid_payload):
        del valid_payload["root_cause_analysis"]
        with pytest.raises(ValidationError):
            BlamelessRCA(**valid_payload)

    def test_empty_timeline_raises(self, valid_payload):
        valid_payload["incident_timeline"] = []
        with pytest.raises(ValidationError):
            BlamelessRCA(**valid_payload)

    def test_empty_action_items_raises(self, valid_payload):
        valid_payload["preventative_action_items"] = []
        with pytest.raises(ValidationError):
            BlamelessRCA(**valid_payload)
