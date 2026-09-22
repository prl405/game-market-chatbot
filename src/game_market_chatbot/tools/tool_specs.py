"""
OpenAI-format tool schema definitions for the predefined query tools.

Each entry follows the OpenAI function-calling schema:
  {
    "type": "function",
    "function": {
        "name":        str,
        "description": str,
        "parameters":  JSON Schema object
    }
  }

The `name` in each definition must exactly match a function name in
query_sales.py / query_market.py / query_releases.py / sql_fallback.py so
dispatch.py can resolve tool calls by name. render_chart is defined
separately in chart_spec.py and appended by dispatch.py.
"""

from __future__ import annotations

from typing import Any

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
    {
        "type": "function",
        "function": {
            "name": "get_schema_info",
            "description": (
                "Return a plain-text description of the steam_games database schema, "
                "including column names, types, index definitions, and critical notes "
                "on JSON array columns and millisecond timestamps. "
                "Call this before writing a run_sql_query call if you are unsure "
                "about column names or data formats."
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
            "name": "run_sql_query",
            "description": (
                "Execute a raw read-only SELECT statement against the steam_games "
                "database and return up to 500 rows as a list of dicts. "
                "Use this as a fallback for complex or ad-hoc questions that the "
                "predefined tools cannot answer. "
                "IMPORTANT — JSON array columns: genres, developers, and publishers "
                "are stored as JSON text (e.g. '[\"Action\",\"RPG\"]'). Always filter "
                "them with LIKE, e.g. WHERE genres LIKE '%RPG%'. Never use equality. "
                "IMPORTANT — timestamps: release_date, first_release_date, "
                "ea_release_date, and ingested_at are Unix timestamps in MILLISECONDS. "
                "Divide by 1000 before passing to SQLite date functions, e.g. "
                "strftime('%Y', release_date / 1000, 'unixepoch')."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "sql": {
                        "type": "string",
                        "description": (
                            "A read-only SELECT statement. Must not contain "
                            "INSERT, UPDATE, DELETE, DROP, CREATE, ALTER, "
                            "REPLACE, TRUNCATE, ATTACH, DETACH, or PRAGMA."
                        ),
                    },
                },
                "required": ["sql"],
            },
        },
    },
]
