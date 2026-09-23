"""FastAPI application assembly and development CORS configuration."""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from game_market_chatbot.api.routes import router
from game_market_chatbot.observability import configure_logging

DEFAULT_CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]


def _configured_cors_origins() -> list[str]:
    configured = os.getenv("API_CORS_ORIGINS")
    if configured is None:
        return DEFAULT_CORS_ORIGINS
    return [origin.strip() for origin in configured.split(",") if origin.strip()]


def create_app(*, cors_origins: list[str] | None = None) -> FastAPI:
    configure_logging()
    application = FastAPI(title="Game Market Chatbot API")
    application.add_middleware(
        CORSMiddleware,
        allow_origins=(
            _configured_cors_origins() if cors_origins is None else cors_origins
        ),
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )
    application.include_router(router)
    return application


app = create_app()