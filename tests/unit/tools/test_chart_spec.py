"""Unit tests for chart-spec normalisation and the render_chart definition.

Exercises normalise_chart_spec directly, independent of the chat loop.
"""

from __future__ import annotations

import json

import pytest

from game_market_chatbot.agent.tool_calls import normalise_chart_spec
from game_market_chatbot.tools.chart_spec import COMPOSE_RESPONSE_TOOL
from game_market_chatbot.tools.dispatch import RENDER_CHART_TOOL, TOOLS, dispatch


def _bar(**overrides):
    args = {
        "chart_type": "bar",
        "data": [{"genre": "RPG", "copies": 12}],
        "x_field": "genre",
        "y_field": "copies",
        "title": "Copies by genre",
    }
    args.update(overrides)
    return args


def _hist(**overrides):
    args = {
        "chart_type": "histogram",
        "source_call_id": "query_1",
        "value_field": "score",
        "title": "Score distribution",
    }
    args.update(overrides)
    return args


# --- standard charts -------------------------------------------------------

@pytest.mark.parametrize("chart_type", ["bar", "line", "scatter", "pie"])
def test_supported_chart_types_are_normalised(chart_type):
    data = [{"genre": 3, "copies": 12}] if chart_type == "scatter" else None
    args = _bar(chart_type=chart_type, **({"data": data} if data else {}))
    assert normalise_chart_spec(args) == args


def test_chart_type_defaults_to_bar():
    args = _bar()
    del args["chart_type"]
    assert normalise_chart_spec(args)["chart_type"] == "bar"


def test_chart_spec_tolerates_json_string_data():
    rows = [{"publisher_class": "Indie", "game_count": 5}]
    spec = normalise_chart_spec({
        "chart_type": "pie",
        "data": json.dumps(rows),
        "x_field": "publisher_class",
        "y_field": "game_count",
        "title": "Games by publisher class",
    })
    assert spec["data"] == rows
    assert spec["chart_type"] == "pie"


def test_missing_title_becomes_empty_string():
    args = _bar()
    del args["title"]
    assert normalise_chart_spec(args)["title"] == ""


@pytest.mark.parametrize(
    "data",
    [
        [{"genre": "RPG", "copies": float("nan")}],
        [{"genre": "RPG", "copies": float("inf")}],
        [{"genre": "RPG", "copies": "12"}],
        [{"genre": "RPG", "copies": True}],
        [{"genre": "RPG"}],
        ["not a row"],
    ],
)
def test_chart_specs_reject_invalid_values(data):
    with pytest.raises(ValueError):
        normalise_chart_spec(_bar(data=data))


def test_chart_row_count_boundaries():
    rows = [{"genre": f"g{i}", "copies": i} for i in range(50)]
    assert len(normalise_chart_spec(_bar(data=rows))["data"]) == 50
    with pytest.raises(ValueError, match="between 1 and 50 rows"):
        normalise_chart_spec(_bar(data=rows + [{"genre": "x", "copies": 1}]))
    with pytest.raises(ValueError, match="between 1 and 50 rows"):
        normalise_chart_spec(_bar(data=[]))


def test_unparseable_json_string_data_is_rejected():
    with pytest.raises(ValueError, match="between 1 and 50 rows"):
        normalise_chart_spec(_bar(data="not json"))


def test_unsupported_chart_type_is_rejected():
    with pytest.raises(ValueError, match="Unsupported chart type"):
        normalise_chart_spec(_bar(chart_type="radar"))


@pytest.mark.parametrize("field", ["x_field", "y_field"])
def test_missing_axis_field_is_rejected(field):
    args = _bar()
    del args[field]
    with pytest.raises(ValueError, match="x_field and y_field"):
        normalise_chart_spec(args)


def test_scatter_requires_numeric_x_values():
    args = _bar(chart_type="scatter")  # x values are strings
    with pytest.raises(ValueError, match="Scatter x values"):
        normalise_chart_spec(args)
    ok = _bar(chart_type="scatter", data=[{"genre": 3, "copies": 4}])
    assert normalise_chart_spec(ok)["data"] == [{"genre": 3, "copies": 4}]


def test_pie_rejects_negative_but_accepts_zero():
    with pytest.raises(ValueError, match="negative"):
        normalise_chart_spec(_bar(chart_type="pie", data=[{"genre": "a", "copies": -1}]))
    spec = normalise_chart_spec(_bar(chart_type="pie", data=[{"genre": "a", "copies": 0}]))
    assert spec["data"][0]["copies"] == 0


# --- histograms ------------------------------------------------------------

@pytest.mark.parametrize(("row_count", "expected_bins"), [(100, 10), (1000, 20)])
def test_histogram_uses_prior_query_values_and_adaptive_bins(row_count, expected_bins):
    rows = [{"score": value} for value in range(row_count)]

    spec = normalise_chart_spec(_hist(), {"query_1": rows})

    assert spec["chart_type"] == "histogram"
    assert len(spec["data"]) == expected_bins
    assert sum(row["count"] for row in spec["data"]) == row_count
    assert spec["x_field"] == "bin_start"
    assert spec["x_end_field"] == "bin_end"
    assert spec["y_field"] == "count"
    assert spec["title"] == "Score distribution"


def test_histogram_bins_are_contiguous_and_span_the_data():
    rows = [{"score": v} for v in (0, 5, 10, 10)]

    data = normalise_chart_spec(_hist(), {"query_1": rows})["data"]

    assert data[0]["bin_start"] == 0
    assert data[-1]["bin_end"] == 10
    for left, right in zip(data, data[1:]):
        assert left["bin_end"] == pytest.approx(right["bin_start"])
    assert data[-1]["count"] >= 2  # the maximum lands in the last bin


def test_histogram_rejects_missing_or_non_numeric_source_values():
    with pytest.raises(ValueError, match="earlier query result"):
        normalise_chart_spec(_hist(), {"other_query": [{"score": 1}]})
    with pytest.raises(ValueError, match="no finite numeric values"):
        normalise_chart_spec(_hist(), {"query_1": [{"score": True}, {"score": "2"}]})


def test_histogram_ignores_non_finite_and_non_numeric_rows():
    rows = [{"score": 1}, {"score": float("nan")}, {"score": "x"}, {"other": 3}, {"score": 3}]

    data = normalise_chart_spec(_hist(), {"query_1": rows})["data"]

    assert sum(row["count"] for row in data) == 2


@pytest.mark.parametrize("missing", ["source_call_id", "value_field"])
def test_histogram_requires_source_and_value_field(missing):
    args = _hist()
    del args[missing]
    with pytest.raises(ValueError, match=missing):
        normalise_chart_spec(args, {"query_1": [{"score": 1}]})


def test_histogram_constant_values_produce_one_nonzero_width_bin():
    spec = normalise_chart_spec(_hist(title="Constant scores"), {"query_1": [{"score": 5}] * 100})

    assert len(spec["data"]) == 1
    assert spec["data"][0]["bin_start"] < 5 < spec["data"][0]["bin_end"]
    assert spec["data"][0]["count"] == 100


# --- tool registration -----------------------------------------------------

def test_render_chart_tool_is_registered_but_not_dispatchable():
    """render_chart travels with TOOLS but is excluded from the dispatcher."""
    names = [t["function"]["name"] for t in TOOLS]
    assert RENDER_CHART_TOOL in names
    assert COMPOSE_RESPONSE_TOOL in names

    with pytest.raises(ValueError, match="Unknown tool"):
        dispatch(RENDER_CHART_TOOL, {})


def test_render_chart_tool_schema_has_required_fields():
    definition = next(t for t in TOOLS if t["function"]["name"] == RENDER_CHART_TOOL)
    params = definition["function"]["parameters"]
    assert set(params["required"]) == {"chart_type", "title"}
    assert {"data", "x_field", "y_field", "source_call_id", "value_field"}.issubset(
        params["properties"]
    )
    assert params["properties"]["chart_type"]["enum"] == [
        "bar", "line", "scatter", "pie", "histogram",
    ]
