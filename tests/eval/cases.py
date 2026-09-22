"""
The 10 eval cases: natural-language question + how to score the answer.

Ground truth for each case is computed lazily by test_answer_quality.py via
tests/eval/ground_truth.py, using each case's `id` to pick the right
ground-truth function — kept here only as metadata, not values, so the
suite always compares against freshly computed truth from the live DB.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class EvalCase:
    id: str
    question: str
    answer_type: Literal[
        "number", "id_set", "percent_table", "count_table", "publisher_table"
    ]
    tolerance: float = 0.0
    similarity_threshold: float = 0.8  # used by id_set / table scoring


CASES: list[EvalCase] = [
    EvalCase(
        id="top_10_by_copies_sold",
        question="What are the top 10 games by copies sold? Write them as text.",
        answer_type="id_set",
    ),
    EvalCase(
        id="genre_market_share",
        question=(
            "What percentage share of total copies sold does each genre "
            "represent? Write them as text."
        ),
        answer_type="percent_table",
        tolerance=2.0,  # percentage points
    ),
    EvalCase(
        id="games_priced_le_9_99",
        question="How many games are priced at $9.99 or below? Write the answer as text.",
        answer_type="number",
        tolerance=0,
    ),
    EvalCase(
        id="median_price",
        question="What is the median price of games in the dataset? Write the answer as text.",
        answer_type="number",
        tolerance=0.5,
    ),
    EvalCase(
        id="games_released_2024",
        question="How many games were released in 2024? Write the answer as text.",
        answer_type="number",
        tolerance=0,
    ),
    EvalCase(
        id="review_score_distribution",
        question=(
            "Give me the distribution of games across review-score bands "
            "(0-9, 10-19, ..., 90-100), with the game count in each band. Write the answer as text."
        ),
        answer_type="count_table",
        tolerance=5,  # game-count tolerance per bucket
    ),
    EvalCase(
        id="top_publishers_by_game_count",
        question="Which publishers have released the most games? Write the answer as text.",
        answer_type="publisher_table",
        similarity_threshold=0.6,
    ),
    EvalCase(
        id="top_games_in_rpg_genre",
        question="What are the top games in the RPG genre by copies sold? Write them as text.",
        answer_type="id_set",
    ),
    EvalCase(
        id="comparable_games_count",
        question=(
            "How many games are comparable to a $10-30 Indie RPG released "
            "between 2020 and 2024? Write the answer as text."
        ),
        answer_type="number",
        tolerance=0,
    ),
    EvalCase(
        id="percentile_95_outliers",
        question=(
            "Which games are 95th-percentile outlier successes by copies "
            "sold? Write them as text."
        ),
        answer_type="id_set",
        similarity_threshold=0.5,  # long list — partial overlap is acceptable
    ),
]
