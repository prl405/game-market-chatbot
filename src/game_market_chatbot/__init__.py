"""
game-market-chatbot CLI entry point.

Available commands:
    game-market-chatbot db init
        Initialise the database schema (idempotent).

    game-market-chatbot ingest <source>
        Run the ingestion script for the named source.
        Available sources: gamalytics
"""

from __future__ import annotations

import sys


def main() -> None:
    args = sys.argv[1:]

    if not args:
        _print_help()
        sys.exit(0)

    command = args[0]

    if command == "db":
        _handle_db(args[1:])
    elif command == "ingest":
        _handle_ingest(args[1:])
    else:
        print(f"Unknown command: {command!r}", file=sys.stderr)
        _print_help()
        sys.exit(1)


def _handle_db(args: list[str]) -> None:
    if not args or args[0] == "init":
        from game_market_chatbot.db.client import init_db
        init_db()
    else:
        print(f"Unknown db subcommand: {args[0]!r}", file=sys.stderr)
        sys.exit(1)


def _handle_ingest(args: list[str]) -> None:
    if not args:
        print("Usage: game-market-chatbot ingest <source>", file=sys.stderr)
        sys.exit(1)

    source = args[0]

    from game_market_chatbot.ingestion import REGISTRY
    if source not in REGISTRY:
        available = ", ".join(REGISTRY.keys())
        print(
            f"Unknown ingestion source: {source!r}. Available: {available}",
            file=sys.stderr,
        )
        sys.exit(1)

    ingester_cls = REGISTRY[source]
    ingester_cls().ingest()


def _print_help() -> None:
    print(__doc__)
