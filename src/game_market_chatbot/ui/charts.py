"""
Plotly chart renderer for LLM-generated chart specs.

The agent layer (agent/chat.py) captures `render_chart` tool calls as chart
specs — plain dicts describing what to plot. This module turns a spec into
a Plotly figure; the Streamlit app then passes the figure to
st.plotly_chart.

Spec format:
    {
        "chart_type": "bar" | "line" | "scatter" | "pie",
        "data":       [{"genre": "Action", "total": 123}, …],   # flat dicts
        "x_field":    "genre",   # x-axis key        (pie: slice label)
        "y_field":    "total",   # y-axis key        (pie: slice value)
        "title":      "Total copies sold by genre",
    }

render_chart() is a pure function with no Streamlit dependency, so it is
fully testable headlessly. Invalid specs raise ValueError — the caller
(app.py) catches this, shows a warning, and still displays the model's
text answer.
"""

from __future__ import annotations

from typing import Any

import plotly.express as px
import plotly.graph_objects as go

SUPPORTED_CHART_TYPES = ("bar", "line", "scatter", "pie")


def render_chart(spec: dict[str, Any]) -> go.Figure:
    """
    Build a Plotly figure from an agent-produced chart spec.

    Args:
        spec: Dict with keys:
            chart_type  "bar" | "line" | "scatter" | "pie"
            data        Non-empty list of flat dicts (rows to plot).
            x_field     Key in each row for the x-axis. For pie charts this
                        is the slice label field (mapped to `names`).
            y_field     Key in each row for the y-axis. For pie charts this
                        is the slice value field (mapped to `values`).
            title       Chart title.

    Returns:
        A plotly.graph_objects.Figure ready for st.plotly_chart.

    Raises:
        ValueError: If the chart type is unsupported, data is missing or
                    empty, or x_field/y_field are absent.
    """
    chart_type = spec.get("chart_type")
    data = spec.get("data", [])
    x_field = spec.get("x_field")
    y_field = spec.get("y_field")
    title = spec.get("title", "")

    if chart_type not in SUPPORTED_CHART_TYPES:
        raise ValueError(
            f"Unsupported chart type: {chart_type!r}. "
            f"Supported types: {', '.join(SUPPORTED_CHART_TYPES)}"
        )

    if not isinstance(data, list) or not data:
        raise ValueError(
            "Chart spec 'data' must be a non-empty list of dicts, "
            f"got: {type(data).__name__}"
        )

    if not x_field or not y_field:
        raise ValueError(
            "Chart spec requires both 'x_field' and 'y_field', "
            f"got x_field={x_field!r}, y_field={y_field!r}"
        )

    if chart_type == "bar":
        return px.bar(data, x=x_field, y=y_field, title=title)
    if chart_type == "line":
        return px.line(data, x=x_field, y=y_field, title=title)
    if chart_type == "scatter":
        return px.scatter(data, x=x_field, y=y_field, title=title)

    # chart_type == "pie" — x_field is the slice label, y_field the value.
    return px.pie(data, names=x_field, values=y_field, title=title)
