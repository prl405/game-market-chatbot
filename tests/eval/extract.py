"""
Parses an agent's free-text answer and scores it against ground truth.

Each `answer_type` in cases.py has a matching `score_*` function here. All
return a ScoreResult so failures carry a human-readable explanation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

_NUMBER_RE = re.compile(r"-?\d[\d,]*\.?\d*")
_PERCENT_PAIR_RE = re.compile(r"([A-Za-z][A-Za-z \-]*?)\D{0,10}?(\d+(?:\.\d+)?)\s*%")
_COUNT_PAIR_RE = re.compile(r"(\d{1,3}-\d{1,3})\D{0,15}?([\d,]+)\s*(?:games?)?")


@dataclass
class ScoreResult:
    passed: bool
    explanation: str


def _first_number(text: str) -> float | None:
    match = _NUMBER_RE.search(text)
    if not match:
        return None
    return float(match.group(0).replace(",", ""))


def score_number(text: str, expected: float, tolerance: float) -> ScoreResult:
    actual = _first_number(text)
    if actual is None:
        return ScoreResult(False, f"No number found in answer: {text!r}")
    diff = abs(actual - expected)
    passed = diff <= tolerance
    return ScoreResult(
        passed,
        f"expected={expected}, found={actual}, diff={diff}, tolerance={tolerance}",
    )


def _jaccard(found: set[str], expected: set[str]) -> float:
    if not expected:
        return 1.0
    intersection = found & expected
    union = found | expected
    return len(intersection) / len(union) if union else 1.0


def score_id_set(
    text: str, expected: list[str], threshold: float,
) -> ScoreResult:
    """Score by substring-matching each expected name against the answer text."""
    lowered = text.lower()
    found = {name for name in expected if name.lower() in lowered}
    similarity = len(found) / len(expected) if expected else 1.0
    passed = similarity >= threshold
    missing = [n for n in expected if n not in found]
    return ScoreResult(
        passed,
        f"recall={similarity:.2f} (threshold={threshold}), missing={missing}",
    )


def score_percent_table(
    text: str, expected: dict[str, float], tolerance: float,
) -> ScoreResult:
    """Extract "<label> ... NN%" pairs and compare each to expected values."""
    pairs = _PERCENT_PAIR_RE.findall(text)
    found: dict[str, float] = {}
    for label, value in pairs:
        label = label.strip().rstrip(":").strip().lower()
        found[label] = float(value)

    mismatches = []
    matched = 0
    for label, expected_value in expected.items():
        actual_value = found.get(label.lower())
        if actual_value is None:
            mismatches.append(f"{label}: not found in answer")
            continue
        diff = abs(actual_value - expected_value)
        if diff > tolerance:
            mismatches.append(
                f"{label}: expected {expected_value}, found {actual_value} (diff {diff})"
            )
        else:
            matched += 1

    passed = matched >= max(1, len(expected) // 2) and not mismatches
    return ScoreResult(
        passed,
        f"matched={matched}/{len(expected)}, mismatches={mismatches}",
    )


def score_count_table(
    text: str, expected: dict[str, int], tolerance: float,
) -> ScoreResult:
    """Extract "<bucket-label> ... NN" pairs and compare each to expected counts."""
    pairs = _COUNT_PAIR_RE.findall(text)
    found: dict[str, int] = {
        label: int(value.replace(",", "")) for label, value in pairs
    }

    mismatches = []
    matched = 0
    for label, expected_value in expected.items():
        actual_value = found.get(label)
        if actual_value is None:
            mismatches.append(f"{label}: not found in answer")
            continue
        diff = abs(actual_value - expected_value)
        if diff > tolerance:
            mismatches.append(
                f"{label}: expected {expected_value}, found {actual_value} (diff {diff})"
            )
        else:
            matched += 1

    passed = matched >= max(1, len(expected) // 2) and not mismatches
    return ScoreResult(
        passed,
        f"matched={matched}/{len(expected)}, mismatches={mismatches}",
    )


def score_publisher_table(
    text: str, expected: list[tuple[str, int]], threshold: float,
) -> ScoreResult:
    """Score by checking that expected top publisher names appear in the text."""
    lowered = text.lower()
    expected_names = [name for name, _ in expected]
    found = [name for name in expected_names if name.lower() in lowered]
    similarity = len(found) / len(expected_names) if expected_names else 1.0
    passed = similarity >= threshold
    return ScoreResult(
        passed,
        f"recall={similarity:.2f} (threshold={threshold}), "
        f"found={found}, expected={expected_names}",
    )


def score(answer_type: str, text: str, expected: Any, case: Any) -> ScoreResult:
    """Dispatch to the right scorer based on the case's answer_type."""
    if answer_type == "number":
        return score_number(text, expected, case.tolerance)
    if answer_type == "id_set":
        return score_id_set(text, expected, case.similarity_threshold)
    if answer_type == "percent_table":
        return score_percent_table(text, expected, case.tolerance)
    if answer_type == "count_table":
        return score_count_table(text, expected, case.tolerance)
    if answer_type == "publisher_table":
        return score_publisher_table(text, expected, case.similarity_threshold)
    raise ValueError(f"Unknown answer_type: {answer_type!r}")
