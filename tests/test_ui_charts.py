"""
Tests for ui/charts.py — the chart-spec → Plotly figure renderer.

render_chart() is a pure function with no Streamlit dependency, so these
tests run headlessly — no browser or `streamlit run` required.
"""

from __future__ import annotations

import plotly.graph_objects as go
import pytest

from game_market_chatbot.ui.charts import render_chart

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
def test_render_chart_returns_plotly_figure(chart_type):
    fig = render_chart(_spec(chart_type))
    assert isinstance(fig, go.Figure)
    assert len(fig.data) > 0  # traces were populated from the spec data


def test_render_chart_sets_title():
    fig = render_chart(_spec("bar"))
    assert fig.layout.title.text == "Total copies sold by genre"


def test_pie_chart_maps_fields_to_names_and_values():
    fig = render_chart(_spec("pie"))
    # x_field → slice labels, y_field → slice values.
    assert list(fig.data[0].labels) == ["Indie", "Action", "Adventure"]
    assert list(fig.data[0].values) == [900_000_000, 800_000_000, 300_000_000]


def test_render_chart_rejects_unknown_chart_type():
    with pytest.raises(ValueError, match="Unsupported chart type"):
        render_chart(_spec("radar"))


@pytest.mark.parametrize("bad_data", [[], "not a list", None])
def test_render_chart_rejects_missing_or_empty_data(bad_data):
    spec = _spec("bar")
    spec["data"] = bad_data
    with pytest.raises(ValueError, match="non-empty list"):
        render_chart(spec)


@pytest.mark.parametrize("field", ["x_field", "y_field"])
def test_render_chart_requires_both_fields(field):
    spec = _spec("bar")
    spec[field] = None
    with pytest.raises(ValueError, match="x_field.*y_field"):
        render_chart(spec)
