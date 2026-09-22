"""
Streamlit chat UI for the game market chatbot.

Run with:
    uv run game-market-chatbot app

Layout
------
- Sidebar: "Data Info" panel showing the database row count and the last
  ingestion timestamp (from the ingested_at column).
- Main area: chat history rendered with st.chat_message. Assistant messages
  that carry a chart spec (produced by the agent's render_chart tool call)
  render a Plotly chart inline below the text with st.plotly_chart.
- Bottom: st.chat_input sends the user's message to agent.chat().

Session state
-------------
st.session_state.messages: list of {"role", "content", "chart_spec"} dicts.
The full history is replayed on every Streamlit rerun, so charts persist
across turns. Only {"role", "content"} pairs are forwarded to the agent.

Chart rendering
---------------
Figure construction lives in ui/charts.py (render_chart). app.py calls it
and passes the resulting figure to st.plotly_chart; failures degrade to a
warning while the text answer is still displayed.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import streamlit as st

from game_market_chatbot.agent.chat import AgentResponse, chat
from game_market_chatbot.ui.charts import render_chart


# ---------------------------------------------------------------------------
# Chart rendering — figure construction lives in ui/charts.py (Task 8);
# this wrapper adds Streamlit display with graceful failure.
# ---------------------------------------------------------------------------

def _render_chart(spec: dict[str, Any]) -> None:
    """Render a chart spec inline, degrading gracefully on failure."""
    try:
        fig = render_chart(spec)
        st.plotly_chart(fig, use_container_width=True)
    except Exception as exc:
        st.warning(f"Chart could not be rendered: {exc}")


# ---------------------------------------------------------------------------
# Sidebar — data info panel
# ---------------------------------------------------------------------------

def get_data_info() -> dict[str, Any] | None:
    """
    Fetch row count and last ingestion timestamp from the database.

    Returns None when the database is unavailable (not initialised yet,
    unreachable Turso Cloud, …) so the sidebar can degrade gracefully.
    """
    try:
        from game_market_chatbot.db.client import get_connection

        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*), MAX(ingested_at) FROM steam_games"
            )
            row_count, last_ingested_ms = cursor.fetchone()
        finally:
            conn.close()
    except Exception:
        return None

    last_ingested = None
    if last_ingested_ms:
        last_ingested = datetime.fromtimestamp(
            last_ingested_ms / 1000, tz=timezone.utc
        ).strftime("%Y-%m-%d %H:%M UTC")

    return {"row_count": row_count, "last_ingested": last_ingested}


def _render_sidebar() -> None:
    with st.sidebar:
        st.header("Data Info")
        info = get_data_info()
        if info is None:
            st.info(
                "Database unavailable. Run "
                "`uv run game-market-chatbot db init` and ingest data first."
            )
        else:
            st.metric("Games in database", f"{info['row_count']:,}")
            st.caption(f"Last ingested: {info['last_ingested'] or 'never'}")


# ---------------------------------------------------------------------------
# Chat history
# ---------------------------------------------------------------------------

def _init_session_state() -> None:
    if "messages" not in st.session_state:
        st.session_state.messages = []


def _render_history() -> None:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message.get("chart_spec"):
                _render_chart(message["chart_spec"])


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    st.set_page_config(page_title="Game Market Chatbot", page_icon="🎮")
    _init_session_state()
    _render_sidebar()

    st.title("🎮 Game Market Chatbot")
    st.caption(
        "Ask questions about the Steam games market — sales, genres, "
        "pricing, review scores and more."
    )

    _render_history()

    if prompt := st.chat_input("Ask about the Steam games market…"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Forward only role/content pairs — chart specs are UI-only state.
        history = [
            {"role": m["role"], "content": m["content"]}
            for m in st.session_state.messages
        ]

        with st.chat_message("assistant"):
            with st.spinner("Thinking…"):
                try:
                    response = chat(history)
                except Exception as exc:
                    response = AgentResponse(text=f"⚠️ Something went wrong: {exc}")

            st.markdown(response.text)
            if response.chart_spec:
                _render_chart(response.chart_spec)

        st.session_state.messages.append({
            "role": "assistant",
            "content": response.text,
            "chart_spec": response.chart_spec,
        })


if __name__ == "__main__":
    main()
