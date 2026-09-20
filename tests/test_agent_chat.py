"""
Unit tests for src/game_market_chatbot/agent/chat.py and the render_chart
tool definition in tools/registry.py.

The OpenRouter API is fully mocked — no network calls are made. The mock
client mimics the OpenAI chat completions response shape
(choices → message with .content and .tool_calls) and plays back a script
of canned responses, one per API call.
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from game_market_chatbot.agent.chat import AgentResponse, chat
from game_market_chatbot.tools.registry import RENDER_CHART_TOOL, TOOLS, dispatch


# ---------------------------------------------------------------------------
# Mock OpenAI/OpenRouter client
# ---------------------------------------------------------------------------

def _tool_call(call_id: str, name: str, arguments: dict) -> SimpleNamespace:
    """Build a mock tool call shaped like the OpenAI response object."""
    return SimpleNamespace(
        id=call_id,
        type="function",
        function=SimpleNamespace(name=name, arguments=json.dumps(arguments)),
    )


def _completion(
    content: str | None = None,
    tool_calls: list | None = None,
) -> SimpleNamespace:
    """Build a mock completion response (response.choices[0].message …)."""
    message = SimpleNamespace(content=content, tool_calls=tool_calls)
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class MockCompletions:
    """Plays back scripted responses, recording every create() call."""

    def __init__(self, script: list):
        self._script = list(script)
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        assert self._script, "Mock client received more calls than scripted"
        return self._script.pop(0)


class MockClient:
    def __init__(self, script: list):
        self.completions = MockCompletions(script)
        self.chat = SimpleNamespace(completions=self.completions)


# ---------------------------------------------------------------------------
# Tests — tool loop
# ---------------------------------------------------------------------------

def test_genre_question_calls_predefined_tool_and_returns_text():
    """
    "What are the top 5 genres?" should trigger get_genre_market_share,
    feed its result back to the model, and return a text answer.
    """
    genre_rows = [
        {"genre": "Indie", "game_count": 80_000, "total_copies_sold": 900_000_000},
        {"genre": "Action", "game_count": 40_000, "total_copies_sold": 800_000_000},
    ]
    client = MockClient(script=[
        _completion(tool_calls=[_tool_call("call_1", "get_genre_market_share", {})]),
        _completion(content="Indie and Action are the largest genres by copies sold."),
    ])

    with patch(
        "game_market_chatbot.agent.chat.dispatch", return_value=genre_rows
    ) as mock_dispatch:
        response = chat(
            [{"role": "user", "content": "What are the top 5 genres?"}],
            client=client,
            model="test/model",
        )

    assert isinstance(response, AgentResponse)
    assert "Indie" in response.text
    assert response.chart_spec is None
    mock_dispatch.assert_called_once_with("get_genre_market_share", {})

    # The system prompt must lead the conversation and embed the schema.
    first_call_messages = client.completions.calls[0]["messages"]
    assert first_call_messages[0]["role"] == "system"
    assert "steam_games" in first_call_messages[0]["content"]
    assert first_call_messages[1] == {
        "role": "user",
        "content": "What are the top 5 genres?",
    }

    # Second call must include the assistant tool call and the tool result.
    second_call_messages = client.completions.calls[1]["messages"]
    assert second_call_messages[-2]["role"] == "assistant"
    assert second_call_messages[-2]["tool_calls"][0]["function"]["name"] == (
        "get_genre_market_share"
    )
    assert second_call_messages[-1]["role"] == "tool"
    assert second_call_messages[-1]["tool_call_id"] == "call_1"
    assert json.loads(second_call_messages[-1]["content"]) == genre_rows


def test_text_only_answer_without_tools():
    """A question the model answers directly skips the tool loop."""
    client = MockClient(script=[
        _completion(content="Hello! Ask me anything about the Steam market."),
    ])

    with patch("game_market_chatbot.agent.chat.dispatch") as mock_dispatch:
        response = chat([{"role": "user", "content": "Hi"}], client=client)

    assert "Hello" in response.text
    assert response.chart_spec is None
    mock_dispatch.assert_not_called()
    assert len(client.completions.calls) == 1


def test_render_chart_is_captured_not_dispatched():
    """
    render_chart must not go through dispatch() — its arguments are captured
    as the AgentResponse chart spec for the UI layer to render.
    """
    chart_args = {
        "chart_type": "bar",
        "data": [
            {"genre": "Indie", "total_copies_sold": 900_000_000},
            {"genre": "Action", "total_copies_sold": 800_000_000},
        ],
        "x_field": "genre",
        "y_field": "total_copies_sold",
        "title": "Total copies sold by genre",
    }
    client = MockClient(script=[
        _completion(tool_calls=[_tool_call("call_1", "get_genre_market_share", {})]),
        _completion(tool_calls=[_tool_call("call_2", RENDER_CHART_TOOL, chart_args)]),
        _completion(content="Here is the genre breakdown, charted below."),
    ])

    with patch(
        "game_market_chatbot.agent.chat.dispatch", return_value=[]
    ) as mock_dispatch:
        response = chat(
            [{"role": "user", "content": "Chart the top genres by sales"}],
            client=client,
        )

    assert response.text == "Here is the genre breakdown, charted below."
    assert response.chart_spec == chart_args
    # Only the data tool was dispatched — never render_chart.
    mock_dispatch.assert_called_once_with("get_genre_market_share", {})

    # The model received a confirmation for its render_chart call.
    tool_messages = [
        m for m in client.completions.calls[-1]["messages"] if m["role"] == "tool"
    ]
    assert any(
        m["tool_call_id"] == "call_2" and "ok" in m["content"]
        for m in tool_messages
    )


def test_chart_spec_tolerates_json_string_data():
    """data passed as a JSON string (instead of a list) is parsed."""
    chart_args = {
        "chart_type": "pie",
        "data": json.dumps([{"publisher_class": "Indie", "game_count": 5}]),
        "x_field": "publisher_class",
        "y_field": "game_count",
        "title": "Games by publisher class",
    }
    client = MockClient(script=[
        _completion(tool_calls=[_tool_call("call_1", RENDER_CHART_TOOL, chart_args)]),
        _completion(content="Chart attached."),
    ])

    with patch("game_market_chatbot.agent.chat.dispatch"):
        response = chat([{"role": "user", "content": "Pie chart please"}], client=client)

    assert response.chart_spec["data"] == [{"publisher_class": "Indie", "game_count": 5}]
    assert response.chart_spec["chart_type"] == "pie"


def test_tool_error_is_fed_back_and_recovered():
    """
    When a tool raises (e.g. invalid SQL), the error is returned to the
    model as the tool result so it can recover, and the turn still ends
    with a text answer.
    """
    client = MockClient(script=[
        _completion(tool_calls=[
            _tool_call("call_1", "run_sql_query", {"sql": "DROP TABLE steam_games"})
        ]),
        _completion(content="That query isn't allowed — read-only SELECTs only."),
    ])

    with patch(
        "game_market_chatbot.agent.chat.dispatch",
        side_effect=ValueError("Only read-only SELECT statements are permitted."),
    ):
        response = chat(
            [{"role": "user", "content": "Delete everything"}], client=client
        )

    assert "read-only" in response.text
    tool_message = client.completions.calls[1]["messages"][-1]
    assert tool_message["role"] == "tool"
    assert "error" in json.loads(tool_message["content"])


def test_tool_round_limit_returns_fallback_text():
    """A model stuck in a tool loop is cut off after MAX_TOOL_ROUNDS."""
    client = MockClient(script=[
        _completion(
            content="Checking…",
            tool_calls=[_tool_call("call_1", "get_genre_market_share", {})],
        )
        for _ in range(3)
    ])

    with patch(
        "game_market_chatbot.agent.chat.MAX_TOOL_ROUNDS", 3
    ), patch("game_market_chatbot.agent.chat.dispatch", return_value=[]):
        response = chat([{"role": "user", "content": "Loop"}], client=client)

    assert response.text == "Checking…"
    assert len(client.completions.calls) == 3


# ---------------------------------------------------------------------------
# Tests — render_chart tool registration
# ---------------------------------------------------------------------------

def test_render_chart_tool_is_registered_but_not_dispatchable():
    """
    render_chart travels with TOOLS so the model can call it, but it is
    excluded from the dispatcher — execution is the UI layer's job.
    """
    names = [t["function"]["name"] for t in TOOLS]
    assert RENDER_CHART_TOOL in names

    with pytest.raises(ValueError, match="Unknown tool"):
        dispatch(RENDER_CHART_TOOL, {})


def test_render_chart_tool_schema_has_required_fields():
    definition = next(
        t for t in TOOLS if t["function"]["name"] == RENDER_CHART_TOOL
    )
    params = definition["function"]["parameters"]
    assert set(params["required"]) == {
        "chart_type", "data", "x_field", "y_field", "title",
    }
    assert params["properties"]["chart_type"]["enum"] == [
        "bar", "line", "scatter", "pie",
    ]
