"""
Database client — supports both local Turso (SQLite) and Turso Cloud.

The connection mode is determined by the DB_PATH environment variable:

  Local file (default, used for ingestion and local development):
      DB_PATH=./data/games.db
      Uses the `turso` library (embedded SQLite engine, DB-API 2.0).

  Turso Cloud (used for the deployed app):
      DB_PATH=libsql://<your-db-name>.turso.io
      TURSO_AUTH_TOKEN=<token>
      Uses the `turso_serverless` library (DB-API 2.0 over the Turso HTTP API).

Usage is identical in both modes:
    from game_market_chatbot.db.client import get_connection

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM steam_games")
    rows = cur.fetchall()
    conn.close()
"""

from __future__ import annotations

import os
from pathlib import Path

import turso
import turso_serverless
from dotenv import load_dotenv

load_dotenv()

_DEFAULT_DB_PATH = "./data/games.db"


def get_db_path() -> str:
    """Return the raw DB_PATH value from the environment."""
    return os.environ.get("DB_PATH", _DEFAULT_DB_PATH)


def _is_remote(db_path: str) -> bool:
    return db_path.startswith("libsql://") or db_path.startswith("https://")


def get_connection():
    """
    Return a DB-API 2.0 compatible connection for the configured DB_PATH.

    Local  → turso.Connection  (embedded SQLite, full read/write)
    Remote → turso_serverless.Connection  (Turso Cloud HTTP API, read/write)
    """
    db_path = get_db_path()

    if _is_remote(db_path):
        token = os.environ.get("TURSO_AUTH_TOKEN", "")
        if not token:
            raise EnvironmentError(
                "TURSO_AUTH_TOKEN must be set when DB_PATH is a remote Turso URL."
            )
        return turso_serverless.connect(url=db_path, auth_token=token)

    # Local file path — create the parent directory if needed.
    local_path = Path(db_path).resolve()
    local_path.parent.mkdir(parents=True, exist_ok=True)
    return turso.connect(str(local_path))


def init_db() -> None:
    """
    Create all tables and indexes defined in schema.sql.

    Safe to run multiple times — all statements use IF NOT EXISTS.
    Only supported for local databases; to initialise Turso Cloud push
    your local file using the CLI:
        turso db create game-market-chatbot --from-file data/games.db
    """
    db_path = get_db_path()
    if _is_remote(db_path):
        raise RuntimeError(
            "db init is only supported for local databases.\n"
            "To initialise Turso Cloud, push your local database:\n"
            "  turso db create game-market-chatbot --from-file data/games.db"
        )

    schema_path = Path(__file__).parent / "schema.sql"
    sql = schema_path.read_text()

    conn = get_connection()
    try:
        cursor = conn.cursor()
        for statement in sql.split(";"):
            statement = statement.strip()
            if statement:
                cursor.execute(statement)
        conn.commit()
        print(f"Database initialised at: {Path(db_path).resolve()}")
    finally:
        conn.close()
