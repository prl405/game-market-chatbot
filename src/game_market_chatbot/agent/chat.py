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
             a chart spec and returned on the AgentResponse for the client to
             render. The model is told the chart was queued.
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
        ...  # hand the spec to the client

Testing:
    Pass a mock `client` to chat() — no network calls are made. The mock
    only needs to provide `client.chat.completions.create(**kwargs)`
    returning objects shaped like the OpenAI response (choices → message
    with .content and .tool_calls).
"""

from __future__ import annotations

import logging
import json
import time
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from game_market_chatbot.agent.config import (
    DEFAULT_MODEL,
    OPENROUTER_BASE_URL,
    build_system_prompt,
    get_client,
    get_model,
)
from game_market_chatbot.agent.tool_calls import (
    assistant_message_to_dict,
    execute_tool_call,
)
from game_market_chatbot.tools.chart_spec import COMPOSE_RESPONSE_TOOL
from game_market_chatbot.tools.dispatch import TOOLS, dispatch

logger = logging.getLogger(__name__)

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
    blocks: list[dict[str, Any]] | None = None


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

    chart_specs: list[dict[str, Any]] = []
    composed_blocks: list[dict[str, Any]] | None = None
    composition_request: dict[str, Any] | None = None
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
            text = message.content or last_text
            if composition_request is not None:
                try:
                    requested_blocks = composition_request["blocks"]
                    if not isinstance(requested_blocks, list):
                        raise ValueError("Response blocks must be a list.")
                    resolved: list[dict[str, Any]] = []
                    for block in requested_blocks:
                        if not isinstance(block, dict):
                            raise ValueError("Response blocks must be objects.")
                        if block.get("type") == "markdown" and isinstance(block.get("content"), str):
                            resolved.append({"type": "markdown", "content": block["content"]})
                        elif block.get("type") == "chart":
                            chart_index = block.get("chart_index")
                            if isinstance(chart_index, bool) or not isinstance(chart_index, int) or not 0 <= chart_index < len(chart_specs):
                                raise ValueError("Chart block references an unavailable chart.")
                            resolved.append({"type": "chart", "chart": chart_specs[chart_index]})
                        else:
                            raise ValueError("Unsupported response block.")
                    composed_blocks = resolved
                except (KeyError, TypeError, ValueError):
                    composed_blocks = None
            if composed_blocks is not None:
                text = "\n\n".join(
                    block["content"]
                    for block in composed_blocks
                    if block["type"] == "markdown"
                )
                return AgentResponse(
                    text=text,
                    chart_spec=next(
                        (block["chart"] for block in composed_blocks if block["type"] == "chart"),
                        None,
                    ),
                    blocks=composed_blocks,
                )
            fallback_blocks = ([{"type": "markdown", "content": text}] if text else [])
            fallback_blocks.extend({"type": "chart", "chart": chart} for chart in chart_specs)
            return AgentResponse(
                text=text,
                chart_spec=chart_specs[0] if chart_specs else None,
                blocks=fallback_blocks,
            )

        if message.content:
            last_text = message.content

        conversation.append(assistant_message_to_dict(message, tool_calls))

        for tool_call in tool_calls:
            result_content, spec = execute_tool_call(
                tool_call,
                turn_id=turn_id,
                dispatch_fn=dispatch,
                logger=logger,
            )
            if spec is not None:
                chart_specs.append(spec)
            if tool_call.function.name == COMPOSE_RESPONSE_TOOL:
                try:
                    composition_request = json.loads(result_content)
                except json.JSONDecodeError:
                    composition_request = None
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
        chart_spec=chart_specs[0] if chart_specs else None,
        blocks=composed_blocks or [
            *([{"type": "markdown", "content": last_text}] if last_text else []),
            *({"type": "chart", "chart": chart} for chart in chart_specs),
        ],
    )
