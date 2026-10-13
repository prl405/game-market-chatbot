"""Unit tests for db.client path resolution, connection, and init_db."""

from __future__ import annotations

import pytest

from game_market_chatbot.db import client


@pytest.fixture()
def local_db_path(tmp_path, monkeypatch):
    path = tmp_path / "nested" / "test.db"
    monkeypatch.setenv("DB_PATH", str(path))
    monkeypatch.delenv("TURSO_AUTH_TOKEN", raising=False)
    return path


def _table_names(path):
    conn = client.get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        return {r[0] for r in cur.fetchall()}
    finally:
        conn.close()


class TestGetDbPath:
    def test_returns_env_value(self, monkeypatch):
        monkeypatch.setenv("DB_PATH", "/some/where.db")
        assert client.get_db_path() == "/some/where.db"

    def test_defaults_when_unset(self, monkeypatch):
        monkeypatch.delenv("DB_PATH", raising=False)
        assert client.get_db_path() == "./data/games.db"


class TestIsRemote:
    @pytest.mark.parametrize(
        "path", ["libsql://db.turso.io", "https://db.turso.io"]
    )
    def test_remote_urls(self, path):
        assert client._is_remote(path) is True

    @pytest.mark.parametrize("path", ["./data/games.db", "/abs/x.db", ":memory:"])
    def test_local_paths(self, path):
        assert client._is_remote(path) is False


class TestGetConnection:
    def test_local_creates_parent_dir_and_connects(self, local_db_path):
        assert not local_db_path.parent.exists()
        conn = client.get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT 1")
            assert cur.fetchone()[0] == 1
        finally:
            conn.close()
        assert local_db_path.parent.is_dir()

    def test_remote_without_token_raises(self, monkeypatch):
        monkeypatch.setenv("DB_PATH", "libsql://x.turso.io")
        monkeypatch.delenv("TURSO_AUTH_TOKEN", raising=False)
        with pytest.raises(EnvironmentError, match="TURSO_AUTH_TOKEN"):
            client.get_connection()

    def test_remote_with_token_uses_serverless_client(self, monkeypatch):
        calls = {}

        def fake_connect(url, auth_token):
            calls["args"] = (url, auth_token)
            return "fake-conn"

        monkeypatch.setenv("DB_PATH", "libsql://x.turso.io")
        monkeypatch.setenv("TURSO_AUTH_TOKEN", "tok")
        monkeypatch.setattr(client.turso_serverless, "connect", fake_connect)

        assert client.get_connection() == "fake-conn"
        assert calls["args"] == ("libsql://x.turso.io", "tok")

    def test_parent_path_is_a_file_raises_oserror(self, tmp_path, monkeypatch):
        blocker = tmp_path / "blocker"
        blocker.write_text("not a directory")
        monkeypatch.setenv("DB_PATH", str(blocker / "sub" / "games.db"))
        with pytest.raises(OSError):
            client.get_connection()


class TestInitDb:
    def test_creates_steam_games_table(self, local_db_path, capsys):
        client.init_db()
        assert "steam_games" in _table_names(local_db_path)
        assert "Database initialised at" in capsys.readouterr().out

    def test_is_idempotent(self, local_db_path):
        client.init_db()
        client.init_db()
        assert "steam_games" in _table_names(local_db_path)

    def test_does_not_drop_existing_data(self, local_db_path):
        client.init_db()
        conn = client.get_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO steam_games (steam_id, name) VALUES (1, 'Kept')"
        )
        conn.commit()
        conn.close()

        client.init_db()

        conn = client.get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT name FROM steam_games WHERE steam_id = 1")
            assert cur.fetchone()[0] == "Kept"
        finally:
            conn.close()

    def test_remote_path_is_rejected(self, monkeypatch):
        monkeypatch.setenv("DB_PATH", "libsql://x.turso.io")
        with pytest.raises(RuntimeError, match="only supported for local"):
            client.init_db()

    def test_invalid_local_path_raises(self, tmp_path, monkeypatch):
        blocker = tmp_path / "blocker"
        blocker.write_text("x")
        monkeypatch.setenv("DB_PATH", str(blocker / "games.db"))
        with pytest.raises(OSError):
            client.init_db()
