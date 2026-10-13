"""Unit tests for tool registration and name-based dispatch (no database)."""

from __future__ import annotations

import inspect
import json

import pytest

from game_market_chatbot.tools import dispatch as dispatch_module
from game_market_chatbot.tools.chart_spec import COMPOSE_RESPONSE_TOOL, RENDER_CHART_TOOL
from game_market_chatbot.tools.dispatch import _FUNCTION_MAP, TOOLS, dispatch

QUERY_TOOLS = {
    "get_top_games_by_copies_sold",
    "get_genre_market_share",
    "get_publisher_class_breakdown",
    "get_games_by_price_range",
    "get_review_score_distribution",
    "get_games_by_release_date",
    "get_schema_info",
    "run_sql_query",
}
UI_TOOLS = {RENDER_CHART_TOOL, COMPOSE_RESPONSE_TOOL}


def _definition(name):
    return next(t for t in TOOLS if t["function"]["name"] == name)


# --- registry --------------------------------------------------------------

def test_registered_tool_names_are_exactly_the_expected_set():
    names = [t["function"]["name"] for t in TOOLS]
    assert len(names) == len(set(names))
    assert set(names) == QUERY_TOOLS | UI_TOOLS


def test_function_map_contains_only_query_tools():
    assert set(_FUNCTION_MAP) == QUERY_TOOLS
    assert all(callable(fn) for fn in _FUNCTION_MAP.values())


@pytest.mark.parametrize("tool", TOOLS, ids=lambda t: t["function"]["name"])
def test_each_tool_definition_is_well_formed(tool):
    assert tool["type"] == "function"
    fn = tool["function"]
    assert fn["description"].strip()
    assert fn["parameters"]["type"] == "object"
    assert isinstance(fn["parameters"]["properties"], dict)
    assert set(fn["parameters"].get("required", [])) <= set(fn["parameters"]["properties"])


@pytest.mark.parametrize("name", sorted(QUERY_TOOLS))
def test_declared_parameters_match_handler_signature(name):
    """Every declared property must be accepted by the handler as a keyword."""
    params = inspect.signature(_FUNCTION_MAP[name]).parameters
    accepts_any = any(p.kind is p.VAR_KEYWORD for p in params.values())
    declared = set(_definition(name)["function"]["parameters"]["properties"])
    if not accepts_any:
        assert declared <= set(params)
    required = set(_definition(name)["function"]["parameters"].get("required", []))
    assert required <= declared


def test_ui_tools_have_no_handler():
    for name in UI_TOOLS:
        assert name not in _FUNCTION_MAP


# --- dispatch routing (handlers mocked) ------------------------------------

@pytest.fixture
def recorded(monkeypatch):
    """Replace every handler with one that records its call and returns a marker."""
    calls = []

    def make(name):
        def handler(**kwargs):
            calls.append((name, kwargs))
            return [{"handled_by": name}]
        return handler

    monkeypatch.setattr(
        dispatch_module, "_FUNCTION_MAP", {n: make(n) for n in QUERY_TOOLS}
    )
    return calls


@pytest.mark.parametrize("name", sorted(QUERY_TOOLS))
def test_dispatch_routes_to_matching_handler(recorded, name):
    result = dispatch(name, {})
    assert result == [{"handled_by": name}]
    assert recorded == [(name, {})]


def test_dict_arguments_are_passed_as_keywords(recorded):
    dispatch("get_top_games_by_copies_sold", {"limit": 3, "genre": "RPG"})
    assert recorded == [("get_top_games_by_copies_sold", {"limit": 3, "genre": "RPG"})]


def test_json_string_arguments_are_decoded(recorded):
    dispatch("get_top_games_by_copies_sold", json.dumps({"limit": 7}))
    assert recorded == [("get_top_games_by_copies_sold", {"limit": 7})]


@pytest.mark.parametrize("empty", ["", "   \n"])
def test_blank_string_arguments_mean_no_arguments(recorded, empty):
    dispatch("get_genre_market_share", empty)
    assert recorded == [("get_genre_market_share", {})]


def test_malformed_json_arguments_raise_and_skip_handler(recorded):
    with pytest.raises(json.JSONDecodeError):
        dispatch("get_genre_market_share", "{not json")
    assert recorded == []


def test_invalid_keyword_arguments_raise_type_error():
    with pytest.raises(TypeError):
        dispatch("get_publisher_class_breakdown", {"bogus_argument": 1})


# --- unknown / UI-handled tools --------------------------------------------

def test_unknown_tool_error_names_tool_and_lists_registered_tools():
    with pytest.raises(ValueError) as exc:
        dispatch("nonexistent_tool", {})
    message = str(exc.value)
    assert "Unknown tool: 'nonexistent_tool'" in message
    for name in QUERY_TOOLS:
        assert name in message


def test_compose_response_is_registered_but_not_dispatchable():
    assert _definition(COMPOSE_RESPONSE_TOOL)
    with pytest.raises(ValueError, match="Unknown tool"):
        dispatch(COMPOSE_RESPONSE_TOOL, {})


def test_tool_name_lookup_is_case_sensitive():
    with pytest.raises(ValueError, match="Unknown tool"):
        dispatch("GET_SCHEMA_INFO", {})
