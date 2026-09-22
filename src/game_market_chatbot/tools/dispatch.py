"""
Assembles the final tool list and dispatches tool calls by name.

Usage:
    from game_market_chatbot.tools.dispatch import TOOLS, dispatch

    # Pass to OpenRouter / OpenAI:
    response = client.chat.completions.create(
        model=..., messages=..., tools=TOOLS
    )

    # Execute a tool call returned by the model:
    result = dispatch(tool_call.function.name, tool_call.function.arguments)
"""

from __future__ import annotations

import json
from typing import Any

from game_market_chatbot.tools.chart_spec import RENDER_CHART_TOOL, _RENDER_CHART_DEFINITION
from game_market_chatbot.tools.query_market import (
    get_genre_market_share,
    get_publisher_class_breakdown,
    get_review_score_distribution,
)
from game_market_chatbot.tools.query_releases import get_games_by_release_date
from game_market_chatbot.tools.query_sales import get_games_by_price_range, get_top_games_by_copies_sold
from game_market_chatbot.tools.sql_fallback import get_schema_info, run_sql_query
from game_market_chatbot.tools.tool_specs import TOOLS as _PREDEFINED_TOOLS

# render_chart travels with the rest of TOOLS so the model can call it, but
# it is deliberately absent from _FUNCTION_MAP — see chart_spec.py.
TOOLS: list[dict[str, Any]] = [*_PREDEFINED_TOOLS, _RENDER_CHART_DEFINITION]

_FUNCTION_MAP = {
    "get_top_games_by_copies_sold":  get_top_games_by_copies_sold,
    "get_genre_market_share":        get_genre_market_share,
    "get_publisher_class_breakdown": get_publisher_class_breakdown,
    "get_games_by_price_range":      get_games_by_price_range,
    "get_review_score_distribution": get_review_score_distribution,
    "get_games_by_release_date":     get_games_by_release_date,
    "get_schema_info":               get_schema_info,
    "run_sql_query":                 run_sql_query,
}


def dispatch(name: str, arguments: str | dict) -> list[dict[str, Any]]:
    """
    Execute a tool call by name with the provided arguments.

    Args:
        name:      The function name from the tool call (must match a key
                   in _FUNCTION_MAP).
        arguments: Either a JSON string or a dict of keyword arguments,
                   as returned by the OpenAI API tool_call.function.arguments.

    Returns:
        The result of the query function — a list of dicts.

    Raises:
        ValueError: If the function name is not registered.
    """
    if name not in _FUNCTION_MAP:
        registered = ", ".join(_FUNCTION_MAP.keys())
        raise ValueError(
            f"Unknown tool: {name!r}. Registered tools: {registered}"
        )

    if isinstance(arguments, str):
        kwargs = json.loads(arguments) if arguments.strip() else {}
    else:
        kwargs = arguments

    return _FUNCTION_MAP[name](**kwargs)
