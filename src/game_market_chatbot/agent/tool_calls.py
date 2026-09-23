"""Adapters for model tool calls and their results."""

from __future__ import annotations

import json
import logging
import math
import time
from typing import Any, Callable

from game_market_chatbot.tools.chart_spec import COMPOSE_RESPONSE_TOOL
from game_market_chatbot.tools.dispatch import RENDER_CHART_TOOL


def parse_arguments(arguments: str | dict | None) -> dict[str, Any]:
    """Normalize tool-call arguments to a dictionary."""
    if isinstance(arguments, dict):
        return arguments
    if not arguments or not str(arguments).strip():
        return {}
    return json.loads(arguments)


def normalise_chart_spec(
    args: dict[str, Any],
    query_results: dict[str, list[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    """Build a chart spec and reject malformed data before it reaches the UI."""
    chart_type = args.get("chart_type", "bar")
    if chart_type == "histogram":
        source_call_id = args.get("source_call_id")
        value_field = args.get("value_field")
        if not isinstance(source_call_id, str) or not source_call_id:
            raise ValueError("Histogram charts require a source_call_id.")
        if not isinstance(value_field, str) or not value_field:
            raise ValueError("Histogram charts require a value_field.")
        source_rows = (query_results or {}).get(source_call_id)
        if source_rows is None:
            raise ValueError("Histogram source must reference an earlier query result in this turn.")
        values = [
            row[value_field]
            for row in source_rows
            if isinstance(row, dict)
            and value_field in row
            and not isinstance(row[value_field], bool)
            and isinstance(row[value_field], (int, float))
            and math.isfinite(row[value_field])
        ]
        if not values:
            raise ValueError("Histogram source has no finite numeric values for that field.")

        minimum = min(values)
        maximum = max(values)
        bin_count = min(20, math.ceil(math.sqrt(len(values))))
        if minimum == maximum:
            padding = max(abs(minimum) * 1e-9, 1.0)
            lower = minimum - padding
            upper = maximum + padding
            if not math.isfinite(lower):
                lower = minimum
            if not math.isfinite(upper):
                upper = maximum
            if lower == upper:
                lower, upper = minimum - 1.0, maximum + 1.0
            bin_count = 1
        else:
            lower, upper = minimum, maximum

        width = (upper - lower) / bin_count
        counts = [0] * bin_count
        for value in values:
            index = min(int((value - lower) / width), bin_count - 1)
            counts[index] += 1
        data = [
            {
                "bin_start": lower + index * width,
                "bin_end": upper if index == bin_count - 1 else lower + (index + 1) * width,
                "count": counts[index],
            }
            for index in range(bin_count)
        ]
        return {
            "chart_type": chart_type,
            "data": data,
            "x_field": "bin_start",
            "x_end_field": "bin_end",
            "y_field": "count",
            "title": str(args.get("title", "")),
        }

    data = args.get("data", [])
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError:
            data = []

    x_field = args.get("x_field")
    y_field = args.get("y_field")
    if not isinstance(chart_type, str) or chart_type not in {"bar", "line", "scatter", "pie"}:
        raise ValueError("Unsupported chart type.")
    if not isinstance(data, list) or not 1 <= len(data) <= 50:
        raise ValueError("Chart data must contain between 1 and 50 rows.")
    if not isinstance(x_field, str) or not x_field or not isinstance(y_field, str) or not y_field:
        raise ValueError("Chart x_field and y_field must be non-empty strings.")

    for row in data:
        if not isinstance(row, dict) or x_field not in row or y_field not in row:
            raise ValueError("Each chart row must contain the plotted fields.")
        y_value = row[y_field]
        if isinstance(y_value, bool) or not isinstance(y_value, (int, float)) or not math.isfinite(y_value):
            raise ValueError("Chart y values must be finite numbers.")
        if chart_type == "scatter":
            x_value = row[x_field]
            if isinstance(x_value, bool) or not isinstance(x_value, (int, float)) or not math.isfinite(x_value):
                raise ValueError("Scatter x values must be finite numbers.")
        if chart_type == "pie" and y_value < 0:
            raise ValueError("Pie values cannot be negative.")

    return {
        "chart_type": chart_type,
        "data": data,
        "x_field": x_field,
        "y_field": y_field,
        "title": str(args.get("title", "")),
    }


def assistant_message_to_dict(message, tool_calls) -> dict[str, Any]:
    """Serialize an assistant response containing tool calls."""
    return {
        "role": "assistant",
        "content": getattr(message, "content", None) or "",
        "tool_calls": [
            {
                "id": tool_call.id,
                "type": "function",
                "function": {
                    "name": tool_call.function.name,
                    "arguments": (
                        tool_call.function.arguments
                        if isinstance(tool_call.function.arguments, str)
                        else json.dumps(tool_call.function.arguments)
                    ),
                },
            }
            for tool_call in tool_calls
        ],
    }


def execute_tool_call(
    tool_call,
    *,
    turn_id: str,
    dispatch_fn: Callable,
    logger: logging.Logger,
    query_results: dict[str, list[dict[str, Any]]] | None = None,
) -> tuple[str, dict[str, Any] | None]:
    """Execute a tool or capture a chart request, returning model content."""
    name = tool_call.function.name

    try:
        args = parse_arguments(tool_call.function.arguments)
    except json.JSONDecodeError as exc:
        logger.info(
            "tool_call",
            extra={"turn_id": turn_id, "tool": name, "status": "error", "duration_ms": 0},
        )
        return json.dumps({"error": f"Invalid tool arguments: {exc}"}), None

    start = time.perf_counter()

    if name == RENDER_CHART_TOOL:
        try:
            spec = normalise_chart_spec(args, query_results)
        except ValueError as exc:
            logger.info(
                "tool_call",
                extra={"turn_id": turn_id, "tool": name, "status": "error", "duration_ms": 0},
            )
            return json.dumps({"error": str(exc)}), None
        logger.info(
            "tool_call",
            extra={
                "turn_id": turn_id,
                "tool": name,
                "tool_args": args,
                "status": "ok",
                "duration_ms": round((time.perf_counter() - start) * 1000, 1),
            },
        )
        return (
            json.dumps({
                "status": "ok",
                "message": "Chart queued — it will be rendered alongside your reply.",
            }),
            spec,
        )

    if name == COMPOSE_RESPONSE_TOOL:
        logger.info(
            "tool_call",
            extra={
                "turn_id": turn_id,
                "tool": name,
                "tool_args": args,
                "status": "ok",
                "duration_ms": round((time.perf_counter() - start) * 1000, 1),
            },
        )
        return json.dumps(args), None

    try:
        result = dispatch_fn(name, args)
        if (
            query_results is not None
            and isinstance(result, list)
            and len(result) <= 1000
            and all(isinstance(row, dict) for row in result)
        ):
            query_results[tool_call.id] = result
        logger.info(
            "tool_call",
            extra={
                "turn_id": turn_id,
                "tool": name,
                "tool_args": args,
                "status": "ok",
                "duration_ms": round((time.perf_counter() - start) * 1000, 1),
            },
        )
        return json.dumps(result, default=str), None
    except Exception as exc:
        logger.info(
            "tool_call",
            extra={
                "turn_id": turn_id,
                "tool": name,
                "tool_args": args,
                "status": "error",
                "duration_ms": round((time.perf_counter() - start) * 1000, 1),
            },
        )
        return json.dumps({"error": f"{type(exc).__name__}: {exc}"}), None