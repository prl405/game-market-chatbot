"""Unit tests for agent/config.py: model selection, client setup, prompt."""

from __future__ import annotations

import sys
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from game_market_chatbot.agent import config


def test_get_model_defaults_when_env_unset(monkeypatch):
    monkeypatch.delenv("OPENROUTER_MODEL", raising=False)
    assert config.get_model() == config.DEFAULT_MODEL


def test_get_model_uses_env_override(monkeypatch):
    monkeypatch.setenv("OPENROUTER_MODEL", "vendor/custom-model")
    assert config.get_model() == "vendor/custom-model"


def test_get_client_requires_api_key(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(EnvironmentError, match="OPENROUTER_API_KEY"):
        config.get_client()


def test_get_client_rejects_empty_api_key(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "")
    with pytest.raises(EnvironmentError, match="OPENROUTER_API_KEY"):
        config.get_client()


def test_get_client_builds_openrouter_client_with_fake_sdk(monkeypatch):
    """The OpenAI SDK is replaced by a fake: no live client is created."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    created = []

    def fake_openai(**kwargs):
        created.append(kwargs)
        return SimpleNamespace(**kwargs)

    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=fake_openai))

    client = config.get_client()

    assert created == [
        {"base_url": config.OPENROUTER_BASE_URL, "api_key": "test-key"}
    ]
    assert client.base_url == "https://openrouter.ai/api/v1"


def test_build_system_prompt_embeds_schema_and_chart_guidance():
    with patch.object(config, "get_schema_info", return_value="SCHEMA_MARKER"):
        prompt = config.build_system_prompt()

    assert "SCHEMA_MARKER" in prompt
    assert "render_chart" in prompt
    assert "compose_response" in prompt
    assert prompt == prompt.strip()
