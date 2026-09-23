"""Validated request and response models for the chat API."""

from __future__ import annotations

import math
from typing import Any, Literal, Annotated

from pydantic import BaseModel, Field, model_validator


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1)


class ChatResponse(BaseModel):
    text: str
    chart_spec: dict[str, Any] | None = None
    blocks: list["ResponseBlock"] = Field(default_factory=list)


class ChartSpecModel(BaseModel):
    chart_type: Literal["bar", "line", "scatter", "pie"]
    data: list[dict[str, Any]] = Field(min_length=1, max_length=50)
    x_field: str = Field(min_length=1)
    y_field: str = Field(min_length=1)
    title: str

    @model_validator(mode="after")
    def validate_rows(self) -> "ChartSpecModel":
        for row in self.data:
            if self.x_field not in row or self.y_field not in row:
                raise ValueError("Chart data rows must include both plotted fields.")
            value = row[self.y_field]
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError("Chart y values must be finite numbers.")
            if self.chart_type == "scatter":
                x_value = row[self.x_field]
                if isinstance(x_value, bool) or not isinstance(x_value, (int, float)) or not math.isfinite(x_value):
                    raise ValueError("Scatter x values must be finite numbers.")
            if self.chart_type == "pie" and value < 0:
                raise ValueError("Pie values cannot be negative.")
        return self


class MarkdownBlock(BaseModel):
    type: Literal["markdown"]
    content: str


class ChartBlock(BaseModel):
    type: Literal["chart"]
    chart: ChartSpecModel


ResponseBlock = Annotated[MarkdownBlock | ChartBlock, Field(discriminator="type")]