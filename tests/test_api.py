from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from game_market_chatbot.agent.chat import AgentResponse
from game_market_chatbot.api import routes
from game_market_chatbot.api.app import create_app


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app(cors_origins=["http://localhost:5173"]))


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.parametrize(
    "messages",
    [
        [],
        [{"role": "system", "content": "not accepted from the client"}],
        [{"role": "user", "content": None}],
    ],
)
def test_chat_rejects_invalid_messages(
    client: TestClient,
    messages: list[dict[str, Any]],
) -> None:
    response = client.post("/api/chat", json={"messages": messages})

    assert response.status_code == 422


def test_chat_forwards_transcript_and_serializes_chart_spec(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    forwarded: list[dict[str, str]] = []
    chart_spec = {
        "chart_type": "bar",
        "data": [{"genre": "RPG", "copies": 12}],
        "x_field": "genre",
        "y_field": "copies",
        "title": "Copies by genre",
    }

    def fake_chat(messages: list[dict[str, str]]) -> AgentResponse:
        forwarded.extend(messages)
        return AgentResponse(text="Here are the results.", chart_spec=chart_spec)

    monkeypatch.setattr(routes, "chat", fake_chat)
    transcript = [
        {"role": "user", "content": "Compare genres."},
        {"role": "assistant", "content": "Which period?"},
        {"role": "user", "content": "All time."},
    ]

    response = client.post("/api/chat", json={"messages": transcript})

    assert response.status_code == 200
    assert forwarded == transcript
    assert response.json() == {
        "text": "Here are the results.",
        "chart_spec": chart_spec,
    }


def test_chat_transcripts_are_forwarded_independently(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    forwarded: list[list[dict[str, str]]] = []

    def fake_chat(messages: list[dict[str, str]]) -> AgentResponse:
        forwarded.append(messages)
        return AgentResponse(text=messages[-1]["content"])

    monkeypatch.setattr(routes, "chat", fake_chat)
    first_transcript = [{"role": "user", "content": "First chat"}]
    second_transcript = [
        {"role": "user", "content": "Second chat"},
        {"role": "assistant", "content": "Second chat response"},
        {"role": "user", "content": "Continue second chat"},
    ]

    first_response = client.post("/api/chat", json={"messages": first_transcript})
    second_response = client.post("/api/chat", json={"messages": second_transcript})

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert forwarded == [first_transcript, second_transcript]


def test_chat_hides_agent_errors_from_client(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def failed_chat(_messages: list[dict[str, str]]) -> AgentResponse:
        raise RuntimeError("private upstream detail")

    monkeypatch.setattr(routes, "chat", failed_chat)

    response = client.post(
        "/api/chat",
        json={"messages": [{"role": "user", "content": "hello"}]},
    )

    assert response.status_code == 500
    assert response.json() == {"detail": "Chat request failed."}
    assert "private upstream detail" not in response.text


def test_cors_allows_configured_frontend_origin() -> None:
    client = TestClient(create_app(cors_origins=["https://chat.example.test"]))

    response = client.options(
        "/api/chat",
        headers={
            "Origin": "https://chat.example.test",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://chat.example.test"