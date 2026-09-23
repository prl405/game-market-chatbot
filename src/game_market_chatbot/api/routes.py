"""HTTP routes delegating requests to the existing chat agent."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from game_market_chatbot.agent.chat import chat
from game_market_chatbot.api.models import ChatRequest, ChatResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/api/chat", response_model=ChatResponse)
def create_chat_response(request: ChatRequest) -> ChatResponse:
    messages = [message.model_dump() for message in request.messages]
    try:
        response = chat(messages)
    except Exception as exc:
        logger.exception("chat_request_failed")
        raise HTTPException(
            status_code=500,
            detail="Chat request failed.",
        ) from exc

    blocks = response.blocks
    if blocks is None:
        blocks = ([{"type": "markdown", "content": response.text}] if response.text else [])
        if response.chart_spec is not None:
            blocks.append({"type": "chart", "chart": response.chart_spec})
    return ChatResponse(text=response.text, chart_spec=response.chart_spec, blocks=blocks)