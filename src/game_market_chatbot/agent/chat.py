"""
Chat agent — wires the OpenRouter LLM to the predefined query tools.

OpenRouter exposes an OpenAI-compatible chat completions API, so the
standard `openai` client is used with `base_url` pointed at OpenRouter.

Tool loop
---------
1. Send the conversation (plus the system prompt) to the model with TOOLS.
2. If the model requests tool calls, handle each one:
     - Predefined query tools and `run_sql_query` are executed via
       tools.dispatch.dispatch().
     - `render_chart` is NOT executed here — its arguments are captured as
       a chart spec and returned on the AgentResponse for the UI layer to
       render (see app.py). The model is told the chart was queued.
3. Tool results are appended to the conversation and the model is called
   again. This repeats until the model returns a plain text answer (or the
   round limit is reached).

The system prompt instructs the model to prefer the predefined query
tools, fall back to `run_sql_query` for open-ended questions, and emit
`render_chart` when a visualisation would add value.

Usage:
    from game_market_chatbot.agent.chat import chat

    response = chat([{"role": "user", "content": "Top 5 genres by sales?"}])
    print(response.text)
    if response.chart_spec:
        ...  # hand the spec to the UI layer

Testing:
    Pass a mock `client` to chat() — no network calls are made. The mock
    only needs to provide `client.chat.completions.create(**kwargs)`
    returning objects shaped like the OpenAI response (choices → message
    with .content and .tool_calls).
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from dotenv import load_dotenv

from game_market_chatbot.tools.dispatch import RENDER_CHART_TOOL, TOOLS, dispatch
from game_market_chatbot.tools.sql_fallback import get_schema_info

load_dotenv()

logger = logging.getLogger(__name__)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "openrouter/free"

# Safety cap on LLM → tool → LLM iterations within a single chat turn.
# Prevents runaway loops if the model keeps requesting tools.
MAX_TOOL_ROUNDS = 10


# ---------------------------------------------------------------------------
# Response type
# ---------------------------------------------------------------------------

@dataclass
class AgentResponse:
    """The agent's final answer for one chat turn.

    Attributes:
        text:       The natural-language answer for the user.
        chart_spec: Chart specification captured from a `render_chart` tool
                    call, with keys chart_type, data, x_field, y_field and
                    title. None when the model answered with text only.
    """

    text: str
    chart_spec: dict[str, Any] | None = None


# ---------------------------------------------------------------------------
# Client / model configuration
# ---------------------------------------------------------------------------

def get_model() -> str:
    """Return the OpenRouter model slug (e.g. 'openai/gpt-4o-mini')."""
    return os.environ.get("OPENROUTER_MODEL", DEFAULT_MODEL)


def get_client():
    """
    Build an OpenAI client pointed at the OpenRouter API.

    Requires OPENROUTER_API_KEY in the environment (or .env file).
    Raises:
        EnvironmentError: If the API key is not set.
    """
    from openai import OpenAI

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "OPENROUTER_API_KEY is not set. "
            "Add it to your .env file to enable the chat agent."
        )
    return OpenAI(base_url=OPENROUTER_BASE_URL, api_key=api_key)


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

def build_system_prompt() -> str:
    """
    Build the system prompt, embedding the live database schema so the
    model can write correct SQL and chooses the right tools.
    """
    return f"""
You are a video game market analyst assistant. You answer questions about
the Steam games market using a local database of ~130,000 games ingested
from Gamalytics.

DATABASE SCHEMA
---------------
{get_schema_info()}

HOW TO ANSWER QUESTIONS
-----------------------
1. ALWAYS ground your answers in data returned by the tools — never guess
   or invent figures.
2. Prefer the predefined query tools (get_top_games_by_copies_sold,
   get_genre_market_share, get_publisher_class_breakdown,
   get_games_by_price_range, get_review_score_distribution,
   get_games_by_release_date) whenever one of them fits the question.
3. For open-ended questions the predefined tools cannot answer, fall back
   to run_sql_query with a read-only SELECT. Call get_schema_info first if
   you are unsure about column names or formats.
4. Remember: genres, developers and publishers are JSON text arrays —
   filter them with LIKE '%value%', never equality. Timestamp columns are
   Unix MILLISECONDS — divide by 1000 before SQLite date functions.

CHARTS
------
When a visualisation would make the answer clearer — rankings, trends,
distributions, comparisons — call the render_chart tool AFTER fetching the
data:
- chart_type: "bar", "line", "scatter" or "pie"
- data: the rows to plot as a list of flat objects. Reuse or aggregate the
  rows returned by a query tool; keep it under ~50 rows.
- x_field / y_field: keys in each data row to plot (for pie charts,
  x_field is the slice label and y_field is the slice value).
- title: a short descriptive chart title.
Call render_chart at most once per answer. The UI renders the chart next
to your text, so do not restate every plotted value in prose. If the
answer is a single number or a short fact, do NOT render a chart.

ANSWER STYLE
------------
Be concise and direct. Lead with the key insight, name specific games and
figures, and note caveats where relevant (estimates, NULL values, etc.).
""".strip()


# ---------------------------------------------------------------------------
# Tool call helpers
# ---------------------------------------------------------------------------

def _parse_arguments(arguments: str | dict | None) -> dict[str, Any]:
    """Normalise tool call arguments (JSON string or dict) to a dict."""
    if isinstance(arguments, dict):
        return arguments
    if not arguments or not str(arguments).strip():
        return {}
    return json.loads(arguments)


def _normalise_chart_spec(args: dict[str, Any]) -> dict[str, Any]:
    """
    Build a clean chart spec from raw render_chart arguments.

    Guarantees the keys the UI layer expects and tolerates the model
    passing `data` as a JSON string instead of a list.
    """
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


def _assistant_message_to_dict(message, tool_calls) -> dict[str, Any]:
    """
    Serialise the assistant message (with tool calls) back into the plain
    dict form the chat completions API expects in the conversation history.
    Works with both real OpenAI response objects and simple test mocks.
    """
    return {
        "role": "assistant",
        "content": getattr(message, "content", None) or "",
        "tool_calls": [
            {
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.function.name,
                    "arguments": (
                        tc.function.arguments
                        if isinstance(tc.function.arguments, str)
                        else json.dumps(tc.function.arguments)
                    ),
                },
            }
            for tc in tool_calls
        ],
    }


def _execute_tool_call(tool_call, *, turn_id: str) -> tuple[str, dict[str, Any] | None]:
    """
    Execute a single tool call.

    Returns:
        A tuple of (tool_result_content, chart_spec). chart_spec is only
        populated for render_chart calls; it is None for all other tools.

    Tool errors are serialised into the result content (rather than raised)
    so the model can see what went wrong and correct itself, e.g. fix a
    malformed SQL query.
    """
    name = tool_call.function.name

    try:
        args = _parse_arguments(tool_call.function.arguments)
    except json.JSONDecodeError as exc:
        logger.info(
            "tool_call",
            extra={"turn_id": turn_id, "tool": name, "status": "error", "duration_ms": 0},
        )
        return json.dumps({"error": f"Invalid tool arguments: {exc}"}), None

    start = time.perf_counter()

    if name == RENDER_CHART_TOOL:
        # Not executed here — captured for the UI layer to render.
        spec = _normalise_chart_spec(args)
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
        result = dispatch(name, args)
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


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def chat(
    messages: list[dict[str, str]],
    *,
    client=None,
    model: str | None = None,
    temperature: float | None = None,
) -> AgentResponse:
    """
    Run one chat turn: send the conversation to the LLM, execute any tool
    calls it requests, and return its final answer.

    Args:
        messages:    Conversation history as a list of {"role", "content"}
                     dicts (user/assistant roles only — the system prompt is
                     prepended internally).
        client:      Optional OpenAI-compatible client. When omitted, one is
                     built from OPENROUTER_API_KEY. Pass a mock in tests.
        model:       Optional OpenRouter model slug. Defaults to the
                     OPENROUTER_MODEL env var, then DEFAULT_MODEL.
        temperature: Optional sampling temperature forwarded to the API.
                     Left unset by default; pass 0 for deterministic evals.

    Returns:
        AgentResponse with the assistant's text and an optional chart spec
        if the model called render_chart during the turn.
    """
    if client is None:
        client = get_client()
    model = model or get_model()

    turn_id = uuid4().hex[:12]

    conversation: list[dict[str, Any]] = [
        {"role": "system", "content": build_system_prompt()},
        *messages,
    ]

    chart_spec: dict[str, Any] | None = None
    last_text = ""

    for round_num in range(MAX_TOOL_ROUNDS):
        logger.info(
            "llm_request",
            extra={
                "turn_id": turn_id,
                "round": round_num,
                "model": model,
                "message_count": len(conversation),
            },
        )
        start = time.perf_counter()
        create_kwargs: dict[str, Any] = {
            "model": model,
            "messages": conversation,
            "tools": TOOLS,
        }
        if temperature is not None:
            create_kwargs["temperature"] = temperature
        try:
            response = client.chat.completions.create(**create_kwargs)
        except Exception:
            logger.exception(
                "llm_request_failed",
                extra={"turn_id": turn_id, "round": round_num},
            )
            raise

        message = response.choices[0].message
        tool_calls = getattr(message, "tool_calls", None) or []
        usage = getattr(response, "usage", None)
        logger.info(
            "llm_response",
            extra={
                "turn_id": turn_id,
                "round": round_num,
                "latency_ms": round((time.perf_counter() - start) * 1000, 1),
                "tool_call_count": len(tool_calls),
                "tool_call_names": [tc.function.name for tc in tool_calls],
                "usage": {
                    "prompt_tokens": getattr(usage, "prompt_tokens", None),
                    "completion_tokens": getattr(usage, "completion_tokens", None),
                    "total_tokens": getattr(usage, "total_tokens", None),
                } if usage is not None else None,
            },
        )

        # No tool calls → this is the final answer.
        if not tool_calls:
            return AgentResponse(
                text=message.content or "",
                chart_spec=chart_spec,
            )

        if message.content:
            last_text = message.content

        conversation.append(_assistant_message_to_dict(message, tool_calls))

        for tool_call in tool_calls:
            result_content, spec = _execute_tool_call(tool_call, turn_id=turn_id)
            if spec is not None:
                chart_spec = spec
            conversation.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result_content,
            })

    # Round limit hit — return whatever text we have rather than looping forever.
    logger.warning("tool_round_limit_reached", extra={"turn_id": turn_id})
    return AgentResponse(
        text=last_text or (
            "I wasn't able to finish researching that question — "
            "please try rephrasing it."
        ),
        chart_spec=chart_spec,
    )
