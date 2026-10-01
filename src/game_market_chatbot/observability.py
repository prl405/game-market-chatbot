"""
Logging setup for observability into LLM API calls and tool execution.

Emits one JSON object per log line (timestamp, level, logger, message, plus
any `extra` fields such as turn_id/round/latency_ms/usage) to stdout and to
a rotating file at logs/app.log.

Usage:
    from game_market_chatbot.observability import configure_logging

    configure_logging()  # call once at process start
"""

from __future__ import annotations

import json
import logging
import logging.handlers
import os
from pathlib import Path

LOG_DIR = Path("logs")
LOG_FILE = LOG_DIR / "app.log"

# Attributes present on every LogRecord — anything else was passed via `extra`.
_STANDARD_RECORD_ATTRS = set(logging.LogRecord("", 0, "", 0, "", None, None).__dict__)


class JsonFormatter(logging.Formatter):
    """Render each log record as a single JSON line, including `extra` fields."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in _STANDARD_RECORD_ATTRS:
                payload[key] = value
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(level: str | None = None) -> None:
    """
    Configure root logging with JSON output to stdout and logs/app.log.

    Idempotent — safe to call repeatedly without installing duplicate handlers.
    """
    root = logging.getLogger()
    if getattr(root, "_game_market_chatbot_configured", False):
        return

    root.setLevel(level or os.environ.get("LOG_LEVEL", "INFO"))

    formatter = JsonFormatter()

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    root.addHandler(stream_handler)

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3
    )
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    root._game_market_chatbot_configured = True
