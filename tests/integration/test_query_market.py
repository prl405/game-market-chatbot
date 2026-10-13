"""
Integration tests for tools.query_market against the seeded in-memory db fixture.
"""

from __future__ import annotations

from game_market_chatbot.tools.query_market import (
    get_genre_market_share,
    get_publisher_class_breakdown,
    get_review_score_distribution,
)



# ---------------------------------------------------------------------------
# get_genre_market_share
# ---------------------------------------------------------------------------

class TestGetGenreMarketShare:

    def test_returns_list_of_dicts(self, db):
        results = get_genre_market_share(conn=db)
        assert isinstance(results, list)
        assert len(results) > 0

    def test_expected_keys_present(self, db):
        expected = {"genre", "game_count", "total_copies_sold",
                    "avg_copies_sold", "avg_review_score"}
        for row in get_genre_market_share(conn=db):
            assert expected.issubset(row.keys())

    def test_sorted_by_total_copies_sold_desc(self, db):
        results = get_genre_market_share(conn=db)
        totals = [r["total_copies_sold"] for r in results]
        assert totals == sorted(totals, reverse=True)

    def test_action_genre_present(self, db):
        results = get_genre_market_share(conn=db)
        genres = [r["genre"] for r in results]
        assert "Action" in genres

    def test_game_count_correct_for_action(self, db):
        # Action games in fixtures: steam_id 1, 4, 6 = 3 games with copies_sold.
        results = get_genre_market_share(conn=db)
        action = next(r for r in results if r["genre"] == "Action")
        assert action["game_count"] == 3

    def test_empty_genres_not_returned(self, db):
        # No fixture game has "Sports" as its only genre contributing —
        # only Racing Sim has Sports. Verify no genre with 0 games appears.
        results = get_genre_market_share(conn=db)
        for row in results:
            assert row["game_count"] > 0

    def test_null_copies_excluded_from_totals(self, db):
        # "Unreleased Game" (steam_id=7) has NULL copies_sold and genres=["Action"].
        # Its NULL must not contribute to Action's total_copies_sold.
        results = get_genre_market_share(conn=db)
        action = next((r for r in results if r["genre"] == "Action"), None)
        if action:
            # Sum of Action games with non-NULL copies: 30M + 50M + 150k = 80,150,000
            assert action["total_copies_sold"] == 80_150_000


# ---------------------------------------------------------------------------
# get_publisher_class_breakdown
# ---------------------------------------------------------------------------

class TestGetPublisherClassBreakdown:

    def test_returns_list_of_dicts(self, db):
        results = get_publisher_class_breakdown(conn=db)
        assert isinstance(results, list)
        assert len(results) > 0

    def test_expected_keys_present(self, db):
        expected = {"publisher_class", "game_count", "total_copies_sold",
                    "avg_copies_sold", "avg_review_score", "avg_price"}
        for row in get_publisher_class_breakdown(conn=db):
            assert expected.issubset(row.keys())

    def test_all_four_classes_present(self, db):
        results = get_publisher_class_breakdown(conn=db)
        classes = {r["publisher_class"] for r in results}
        assert {"AAA", "AA", "Indie", "Hobbyist"}.issubset(classes)

    def test_sorted_by_total_copies_sold_desc(self, db):
        results = get_publisher_class_breakdown(conn=db)
        totals = [r["total_copies_sold"] for r in results]
        assert totals == sorted(totals, reverse=True)

    def test_aaa_has_highest_total(self, db):
        results = get_publisher_class_breakdown(conn=db)
        top = results[0]["publisher_class"]
        # AAA games: 30M + 50M + 12M = 92M — should be highest.
        assert top == "AAA"

    def test_game_count_correct_for_indie(self, db):
        results = get_publisher_class_breakdown(conn=db)
        indie = next(r for r in results if r["publisher_class"] == "Indie")
        # Indie games with non-NULL copies: steam_id 2, 8 = 2 games.
        assert indie["game_count"] == 2

    def test_null_copies_excluded(self, db):
        results = get_publisher_class_breakdown(conn=db)
        aa = next(r for r in results if r["publisher_class"] == "AA")
        # AA games with non-NULL: steam_id 3, 5, 9 = 3 games (7 has NULL).
        assert aa["game_count"] == 3


# ---------------------------------------------------------------------------
# get_review_score_distribution
# ---------------------------------------------------------------------------

class TestGetReviewScoreDistribution:

    def test_returns_list_of_dicts(self, db):
        results = get_review_score_distribution(conn=db)
        assert isinstance(results, list)
        assert len(results) > 0

    def test_expected_keys_present(self, db):
        expected = {"bucket_label", "min_score", "max_score",
                    "game_count", "total_copies_sold", "avg_copies_sold"}
        for row in get_review_score_distribution(conn=db):
            assert expected.issubset(row.keys())

    def test_ordered_by_bucket_asc(self, db):
        results = get_review_score_distribution(conn=db)
        min_scores = [r["min_score"] for r in results]
        assert min_scores == sorted(min_scores)

    def test_bucket_label_format(self, db):
        results = get_review_score_distribution(conn=db)
        for row in results:
            label = row["bucket_label"]
            assert "-" in label
            low, high = label.split("-")
            assert low.isdigit() and high.isdigit()

    def test_min_max_score_consistent_with_label(self, db):
        results = get_review_score_distribution(conn=db)
        for row in results:
            assert row["min_score"] <= row["max_score"]
            assert row["bucket_label"] == f"{row['min_score']}-{row['max_score']}"

    def test_null_review_scores_excluded(self, db):
        # "Unreleased Game" has NULL review_score — total game count across
        # all buckets must not include it.
        results = get_review_score_distribution(conn=db)
        total_counted = sum(r["game_count"] for r in results)
        # 9 games have non-NULL review_score (all except steam_id 7).
        assert total_counted == 9

    def test_game_count_correct_for_90s_bucket(self, db):
        # Games with review_score 90-99: steam_id 1 (95), 2 (97), 5 (91) = 3.
        results = get_review_score_distribution(conn=db)
        bucket_90 = next((r for r in results if r["min_score"] == 90), None)
        assert bucket_90 is not None
        assert bucket_90["game_count"] == 3

    def test_no_bucket_has_zero_game_count(self, db):
        results = get_review_score_distribution(conn=db)
        for row in results:
            assert row["game_count"] > 0
