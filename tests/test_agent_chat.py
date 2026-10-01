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
from game_market_chatbot.tools.chart_spec import COMPOSE_RESPONSE_TOOL
from game_market_chatbot.agent.tool_calls import normalise_chart_spec
from game_market_chatbot.tools.dispatch import RENDER_CHART_TOOL, TOOLS, dispatch


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


@pytest.mark.parametrize(("row_count", "expected_bins"), [(100, 10), (1000, 20)])
def test_histogram_uses_prior_query_values_and_adaptive_bins(row_count, expected_bins):
    rows = [{"score": value} for value in range(row_count)]
    client = MockClient(script=[
        _completion(tool_calls=[_tool_call("query_1", "run_sql_query", {"sql": "SELECT score"})]),
        _completion(tool_calls=[_tool_call("chart_1", RENDER_CHART_TOOL, {
            "chart_type": "histogram",
            "source_call_id": "query_1",
            "value_field": "score",
            "title": "Score distribution",
        })]),
        _completion(content="The scores are distributed across these bins."),
    ])

    with patch("game_market_chatbot.agent.chat.dispatch", return_value=rows):
        response = chat([{"role": "user", "content": "Show score distribution"}], client=client)

    spec = response.chart_spec
    assert spec["chart_type"] == "histogram"
    assert len(spec["data"]) == expected_bins
    assert sum(row["count"] for row in spec["data"]) == row_count
    assert spec["x_field"] == "bin_start"
    assert spec["x_end_field"] == "bin_end"
    assert spec["y_field"] == "count"


def test_histogram_rejects_missing_or_non_numeric_source_values():
    args = {
        "chart_type": "histogram",
        "source_call_id": "query_1",
        "value_field": "score",
        "title": "Score distribution",
    }
    with pytest.raises(ValueError, match="earlier query result"):
        normalise_chart_spec(args, {"other_query": [{"score": 1}]})
    with pytest.raises(ValueError, match="no finite numeric values"):
        normalise_chart_spec(args, {"query_1": [{"score": True}, {"score": "2"}]})


def test_histogram_constant_values_produce_one_nonzero_width_bin():
    spec = normalise_chart_spec(
        {
            "chart_type": "histogram",
            "source_call_id": "query_1",
            "value_field": "score",
            "title": "Constant scores",
        },
        {"query_1": [{"score": 5}] * 100},
    )

    assert len(spec["data"]) == 1
    assert spec["data"][0]["bin_start"] < 5 < spec["data"][0]["bin_end"]
    assert spec["data"][0]["count"] == 100


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


def test_compose_response_preserves_text_chart_text_order():
    chart_args = {
        "chart_type": "bar",
        "data": [{"genre": "RPG", "copies": 12}],
        "x_field": "genre",
        "y_field": "copies",
        "title": "Copies by genre",
    }
    second_chart = {
        "chart_type": "line",
        "data": [{"period": "2024", "copies": 12}],
        "x_field": "period",
        "y_field": "copies",
        "title": "Copies over time",
    }
    blocks = [
        {"type": "markdown", "content": "## Leading genre\n\nRPG leads."},
        {"type": "chart", "chart_index": 0},
        {"type": "markdown", "content": "| Genre | Copies |\n| --- | ---: |\n| RPG | 12 |"},
        {"type": "chart", "chart_index": 1},
        {"type": "markdown", "content": "Sales stayed level."},
    ]
    client = MockClient(script=[
        _completion(tool_calls=[
            _tool_call("chart", RENDER_CHART_TOOL, chart_args),
            _tool_call("chart_2", RENDER_CHART_TOOL, second_chart),
            _tool_call("compose", COMPOSE_RESPONSE_TOOL, {"blocks": blocks}),
        ]),
        _completion(content="Composed."),
    ])

    response = chat([{"role": "user", "content": "Compare genres"}], client=client)

    assert response.blocks == [
        blocks[0],
        {"type": "chart", "chart": chart_args},
        blocks[2],
        {"type": "chart", "chart": second_chart},
        blocks[4],
    ]
    assert response.chart_spec == chart_args
    assert response.text == "\n\n".join(
        block["content"] for block in (blocks[0], blocks[2], blocks[4])
    )


@pytest.mark.parametrize(
    "data",
    [
        [{"genre": "RPG", "copies": float("nan")}],
        [{"genre": "RPG", "copies": "12"}],
        [{"genre": "RPG"}],
    ],
)
def test_chart_specs_reject_invalid_values(data):
    with pytest.raises(ValueError):
        normalise_chart_spec({
            "chart_type": "bar",
            "data": data,
            "x_field": "genre",
            "y_field": "copies",
            "title": "Copies by genre",
        })


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
# Tests — observability logging
# ---------------------------------------------------------------------------

def test_chat_logs_llm_requests_responses_and_tool_calls(caplog):
    """
    Each round logs an llm_request/llm_response pair, tool dispatches log a
    tool_call record, and every record for the turn shares one turn_id.
    """
    genre_rows = [{"genre": "Indie", "game_count": 80_000}]
    client = MockClient(script=[
        _completion(tool_calls=[_tool_call("call_1", "get_genre_market_share", {})]),
        _completion(content="Indie leads by game count."),
    ])

    with caplog.at_level("INFO", logger="game_market_chatbot.agent.chat"):
        with patch(
            "game_market_chatbot.agent.chat.dispatch", return_value=genre_rows
        ):
            chat(
                [{"role": "user", "content": "What are the top genres?"}],
                client=client,
            )

    messages = [r.message for r in caplog.records]
    assert messages.count("llm_request") == 2
    assert messages.count("llm_response") == 2
    assert messages.count("tool_call") == 1

    turn_ids = {r.turn_id for r in caplog.records}
    assert len(turn_ids) == 1

    tool_record = next(r for r in caplog.records if r.message == "tool_call")
    assert tool_record.tool == "get_genre_market_share"
    assert tool_record.status == "ok"


def test_chat_logs_tool_error_status(caplog):
    """A tool that raises is logged with status='error'."""
    client = MockClient(script=[
        _completion(tool_calls=[
            _tool_call("call_1", "run_sql_query", {"sql": "DROP TABLE steam_games"})
        ]),
        _completion(content="That query isn't allowed."),
    ])

    with caplog.at_level("INFO", logger="game_market_chatbot.agent.chat"):
        with patch(
            "game_market_chatbot.agent.chat.dispatch",
            side_effect=ValueError("Only read-only SELECT statements are permitted."),
        ):
            chat([{"role": "user", "content": "Delete everything"}], client=client)

    tool_record = next(r for r in caplog.records if r.message == "tool_call")
    assert tool_record.status == "error"


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
    assert COMPOSE_RESPONSE_TOOL in names

    with pytest.raises(ValueError, match="Unknown tool"):
        dispatch(RENDER_CHART_TOOL, {})


def test_render_chart_tool_schema_has_required_fields():
    definition = next(
        t for t in TOOLS if t["function"]["name"] == RENDER_CHART_TOOL
    )
    params = definition["function"]["parameters"]
    assert set(params["required"]) == {"chart_type", "title"}
    assert {"data", "x_field", "y_field", "source_call_id", "value_field"}.issubset(
        params["properties"]
    )
    assert params["properties"]["chart_type"]["enum"] == [
        "bar", "line", "scatter", "pie", "histogram",
    ]
