"""Tests for tools.render_graph: assets/contribution-graph.svg generation."""

from __future__ import annotations

import datetime
import json
from pathlib import Path

import pytest

from tools.config import load_theme
from tools.render_graph import (
    GraphRenderError,
    load_contribution_records,
    render_graph_svg,
)
from tools.validate_svg import validate_svg_bytes

REPO_ROOT = Path(__file__).resolve().parent.parent
REAL_THEME = REPO_ROOT / "config" / "theme.json"


def _make_document(start: datetime.date, end: datetime.date, *, username: str = "octocat") -> dict:
    days = []
    cursor = start
    while cursor <= end:
        days.append({"date": cursor.isoformat(), "level": 1, "count": 2})
        cursor += datetime.timedelta(days=1)
    return {
        "schema_version": 1,
        "username": username,
        "retrieved_at": "2024-06-15T00:00:00+00:00",
        "source": "test-fixture",
        "days": days,
        "statistics": {},
        "assumptions": [],
    }


def _write_document(tmp_path: Path, document: dict) -> Path:
    path = tmp_path / "contributions.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def test_leap_year_full_range_parses(tmp_path: Path) -> None:
    document = _make_document(datetime.date(2024, 1, 1), datetime.date(2024, 12, 31))
    path = _write_document(tmp_path, document)
    records, loaded_doc = load_contribution_records(path)
    assert len(records) == 366
    assert any(r.date == "2024-02-29" for r in records)
    assert loaded_doc["username"] == "octocat"


def test_missing_dates_are_filled(tmp_path: Path) -> None:
    document = _make_document(datetime.date(2024, 1, 1), datetime.date(2024, 1, 10))
    del document["days"][5]  # remove 2024-01-06
    path = _write_document(tmp_path, document)
    records, _ = load_contribution_records(path)
    dates = [r.date for r in records]
    assert dates == [f"2024-01-{d:02d}" for d in range(1, 11)]
    gap = next(r for r in records if r.date == "2024-01-06")
    assert gap.level == 0
    assert gap.count is None


def test_empty_days_rejected(tmp_path: Path) -> None:
    document = _make_document(datetime.date(2024, 1, 1), datetime.date(2024, 1, 1))
    document["days"] = []
    path = _write_document(tmp_path, document)
    with pytest.raises(GraphRenderError, match="non-empty"):
        load_contribution_records(path)


def test_zero_activity_renders(tmp_path: Path) -> None:
    document = _make_document(datetime.date(2024, 1, 1), datetime.date(2024, 3, 1))
    for day in document["days"]:
        day["level"] = 0
        day["count"] = 0
    path = _write_document(tmp_path, document)
    records, doc = load_contribution_records(path)
    theme = load_theme(REAL_THEME)
    svg = render_graph_svg(records, doc, theme, static=True)
    validate_svg_bytes(svg.encode("utf-8"), source="graph.svg")


def test_chronological_and_weekday_placement(tmp_path: Path) -> None:
    # 2024-01-01 is a Monday.
    document = _make_document(datetime.date(2024, 1, 1), datetime.date(2024, 1, 31))
    path = _write_document(tmp_path, document)
    records, _ = load_contribution_records(path)
    assert datetime.date.fromisoformat(records[0].date).strftime("%A") == "Monday"
    assert [r.date for r in records] == sorted(r.date for r in records)


def test_svg_is_valid_and_has_title_desc(tmp_path: Path) -> None:
    document = _make_document(datetime.date(2024, 1, 1), datetime.date(2024, 6, 30), username="octo & cat")
    path = _write_document(tmp_path, document)
    records, doc = load_contribution_records(path)
    theme = load_theme(REAL_THEME)
    svg = render_graph_svg(records, doc, theme, static=False)
    validate_svg_bytes(svg.encode("utf-8"), source="graph.svg")
    assert "<title>" in svg and "</title>" in svg
    assert "<desc>" in svg
    # Username with '&' must be escaped, never raw, inside the XML text content.
    assert "octo &amp; cat" in svg
    assert "octo & cat" not in svg


def test_static_mode_has_no_animation_classes(tmp_path: Path) -> None:
    document = _make_document(datetime.date(2024, 1, 1), datetime.date(2024, 3, 1))
    path = _write_document(tmp_path, document)
    records, doc = load_contribution_records(path)
    theme = load_theme(REAL_THEME)
    svg = render_graph_svg(records, doc, theme, static=True)
    assert "lt-reveal" not in svg


def test_animated_mode_supports_reduced_motion(tmp_path: Path) -> None:
    document = _make_document(datetime.date(2024, 1, 1), datetime.date(2024, 3, 1))
    path = _write_document(tmp_path, document)
    records, doc = load_contribution_records(path)
    theme = load_theme(REAL_THEME)
    svg = render_graph_svg(records, doc, theme, static=False)
    assert "prefers-reduced-motion" in svg
    assert "lt-reveal" in svg


def test_legend_present(tmp_path: Path) -> None:
    document = _make_document(datetime.date(2024, 1, 1), datetime.date(2024, 3, 1))
    path = _write_document(tmp_path, document)
    records, doc = load_contribution_records(path)
    theme = load_theme(REAL_THEME)
    svg = render_graph_svg(records, doc, theme, static=True)
    assert ">Less<" in svg
    assert ">More<" in svg
    assert "Public GitHub contribution activity" in svg
    assert "2024-06-15" in svg


def test_deterministic_rendering(tmp_path: Path) -> None:
    document = _make_document(datetime.date(2024, 1, 1), datetime.date(2024, 6, 30))
    path = _write_document(tmp_path, document)
    records, doc = load_contribution_records(path)
    theme = load_theme(REAL_THEME)
    first = render_graph_svg(records, doc, theme, static=False)
    second = render_graph_svg(records, doc, theme, static=False)
    assert first == second


def test_no_remote_resources(tmp_path: Path) -> None:
    document = _make_document(datetime.date(2024, 1, 1), datetime.date(2024, 3, 1))
    path = _write_document(tmp_path, document)
    records, doc = load_contribution_records(path)
    theme = load_theme(REAL_THEME)
    svg = render_graph_svg(records, doc, theme, static=False)
    assert svg.count("http://") == 1  # only the SVG namespace declaration
    assert "https://" not in svg
