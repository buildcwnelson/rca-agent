"""Tests for agent.factory — multi-provider model instantiation."""

from __future__ import annotations

import os
from unittest.mock import patch

from agno.models.google import Gemini
from agno.models.openai import OpenAIChat
from agno.models.openrouter import OpenRouter

from rca_agent.agent.factory import create_model_instance, resolve_provider_and_key


class TestResolveProviderAndKey:
    """Test resolution of provider, model, and API key from flags and environment."""

    def test_explicit_provider_openrouter(self):
        provider, model, key = resolve_provider_and_key(
            provider="openrouter",
            model="meta-llama/llama-3.3-70b-instruct",
            api_key="custom-or-key",
        )
        assert provider == "openrouter"
        assert model == "meta-llama/llama-3.3-70b-instruct"
        assert key == "custom-or-key"

    def test_explicit_provider_openai(self):
        provider, model, key = resolve_provider_and_key(
            provider="openai",
            model="gpt-4o",
            api_key="custom-oa-key",
        )
        assert provider == "openai"
        assert model == "gpt-4o"
        assert key == "custom-oa-key"

    def test_model_prefix_detects_openrouter(self):
        provider, model, _ = resolve_provider_and_key(
            model="openrouter/anthropic/claude-3.5-sonnet"
        )
        assert provider == "openrouter"
        assert model == "anthropic/claude-3.5-sonnet"

    def test_model_prefix_detects_openai(self):
        provider, model, _ = resolve_provider_and_key(model="gpt-4o-mini")
        assert provider == "openai"
        assert model == "gpt-4o-mini"

    def test_auto_detects_openrouter_from_env(self):
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "sk-or-test"}, clear=True):
            provider, _, key = resolve_provider_and_key()
            assert provider == "openrouter"
            assert key == "sk-or-test"

    def test_auto_detects_openai_from_env(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-oa-test"}, clear=True):
            provider, _, key = resolve_provider_and_key()
            assert provider == "openai"
            assert key == "sk-oa-test"

    def test_auto_detects_gemini_from_env(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "gemini-test-key"}, clear=True):
            provider, _, key = resolve_provider_and_key()
            assert provider == "gemini"
            assert key == "gemini-test-key"


class TestCreateModelInstance:
    """Test model object creation across providers."""

    def test_create_gemini_model(self):
        model = create_model_instance(
            provider="gemini",
            model_id="gemini-3.6-flash",
            api_key="test-key",
        )
        assert isinstance(model, Gemini)
        assert model.id == "gemini-3.6-flash"

    def test_create_openrouter_model(self):
        model = create_model_instance(
            provider="openrouter",
            model_id="anthropic/claude-3.5-sonnet",
            api_key="test-key",
        )
        assert isinstance(model, OpenRouter)
        assert model.id == "anthropic/claude-3.5-sonnet"
        assert model.provider == "OpenRouter"

    def test_create_openai_model(self):
        model = create_model_instance(
            provider="openai",
            model_id="gpt-4o",
            api_key="test-key",
        )
        assert isinstance(model, OpenAIChat)
        assert model.id == "gpt-4o"
        assert model.provider == "OpenAI"
