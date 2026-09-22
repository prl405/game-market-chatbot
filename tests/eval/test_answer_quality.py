"""
Answer-quality eval suite — runs the real chat agent against the real
database and checks its free-text answer against ground truth computed
independently (see ground_truth.py).

Opt-in only: costs real API tokens and is inherently non-deterministic, so
it is skipped unless RUN_LLM_EVAL is set, and never runs as part of the
regular `pytest` suite.

Usage:
    RUN_LLM_EVAL=1 pytest tests/eval/test_answer_quality.py -v
"""

from __future__ import annotations

import os

import pytest

from game_market_chatbot.agent.chat import chat, get_client, get_model
from game_market_chatbot.db.client import get_connection

from .cases import CASES, EvalCase
from .extract import score
from . import ground_truth as gt

pytestmark = pytest.mark.skipif(
    not os.environ.get("RUN_LLM_EVAL"),
    reason="opt-in LLM eval suite — set RUN_LLM_EVAL=1 to run",
)


@pytest.fixture(scope="session")
def real_db():
    conn = get_connection()
    yield conn
    conn.close()


@pytest.fixture(scope="session")
def real_client():
    return get_client()


def _compute_expected(case: EvalCase, conn):
    """Look up the ground-truth value for a case by its id."""
    if case.id == "top_10_by_copies_sold":
        return gt.top_games_by_copies_sold(conn, limit=10)
    if case.id == "genre_market_share":
        return gt.genre_market_share(conn)
    if case.id == "games_priced_le_9_99":
        return gt.games_priced_at_or_below(conn, threshold=9.99)
    if case.id == "median_price":
        return gt.median_price(conn)
    if case.id == "games_released_2024":
        return gt.games_released_in_year(conn, year=2024)
    if case.id == "review_score_distribution":
        return gt.review_score_distribution(conn)
    if case.id == "top_publishers_by_game_count":
        return gt.top_publishers_by_game_count(conn, top_n=10)
    if case.id == "top_games_in_rpg_genre":
        return gt.top_games_in_genre(conn, genre="RPG", limit=10)
    if case.id == "comparable_games_count":
        return gt.comparable_games_count(conn)
    if case.id == "percentile_95_outliers":
        _threshold, names = gt.percentile_outliers(conn, percentile=95.0)
        return names
    raise ValueError(f"No ground-truth mapping for case id: {case.id!r}")


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test_answer_matches_ground_truth(case: EvalCase, real_db, real_client):
    expected = _compute_expected(case, real_db)

    response = chat(
        [{"role": "user", "content": case.question}],
        client=real_client,
        model=get_model(),
        temperature=0,
    )

    result = score(case.answer_type, response.text, expected, case)
    assert result.passed, (
        f"[{case.id}] {result.explanation}\n---\nAgent answer:\n{response.text}"
    )
