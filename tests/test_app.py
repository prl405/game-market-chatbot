"""
Tests for the chart-spec → Plotly figure mapping in app.py.

These run headlessly — build_chart_figure is a pure function that never
touches Streamlit runtime state, so no browser or `streamlit run` is
required. (The full UI test — loading the app in a browser and sending a
message — is manual, per PLAN.md Task 7.)
"""

from __future__ import annotations

import plotly.graph_objects as go
import pytest

from game_market_chatbot.app import build_chart_figure

DATA = [
    {"genre": "Indie", "total_copies_sold": 900_000_000},
    {"genre": "Action", "total_copies_sold": 800_000_000},
    {"genre": "Adventure", "total_copies_sold": 300_000_000},
]


def _spec(chart_type: str) -> dict:
    return {
        "chart_type": chart_type,
        "data": DATA,
        "x_field": "genre",
        "y_field": "total_copies_sold",
        "title": "Total copies sold by genre",
    }


@pytest.mark.parametrize("chart_type", ["bar", "line", "scatter", "pie"])
def test_build_chart_figure_returns_plotly_figure(chart_type):
    fig = build_chart_figure(_spec(chart_type))
    assert isinstance(fig, go.Figure)
    assert len(fig.data) > 0  # traces were populated from the spec data


def test_build_chart_figure_sets_title():
    fig = build_chart_figure(_spec("bar"))
    assert fig.layout.title.text == "Total copies sold by genre"


def test_build_chart_figure_rejects_unknown_chart_type():
    with pytest.raises(ValueError, match="Unsupported chart type"):
        build_chart_figure(_spec("radar"))
