"""Unit tests for agent/tool_calls.py: argument parsing, serialization, execution.

External services are never touched: dispatch is replaced with a fake.
"""

from __future__ import annotations

import json
import logging
from types import SimpleNamespace

import pytest

from game_market_chatbot.agent.tool_calls import (
    assistant_message_to_dict,
    execute_tool_call,
    parse_arguments,
)
from game_market_chatbot.tools.chart_spec import COMPOSE_RESPONSE_TOOL
from game_market_chatbot.tools.dispatch import RENDER_CHART_TOOL

LOGGER = logging.getLogger("test_tool_calls")


def _tc(call_id, name, arguments):
    return SimpleNamespace(
        id=call_id,
        type="function",
        function=SimpleNamespace(name=name, arguments=arguments),
    )


class FakeDispatch:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.calls = []

    def __call__(self, name, args):
        self.calls.append((name, args))
        if self.error:
            raise self.error
        return self.result


def _run(tool_call, dispatch_fn=None, query_results=None):
    return execute_tool_call(
        tool_call,
        turn_id="turn-1",
        dispatch_fn=dispatch_fn or FakeDispatch(),
        logger=LOGGER,
        query_results=query_results,
    )


# --- parse_arguments -------------------------------------------------------

def test_parse_arguments_returns_dict_unchanged():
    args = {"limit": 5}
    assert parse_arguments(args) is args


def test_parse_arguments_decodes_json_string():
    assert parse_arguments('{"limit": 5, "genre": "RPG"}') == {"limit": 5, "genre": "RPG"}


@pytest.mark.parametrize("empty", [None, "", "   "])
def test_parse_arguments_empty_inputs_become_empty_dict(empty):
    assert parse_arguments(empty) == {}


def test_parse_arguments_malformed_json_raises():
    with pytest.raises(json.JSONDecodeError):
        parse_arguments('{"limit": ')


# --- assistant_message_to_dict --------------------------------------------

def test_assistant_message_serializes_tool_calls():
    message = SimpleNamespace(content=None)
    calls = [
        _tc("c1", "get_genre_market_share", '{"limit": 3}'),
        _tc("c2", "run_sql_query", {"sql": "SELECT 1"}),
    ]

    assert assistant_message_to_dict(message, calls) == {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {
                "id": "c1",
                "type": "function",
                "function": {"name": "get_genre_market_share", "arguments": '{"limit": 3}'},
            },
            {
                "id": "c2",
                "type": "function",
                "function": {"name": "run_sql_query", "arguments": '{"sql": "SELECT 1"}'},
            },
        ],
    }


def test_assistant_message_keeps_content_text():
    message = SimpleNamespace(content="Checking")
    result = assistant_message_to_dict(message, [_tc("c1", "t", "{}")])
    assert result["content"] == "Checking"


# --- execute_tool_call -----------------------------------------------------

def test_supported_tool_reaches_dispatch_with_parsed_arguments():
    fake = FakeDispatch(result=[{"genre": "RPG", "n": 2}])

    content, spec = _run(_tc("c1", "get_top_games_by_copies_sold", '{"limit": 3}'), fake)

    assert fake.calls == [("get_top_games_by_copies_sold", {"limit": 3})]
    assert json.loads(content) == [{"genre": "RPG", "n": 2}]
    assert spec is None


def test_dispatch_rows_are_remembered_by_call_id():
    rows = [{"score": 1}, {"score": 2}]
    store: dict = {}

    _run(_tc("q1", "run_sql_query", {"sql": "SELECT score"}), FakeDispatch(rows), store)

    assert store == {"q1": rows}


def test_non_row_results_are_not_remembered():
    store: dict = {}
    _run(_tc("q1", "get_schema_info", {}), FakeDispatch("schema text"), store)
    assert store == {}


def test_unsupported_tool_returns_error_content():
    from game_market_chatbot.tools.dispatch import dispatch

    content, spec = _run(_tc("c1", "drop_everything", "{}"), dispatch)

    error = json.loads(content)["error"]
    assert error.startswith("ValueError")
    assert "Unknown tool" in error
    assert spec is None


def test_dispatch_exception_is_reported_not_raised():
    fake = FakeDispatch(error=ValueError("Only read-only SELECT statements are permitted."))

    content, spec = _run(_tc("c1", "run_sql_query", {"sql": "DROP TABLE x"}), fake)

    assert json.loads(content) == {
        "error": "ValueError: Only read-only SELECT statements are permitted."
    }
    assert spec is None


def test_malformed_arguments_do_not_reach_dispatch():
    fake = FakeDispatch(result=[])

    content, spec = _run(_tc("c1", "run_sql_query", '{"sql": '), fake)

    assert "Invalid tool arguments" in json.loads(content)["error"]
    assert fake.calls == []
    assert spec is None


def test_render_chart_returns_spec_and_skips_dispatch():
    fake = FakeDispatch()
    args = {
        "chart_type": "bar",
        "data": [{"genre": "RPG", "copies": 12}],
        "x_field": "genre",
        "y_field": "copies",
        "title": "Copies",
    }

    content, spec = _run(_tc("c1", RENDER_CHART_TOOL, args), fake)

    assert spec == args
    assert json.loads(content)["status"] == "ok"
    assert fake.calls == []


def test_render_chart_with_invalid_data_returns_error_and_no_spec():
    args = {"chart_type": "bar", "data": [], "x_field": "a", "y_field": "b", "title": "t"}

    content, spec = _run(_tc("c1", RENDER_CHART_TOOL, args))

    assert "between 1 and 50 rows" in json.loads(content)["error"]
    assert spec is None


def test_histogram_chart_uses_results_from_earlier_dispatch():
    store: dict = {}
    _run(_tc("q1", "run_sql_query", {"sql": "s"}), FakeDispatch([{"v": i} for i in range(4)]), store)

    _, spec = _run(
        _tc("c2", RENDER_CHART_TOOL, {
            "chart_type": "histogram", "source_call_id": "q1",
            "value_field": "v", "title": "Dist",
        }),
        query_results=store,
    )

    assert spec["chart_type"] == "histogram"
    assert sum(row["count"] for row in spec["data"]) == 4


def test_compose_response_echoes_blocks_without_dispatch():
    fake = FakeDispatch()
    args = {"blocks": [{"type": "markdown", "content": "Hi"}]}

    content, spec = _run(_tc("c1", COMPOSE_RESPONSE_TOOL, args), fake)

    assert json.loads(content) == args
    assert spec is None
    assert fake.calls == []


def test_tool_call_is_logged_with_status(caplog):
    with caplog.at_level("INFO", logger="test_tool_calls"):
        _run(_tc("c1", "get_schema_info", {}), FakeDispatch([]))
        _run(_tc("c2", "run_sql_query", {}), FakeDispatch(error=RuntimeError("x")))

    records = [r for r in caplog.records if r.message == "tool_call"]
    assert [(r.tool, r.status, r.turn_id) for r in records] == [
        ("get_schema_info", "ok", "turn-1"),
        ("run_sql_query", "error", "turn-1"),
    ]
