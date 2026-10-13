"""Unit tests for API request/response model validation (no HTTP app)."""

from __future__ import annotations

import math
from typing import Any

import pytest
from pydantic import ValidationError

from game_market_chatbot.api.models import (
    ChartBlock,
    ChartSpecModel,
    ChatRequest,
    ChatResponse,
    MarkdownBlock,
)


def bar_spec(**overrides: Any) -> dict[str, Any]:
    spec: dict[str, Any] = {
        "chart_type": "bar",
        "data": [{"genre": "RPG", "copies": 12}],
        "x_field": "genre",
        "y_field": "copies",
        "title": "Copies by genre",
    }
    spec.update(overrides)
    return spec


def histogram_spec(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "chart_type": "histogram",
        "data": rows,
        "x_field": "start",
        "x_end_field": "end",
        "y_field": "count",
        "title": "Distribution",
    }


class TestChatRequest:
    def test_parses_valid_transcript(self) -> None:
        request = ChatRequest.model_validate(
            {
                "messages": [
                    {"role": "user", "content": "Hi"},
                    {"role": "assistant", "content": "Hello"},
                ]
            }
        )

        assert [(m.role, m.content) for m in request.messages] == [
            ("user", "Hi"),
            ("assistant", "Hello"),
        ]

    @pytest.mark.parametrize(
        "payload",
        [
            {},
            {"messages": []},
            {"messages": [{"role": "system", "content": "x"}]},
            {"messages": [{"role": "user", "content": None}]},
            {"messages": [{"role": "user"}]},
        ],
    )
    def test_rejects_invalid_payloads(self, payload: dict[str, Any]) -> None:
        with pytest.raises(ValidationError):
            ChatRequest.model_validate(payload)


class TestChartSpecModel:
    def test_valid_bar_spec_round_trips_without_empty_x_end_field(self) -> None:
        dumped = ChartSpecModel.model_validate(bar_spec()).model_dump()

        assert dumped == bar_spec()
        assert "x_end_field" not in dumped

    @pytest.mark.parametrize("chart_type", ["bar", "line", "pie"])
    def test_accepts_category_chart_types(self, chart_type: str) -> None:
        spec = ChartSpecModel.model_validate(bar_spec(chart_type=chart_type))

        assert spec.chart_type == chart_type

    def test_accepts_numeric_scatter(self) -> None:
        spec = ChartSpecModel.model_validate(
            bar_spec(chart_type="scatter", data=[{"genre": 1.5, "copies": 2}])
        )

        assert spec.data == [{"genre": 1.5, "copies": 2}]

    def test_accepts_zero_pie_value(self) -> None:
        ChartSpecModel.model_validate(
            bar_spec(chart_type="pie", data=[{"genre": "A", "copies": 0}])
        )

    @pytest.mark.parametrize(
        "overrides",
        [
            {"chart_type": "radar"},
            {"data": []},
            {"x_field": ""},
            {"y_field": ""},
            {"title": None},
            {"data": [{"genre": "RPG"}]},
            {"data": [{"copies": 1}]},
            {"data": [{"genre": "RPG", "copies": "12"}]},
            {"data": [{"genre": "RPG", "copies": True}]},
            {"data": [{"genre": "RPG", "copies": math.nan}]},
            {"data": [{"genre": "RPG", "copies": math.inf}]},
        ],
    )
    def test_rejects_invalid_bar_specs(self, overrides: dict[str, Any]) -> None:
        with pytest.raises(ValidationError):
            ChartSpecModel.model_validate(bar_spec(**overrides))

    @pytest.mark.parametrize(
        "x_value", ["one", True, math.nan]
    )
    def test_rejects_non_numeric_scatter_x(self, x_value: Any) -> None:
        with pytest.raises(ValidationError, match="Scatter x values"):
            ChartSpecModel.model_validate(
                bar_spec(chart_type="scatter", data=[{"genre": x_value, "copies": 2}])
            )

    def test_rejects_negative_pie_value(self) -> None:
        with pytest.raises(ValidationError, match="Pie values"):
            ChartSpecModel.model_validate(
                bar_spec(chart_type="pie", data=[{"genre": "A", "copies": -1}])
            )

    def test_row_count_boundary_is_50(self) -> None:
        def rows(n: int) -> list[dict[str, Any]]:
            return [{"genre": str(i), "copies": i} for i in range(n)]

        assert len(ChartSpecModel.model_validate(bar_spec(data=rows(50))).data) == 50
        with pytest.raises(ValidationError):
            ChartSpecModel.model_validate(bar_spec(data=rows(51)))


class TestHistogramSpec:
    def test_accepts_ordered_intervals_and_keeps_x_end_field(self) -> None:
        spec = ChartSpecModel.model_validate(
            histogram_spec(
                [
                    {"start": 0, "end": 5, "count": 3},
                    {"start": 5, "end": 10, "count": 0},
                ]
            )
        )

        assert spec.x_end_field == "end"
        assert spec.model_dump()["x_end_field"] == "end"

    def test_requires_x_end_field(self) -> None:
        spec = histogram_spec([{"start": 0, "end": 5, "count": 3}])
        del spec["x_end_field"]

        with pytest.raises(ValidationError, match="x_end_field"):
            ChartSpecModel.model_validate(spec)

    def test_bin_count_boundary_is_20(self) -> None:
        def bins(n: int) -> list[dict[str, Any]]:
            return [{"start": i, "end": i + 1, "count": 1} for i in range(n)]

        ChartSpecModel.model_validate(histogram_spec(bins(20)))
        with pytest.raises(ValidationError, match="20 bins"):
            ChartSpecModel.model_validate(histogram_spec(bins(21)))

    @pytest.mark.parametrize(
        ("rows", "message"),
        [
            ([{"start": 0, "end": 6, "count": 1}, {"start": 5, "end": 10, "count": 1}], "non-overlapping"),
            ([{"start": 5, "end": 5, "count": 1}], "increasing"),
            ([{"start": 0, "end": 5, "count": -1}], "nonnegative"),
            ([{"start": 0, "end": 5}], "both boundaries"),
            ([{"start": 0, "end": "5", "count": 1}], "finite numbers"),
            ([{"start": 0, "end": math.inf, "count": 1}], "finite numbers"),
        ],
    )
    def test_rejects_invalid_bins(self, rows: list[dict[str, Any]], message: str) -> None:
        with pytest.raises(ValidationError, match=message):
            ChartSpecModel.model_validate(histogram_spec(rows))


class TestChatResponse:
    def test_defaults_to_no_chart_and_no_blocks(self) -> None:
        response = ChatResponse(text="hi")

        assert response.chart_spec is None
        assert response.blocks == []

    def test_parses_blocks_by_type_discriminator(self) -> None:
        response = ChatResponse.model_validate(
            {
                "text": "hi",
                "blocks": [
                    {"type": "markdown", "content": "hi"},
                    {"type": "chart", "chart": bar_spec()},
                ],
            }
        )

        assert isinstance(response.blocks[0], MarkdownBlock)
        assert isinstance(response.blocks[1], ChartBlock)
        assert response.blocks[1].chart.title == "Copies by genre"

    @pytest.mark.parametrize(
        "block",
        [
            {"type": "image", "content": "x"},
            {"type": "chart", "chart": bar_spec(data=[])},
            {"type": "markdown"},
        ],
    )
    def test_rejects_invalid_blocks(self, block: dict[str, Any]) -> None:
        with pytest.raises(ValidationError):
            ChatResponse.model_validate({"text": "hi", "blocks": [block]})
