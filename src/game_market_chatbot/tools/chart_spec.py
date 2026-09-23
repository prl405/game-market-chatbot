"""Definition for the chart tool whose arguments are captured by the agent.

render_chart is included with the model-facing tools but deliberately absent
from dispatch._FUNCTION_MAP. The agent returns its arguments as a chart spec
for the client to render; dispatching this tool by name raises ValueError.
"""

from __future__ import annotations

from typing import Any

RENDER_CHART_TOOL = "render_chart"
COMPOSE_RESPONSE_TOOL = "compose_response"

_RENDER_CHART_DEFINITION: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": RENDER_CHART_TOOL,
        "description": (
            "Queue a chart that can be placed within your composed answer. "
            "Call this AFTER fetching data with another tool — pass the rows "
            "you want to plot (keep it under ~50 rows; aggregate or trim "
            "larger results first). The chart appears next to your reply, so "
            "you do not need to restate every value in prose. "
            "Use bar for rankings/comparisons, line for trends over time, "
            "scatter for relationships between two numeric fields, and pie "
            "for share-of-total breakdowns."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "chart_type": {
                    "type": "string",
                    "enum": ["bar", "line", "scatter", "pie"],
                    "description": "The type of chart to render.",
                },
                "data": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": (
                        "Rows to plot as a list of flat objects, e.g. "
                        "[{\"genre\": \"Action\", \"total_copies_sold\": 123}, …]. "
                        "Typically copied (or aggregated) from a query tool result."
                    ),
                },
                "x_field": {
                    "type": "string",
                    "description": (
                        "Key in each data row for the x-axis. "
                        "For pie charts this is the slice label field."
                    ),
                },
                "y_field": {
                    "type": "string",
                    "description": (
                        "Key in each data row for the y-axis. "
                        "For pie charts this is the slice value field."
                    ),
                },
                "title": {
                    "type": "string",
                    "description": "Short descriptive chart title.",
                },
            },
            "required": ["chart_type", "data", "x_field", "y_field", "title"],
        },
    },
}

_COMPOSE_RESPONSE_DEFINITION: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": COMPOSE_RESPONSE_TOOL,
        "description": (
            "Return the complete user-facing answer as ordered content blocks. "
            "Use markdown blocks for prose and tables, and chart blocks to place "
            "previously requested charts at the correct point in the answer."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "blocks": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string", "enum": ["markdown", "chart"]},
                            "content": {
                                "type": "string",
                                "description": "Markdown text, required for markdown blocks.",
                            },
                            "chart_index": {
                                "type": "integer",
                                "minimum": 0,
                                "description": "Queued chart index, required for chart blocks.",
                            },
                        },
                        "required": ["type"],
                        "additionalProperties": False,
                    },
                }
            },
            "required": ["blocks"],
            "additionalProperties": False,
        },
    },
}
