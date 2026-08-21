"""Tests for tools.pull_contributions.compute_statistics: streaks and aggregates."""

from __future__ import annotations

from tools.pull_contributions import DayRecord, compute_statistics


def _records(levels: list[int], counts: list[int | None] | None = None) -> list[DayRecord]:
    counts = counts or [None] * len(levels)
    dates = [f"2024-01-{day:02d}" for day in range(1, len(levels) + 1)]
    return [
        DayRecord(date=d, level=level, count=count)
        for d, level, count in zip(dates, levels, counts)
    ]


def test_current_streak_counts_trailing_active_days() -> None:
    records = _records([0, 1, 1, 0, 1, 1, 1])
    stats = compute_statistics(records)
    assert stats["current_streak_days"] == 3


def test_current_streak_is_zero_when_last_day_inactive() -> None:
    records = _records([1, 1, 0])
    stats = compute_statistics(records)
    assert stats["current_streak_days"] == 0


def test_longest_streak_finds_best_run() -> None:
    records = _records([1, 0, 1, 1, 1, 1, 0, 1])
    stats = compute_statistics(records)
    assert stats["longest_streak_days"] == 4


def test_known_contribution_total_sums_only_known_counts() -> None:
    records = _records([1, 1, 1], counts=[3, None, 5])
    stats = compute_statistics(records)
    assert stats["known_contribution_days"] == 2
    assert stats["known_contribution_total"] == 8
    assert stats["total_is_complete"] is False


def test_total_is_complete_true_when_all_days_known() -> None:
    records = _records([1, 0], counts=[3, 0])
    stats = compute_statistics(records)
    assert stats["total_is_complete"] is True
    assert stats["known_contribution_total"] == 3


def test_weekday_totals_only_include_known_counts() -> None:
    # 2024-01-01 is a Monday.
    records = _records([1, 1], counts=[5, None])
    stats = compute_statistics(records)
    assert stats["weekday_totals_known"]["Mon"] == 5
    assert sum(stats["weekday_totals_known"].values()) == 5


def test_empty_records_produce_zeroed_statistics() -> None:
    stats = compute_statistics([])
    assert stats["current_streak_days"] == 0
    assert stats["longest_streak_days"] == 0
    assert stats["known_contribution_total"] == 0
    assert stats["total_is_complete"] is True
