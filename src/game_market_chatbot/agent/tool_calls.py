"""Adapters for model tool calls and their results."""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Callable

from game_market_chatbot.tools.dispatch import RENDER_CHART_TOOL


def parse_arguments(arguments: str | dict | None) -> dict[str, Any]:
    """Normalize tool-call arguments to a dictionary."""
    if isinstance(arguments, dict):
        return arguments
    if not arguments or not str(arguments).strip():
        return {}
    return json.loads(arguments)


def normalise_chart_spec(args: dict[str, Any]) -> dict[str, Any]:
    """Build a chart spec while tolerating JSON-encoded data rows."""
    data = args.get("data", [])
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError:
            data = []

    return {
        "chart_type": args.get("chart_type", "bar"),
        "data": data,
        "x_field": args.get("x_field"),
        "y_field": args.get("y_field"),
        "title": args.get("title", ""),
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
        spec = normalise_chart_spec(args)
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

    try:
        result = dispatch_fn(name, args)
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