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
build_chart_figure() maps a chart spec to a Plotly figure using Plotly
Express. Task 8 extracts/extends this into ui/charts.py — it lives here
for now so Task 7 is self-contained.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import streamlit as st

from game_market_chatbot.agent.chat import AgentResponse, chat


# ---------------------------------------------------------------------------
# Chart rendering (Task 8 will move/expand this into ui/charts.py)
# ---------------------------------------------------------------------------

def build_chart_figure(spec: dict[str, Any]):
    """
    Build a Plotly figure from an agent-produced chart spec.

    Args:
        spec: Dict with keys chart_type ("bar" | "line" | "scatter" | "pie"),
              data (list of flat dicts), x_field, y_field and title.

    Returns:
        A plotly.graph_objects.Figure.

    Raises:
        ValueError: If the chart type is not supported.
    """
    import plotly.express as px

    chart_type = spec.get("chart_type")
    data = spec.get("data", [])
    x_field = spec.get("x_field")
    y_field = spec.get("y_field")
    title = spec.get("title", "")

    if chart_type == "bar":
        return px.bar(data, x=x_field, y=y_field, title=title)
    if chart_type == "line":
        return px.line(data, x=x_field, y=y_field, title=title)
    if chart_type == "scatter":
        return px.scatter(data, x=x_field, y=y_field, title=title)
    if chart_type == "pie":
        return px.pie(data, names=x_field, values=y_field, title=title)

    raise ValueError(f"Unsupported chart type: {chart_type!r}")


def _render_chart(spec: dict[str, Any]) -> None:
    """Render a chart spec inline, degrading gracefully on failure."""
    try:
        fig = build_chart_figure(spec)
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
