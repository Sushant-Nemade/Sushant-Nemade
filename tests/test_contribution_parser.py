"""Tests for tools.pull_contributions: HTML parsing, validation, and write safety.

No test in this module performs live network access.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.pull_contributions import (
    ContributionDataError,
    DayRecord,
    _atomic_write_json,
    _main,
    is_valid_document,
    parse_contributions_html,
    validate_records,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _wrap(cells_html: str) -> str:
    return (
        "<!DOCTYPE html><html><body>"
        f'<table class="ContributionCalendar-grid"><tbody><tr>{cells_html}</tr></tbody></table>'
        "</body></html>"
    )


def test_valid_full_year_response_parses() -> None:
    html_text = (FIXTURES / "contributions-sample.html").read_text(encoding="utf-8")
    records = parse_contributions_html(html_text)
    assert len(records) == 366  # 2024 fixture is a leap year
    assert records[0].date == "2024-01-01"
    assert records[-1].date == "2024-12-31"
    validate_records(records)  # should not raise


def test_empty_response_rejected() -> None:
    html_text = (FIXTURES / "contributions-empty.html").read_text(encoding="utf-8")
    with pytest.raises(ContributionDataError, match="no recognizable"):
        parse_contributions_html(html_text)


def test_malformed_response_rejected() -> None:
    html_text = (FIXTURES / "contributions-malformed.html").read_text(encoding="utf-8")
    with pytest.raises(ContributionDataError, match="no recognizable"):
        parse_contributions_html(html_text)


def test_truly_empty_string_rejected() -> None:
    with pytest.raises(ContributionDataError, match="empty HTML"):
        parse_contributions_html("   ")


def test_missing_day_is_filled_with_unknown_placeholder() -> None:
    html_text = _wrap(
        '<td data-date="2024-01-01" data-level="1" aria-label="2 contributions on January 1, 2024."></td>'
        # 2024-01-02 intentionally missing
        '<td data-date="2024-01-03" data-level="0" aria-label="No contributions on January 3, 2024."></td>'
    )
    records = parse_contributions_html(html_text)
    assert [r.date for r in records] == ["2024-01-01", "2024-01-02", "2024-01-03"]
    gap = records[1]
    assert gap.level == 0
    assert gap.count is None


def test_duplicate_dates_are_deduplicated() -> None:
    html_text = _wrap(
        '<td data-date="2024-01-01" data-level="1" aria-label="1 contribution on January 1, 2024."></td>'
        '<td data-date="2024-01-01" data-level="3" aria-label="9 contributions on January 1, 2024."></td>'
    )
    records = parse_contributions_html(html_text)
    assert len(records) == 1
    assert records[0].level == 3
    assert records[0].count == 9


def test_invalid_date_rejected() -> None:
    html_text = _wrap('<td data-date="not-a-date" data-level="1"></td>')
    with pytest.raises(ContributionDataError, match="invalid date"):
        parse_contributions_html(html_text)


def test_missing_count_yields_none_not_zero() -> None:
    html_text = _wrap('<td data-date="2024-01-01" data-level="2"></td>')
    records = parse_contributions_html(html_text)
    assert records[0].count is None
    assert records[0].level == 2


def test_zero_contribution_day_parsed_as_zero_not_none() -> None:
    html_text = _wrap(
        '<td data-date="2024-01-01" data-level="0" aria-label="No contributions on January 1, 2024."></td>'
    )
    records = parse_contributions_html(html_text)
    assert records[0].count == 0
    assert records[0].level == 0


def test_invalid_level_rejected() -> None:
    html_text = _wrap('<td data-date="2024-01-01" data-level="9"></td>')
    with pytest.raises(ContributionDataError, match="out of range"):
        parse_contributions_html(html_text)


def test_validate_records_rejects_implausibly_few_days() -> None:
    records = [DayRecord(date="2024-01-01", level=1, count=1)]
    with pytest.raises(ContributionDataError, match="implausibly few"):
        validate_records(records)


def test_is_valid_document_requires_min_days() -> None:
    assert not is_valid_document({"days": [{"date": "2024-01-01"}]})
    assert is_valid_document({"days": [{"date": "2024-01-01"}] * 366})


def test_atomic_write_produces_parseable_json(tmp_path: Path) -> None:
    target = tmp_path / "contributions.json"
    document = {"days": [{"date": "2024-01-01", "level": 1, "count": 1}] * 300}
    _atomic_write_json(target, document)
    assert json.loads(target.read_text(encoding="utf-8"))["days"][0]["date"] == "2024-01-01"


def test_main_rejects_placeholder_username(tmp_path: Path) -> None:
    exit_code = _main(["--username", "<username>", "--output", str(tmp_path / "out.json")])
    assert exit_code == 1
    assert not (tmp_path / "out.json").exists()


def test_main_preserves_existing_file_on_fetch_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    output_path = tmp_path / "contributions.json"
    existing_document = {"days": [{"date": "2024-01-01", "level": 1, "count": 1}] * 366}
    output_path.write_text(json.dumps(existing_document), encoding="utf-8")

    def _boom(*_args, **_kwargs):
        raise ContributionDataError("simulated network failure")

    monkeypatch.setattr("tools.pull_contributions.fetch_contributions_html", _boom)

    exit_code = _main(["--username", "octocat", "--output", str(output_path)])

    assert exit_code == 1
    # The previously valid file must be untouched, never replaced with empty data.
    assert json.loads(output_path.read_text(encoding="utf-8")) == existing_document


def test_main_writes_new_document_on_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    output_path = tmp_path / "contributions.json"
    html_text = (FIXTURES / "contributions-sample.html").read_text(encoding="utf-8")

    monkeypatch.setattr("tools.pull_contributions.fetch_contributions_html", lambda *a, **k: html_text)

    exit_code = _main(["--username", "octocat", "--output", str(output_path)])

    assert exit_code == 0
    written = json.loads(output_path.read_text(encoding="utf-8"))
    assert written["username"] == "octocat"
    assert len(written["days"]) == 366
