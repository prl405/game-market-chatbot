"""
OpenAI-format tool definitions for the predefined query tools.

Each entry in TOOLS follows the OpenAI function-calling schema:
  {
    "type": "function",
    "function": {
        "name":        str,
        "description": str,
        "parameters":  JSON Schema object
    }
  }

The agent layer passes TOOLS directly to the `tools` parameter of the
OpenAI chat completions API. The `name` in each definition must exactly
match the function name in queries.py so the agent dispatcher can resolve
tool calls by name.

Usage:
    from game_market_chatbot.tools.registry import TOOLS, dispatch

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

from game_market_chatbot.tools.queries import (
    get_games_by_price_range,
    get_games_by_release_date,
    get_genre_market_share,
    get_publisher_class_breakdown,
    get_review_score_distribution,
    get_top_games_by_copies_sold,
)

# ---------------------------------------------------------------------------
# Tool definitions (OpenAI function-calling schema)
# ---------------------------------------------------------------------------

TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_top_games_by_copies_sold",
            "description": (
                "Return the top N Steam games ranked by total copies sold. "
                "Optionally filter by a single genre (e.g. 'RPG', 'Simulation'). "
                "Use this to identify market leaders, compare performance within "
                "a genre, or find benchmarks for a specific category."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Number of games to return. Default 10, max 100.",
                        "default": 10,
                    },
                    "genre_filter": {
                        "type": "string",
                        "description": (
                            "Optional genre to filter by, e.g. 'RPG', 'Action', "
                            "'Simulation'. Matched case-insensitively against the "
                            "game's genre list. Omit to query across all genres."
                        ),
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_genre_market_share",
            "description": (
                "Return total copies sold, game count, and average review score "
                "for every genre on Steam, sorted by total copies sold. "
                "Use this to compare genre sizes, identify dominant markets, "
                "or find underserved niches."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_publisher_class_breakdown",
            "description": (
                "Return game count, total copies sold, average copies sold, "
                "average review score, and average price grouped by publisher "
                "class (AAA, AA, Indie, Hobbyist). "
                "Use this to compare how different tiers of developer perform "
                "commercially and critically."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_games_by_price_range",
            "description": (
                "Return games within a price band (USD), ordered by copies sold. "
                "Use this to analyse competition at a specific price point, "
                "understand what games a new release would compete against, "
                "or find comparables for pricing strategy."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "min_price": {
                        "type": "number",
                        "description": "Minimum price in USD (inclusive). Default 0.",
                        "default": 0.0,
                    },
                    "max_price": {
                        "type": "number",
                        "description": "Maximum price in USD (inclusive). Default 70.",
                        "default": 70.0,
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum rows to return. Default 50, max 200.",
                        "default": 50,
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_review_score_distribution",
            "description": (
                "Return a histogram of Steam games bucketed by review score "
                "in 10-point bands (0-9, 10-19, …, 90-100), including game "
                "count and total/average copies sold per band. "
                "Use this to understand the relationship between review quality "
                "and commercial performance, or to assess how hard a quality "
                "bar is to reach."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_games_by_release_date",
            "description": (
                "Return games released within a date window, ordered by release "
                "date or copies sold. Optionally filter by genre. "
                "Use this to analyse release trends over time, find games that "
                "launched in a specific year or period, or assess how a market "
                "segment has evolved."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "year_from": {
                        "type": "integer",
                        "description": (
                            "Start year (inclusive), e.g. 2020. "
                            "Omit for no lower bound."
                        ),
                    },
                    "year_to": {
                        "type": "integer",
                        "description": (
                            "End year (inclusive), e.g. 2023. "
                            "Omit for no upper bound."
                        ),
                    },
                    "month_from": {
                        "type": "integer",
                        "description": (
                            "Start month 1–12, only used when year_from is set. "
                            "Defaults to January (1)."
                        ),
                    },
                    "month_to": {
                        "type": "integer",
                        "description": (
                            "End month 1–12, only used when year_to is set. "
                            "Defaults to December (12)."
                        ),
                    },
                    "genre_filter": {
                        "type": "string",
                        "description": (
                            "Optional genre to filter by, e.g. 'Indie', 'RPG'. "
                            "Matched against the JSON genres array."
                        ),
                    },
                    "order_by": {
                        "type": "string",
                        "enum": ["release_date", "copies_sold"],
                        "description": (
                            "Sort order. 'release_date' (default) returns newest "
                            "first. 'copies_sold' returns best-selling first."
                        ),
                        "default": "release_date",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum rows to return. Default 50, max 200.",
                        "default": 50,
                    },
                },
                "required": [],
            },
        },
    },
]

# ---------------------------------------------------------------------------
# Dispatcher — maps function name → callable
# ---------------------------------------------------------------------------

_FUNCTION_MAP = {
    "get_top_games_by_copies_sold":  get_top_games_by_copies_sold,
    "get_genre_market_share":        get_genre_market_share,
    "get_publisher_class_breakdown": get_publisher_class_breakdown,
    "get_games_by_price_range":      get_games_by_price_range,
    "get_review_score_distribution": get_review_score_distribution,
    "get_games_by_release_date":     get_games_by_release_date,
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
