"""Retrieve and normalize public GitHub contribution-calendar data.

Network retrieval (:func:`fetch_contributions_html`) is kept strictly separate
from HTML parsing (:func:`parse_contributions_html`) so the parser can be
fully unit-tested offline against saved fixtures. Nothing is ever written to
``assets/contributions.json`` unless the freshly parsed data passes
validation - a failed or implausible fetch always preserves the previous
valid file.

Usage (from the repository root):
    python -m tools.pull_contributions
    python -m tools.pull_contributions --username Sushant-Nemade
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
import time
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import httpx
from lxml import html as lxml_html

from tools.config import DEFAULT_PROFILE_PATH, is_plausible_github_username, load_profile

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_PATH = REPO_ROOT / "assets" / "contributions.json"

SCHEMA_VERSION = 1
MIN_PLAUSIBLE_DAYS = 300
DEFAULT_TIMEOUT_SECONDS = 10.0
DEFAULT_RETRIES = 3
USER_AGENT_TEMPLATE = (
    "living-terminal-profile-bot/1.0 "
    "(+https://github.com/{username}; public contribution-graph refresh)"
)


class ContributionDataError(ValueError):
    """Raised when contribution data cannot be retrieved, parsed, or validated."""


@dataclass(frozen=True)
class DayRecord:
    date: str  # ISO 8601, e.g. "2024-01-31"
    level: int  # GitHub's public relative-activity scale, 0-4
    count: int | None  # exact contribution count, when reliably exposed


_COUNT_PATTERN = re.compile(r"(No|\d+)\s+contributions?\s+on", re.IGNORECASE)


def _extract_count(cell) -> int | None:
    data_count = cell.get("data-count")
    if data_count is not None:
        try:
            return int(data_count)
        except ValueError:
            pass
    aria_label = cell.get("aria-label") or ""
    match = _COUNT_PATTERN.search(aria_label)
    if not match:
        return None
    token = match.group(1)
    return 0 if token.lower() == "no" else int(token)


def _fill_gaps(records: list[DayRecord]) -> list[DayRecord]:
    """Insert level=0/count=None placeholders for any missing dates in-range."""
    if not records:
        return records
    by_date = {record.date: record for record in records}
    current = date.fromisoformat(records[0].date)
    end = date.fromisoformat(records[-1].date)
    filled: list[DayRecord] = []
    while current <= end:
        iso = current.isoformat()
        filled.append(by_date.get(iso) or DayRecord(date=iso, level=0, count=None))
        current += timedelta(days=1)
    return filled


def parse_contributions_html(html_text: str) -> list[DayRecord]:
    """Parse a GitHub public contribution-calendar HTML fragment.

    Pure function: performs no network access. Raises
    :class:`ContributionDataError` if the structure is not recognized.
    """
    if not html_text or not html_text.strip():
        raise ContributionDataError("empty HTML response")
    try:
        tree = lxml_html.fromstring(html_text)
    except Exception as exc:  # noqa: BLE001 - lxml raises various parser errors
        raise ContributionDataError(f"could not parse HTML: {exc}") from exc

    cells = tree.xpath("//td[@data-date]")
    if not cells:
        raise ContributionDataError(
            "no recognizable contribution-calendar cells found "
            "(GitHub may have changed its public HTML structure)"
        )

    by_date: dict[str, DayRecord] = {}
    for cell in cells:
        raw_date = cell.get("data-date")
        try:
            parsed_date = date.fromisoformat(raw_date)
        except (TypeError, ValueError) as exc:
            raise ContributionDataError(f"invalid date encountered: {raw_date!r}") from exc

        level_raw = cell.get("data-level")
        try:
            level = int(level_raw)
        except (TypeError, ValueError) as exc:
            raise ContributionDataError(
                f"invalid or missing data-level for {raw_date}: {level_raw!r}"
            ) from exc
        if not 0 <= level <= 4:
            raise ContributionDataError(f"data-level out of range for {raw_date}: {level}")

        # Later occurrences of the same date (duplicate cells) overwrite earlier
        # ones; this both de-duplicates and keeps the parser resilient to
        # malformed markup that repeats a cell.
        by_date[parsed_date.isoformat()] = DayRecord(
            date=parsed_date.isoformat(), level=level, count=_extract_count(cell)
        )

    ordered = sorted(by_date.values(), key=lambda record: record.date)
    return _fill_gaps(ordered)


def validate_records(records: list[DayRecord]) -> None:
    """Raise :class:`ContributionDataError` if ``records`` is not plausible."""
    if len(records) < MIN_PLAUSIBLE_DAYS:
        raise ContributionDataError(
            f"implausibly few days parsed ({len(records)} < {MIN_PLAUSIBLE_DAYS} minimum)"
        )
    seen: set[str] = set()
    for record in records:
        if record.date in seen:
            raise ContributionDataError(f"duplicate date after normalization: {record.date}")
        seen.add(record.date)
        if not 0 <= record.level <= 4:
            raise ContributionDataError(f"level out of range for {record.date}: {record.level}")


_WEEKDAY_NAMES = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


def compute_statistics(records: list[DayRecord]) -> dict:
    """Compute only statistics that can be reliably derived from ``records``."""
    current_streak = 0
    for record in reversed(records):
        if record.level > 0:
            current_streak += 1
        else:
            break

    longest_streak = 0
    running = 0
    for record in records:
        if record.level > 0:
            running += 1
            longest_streak = max(longest_streak, running)
        else:
            running = 0

    known_counts = [record.count for record in records if record.count is not None]
    known_days = len(known_counts)
    known_total = sum(known_counts) if known_counts else 0

    weekday_totals = {name: 0 for name in _WEEKDAY_NAMES}
    for record in records:
        if record.count is None:
            continue
        weekday_name = _WEEKDAY_NAMES[date.fromisoformat(record.date).weekday()]
        weekday_totals[weekday_name] += record.count

    return {
        "current_streak_days": current_streak,
        "longest_streak_days": longest_streak,
        "known_contribution_days": known_days,
        "known_contribution_total": known_total,
        "total_is_complete": known_days == len(records),
        "weekday_totals_known": weekday_totals,
    }


def build_normalized_document(
    username: str,
    records: list[DayRecord],
    *,
    retrieved_at: str,
    source_description: str,
) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "username": username,
        "retrieved_at": retrieved_at,
        "source": source_description,
        "days": [asdict(record) for record in records],
        "statistics": compute_statistics(records),
        "assumptions": [
            "count is null for a day when GitHub's public markup did not expose an "
            "exact figure; it is never guessed or assumed to be zero.",
            "level (0-4) reflects GitHub's public relative-activity scale for that day.",
            "streaks are computed using level > 0 as the 'had public activity' indicator.",
            "known_contribution_total only sums days where an exact count was available; "
            "see total_is_complete to know whether it covers every day in range.",
        ],
    }


def fetch_contributions_html(
    username: str,
    *,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    retries: int = DEFAULT_RETRIES,
) -> str:
    """Fetch the public contribution-calendar HTML fragment for ``username``."""
    url = f"https://github.com/users/{username}/contributions"
    headers = {"User-Agent": USER_AGENT_TEMPLATE.format(username=username)}
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            with httpx.Client(timeout=timeout, headers=headers, follow_redirects=True) as client:
                response = client.get(url)
            response.raise_for_status()
            if not response.text.strip():
                raise ContributionDataError("empty response body")
            return response.text
        except (httpx.HTTPError, ContributionDataError) as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(min(2**attempt, 8))
    raise ContributionDataError(f"failed to fetch contributions after {retries} attempt(s): {last_error}")


def _atomic_write_json(path: Path, document: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=".tmp-", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(document, handle, indent=2)
            handle.write("\n")
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.remove(tmp_name)


def is_valid_document(document: dict) -> bool:
    """Structural check used as a final gate before ``document`` replaces a file."""
    days = document.get("days")
    return isinstance(days, list) and len(days) >= MIN_PLAUSIBLE_DAYS


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Refresh assets/contributions.json")
    parser.add_argument("--username", default=None)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE_PATH)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--retries", type=int, default=DEFAULT_RETRIES)
    args = parser.parse_args(argv)

    username = args.username
    if not username:
        try:
            username = load_profile(args.profile).identity.github_username
        except Exception as exc:  # noqa: BLE001 - CLI error boundary
            print(f"Could not determine username from configuration: {exc}", file=sys.stderr)
            return 1

    if not is_plausible_github_username(username):
        print(f"Refusing to fetch: {username!r} is not a plausible GitHub username", file=sys.stderr)
        return 1

    try:
        html_text = fetch_contributions_html(username, timeout=args.timeout, retries=args.retries)
        records = parse_contributions_html(html_text)
        validate_records(records)
    except ContributionDataError as exc:
        print(
            f"Contribution retrieval/parse failed; preserving existing {args.output}: {exc}",
            file=sys.stderr,
        )
        return 1

    document = build_normalized_document(
        username,
        records,
        retrieved_at=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        source_description=(
            f"https://github.com/users/{username}/contributions "
            "(public HTML, GitHub profile contribution calendar)"
        ),
    )

    if not is_valid_document(document):
        print(f"New data failed final validation; preserving existing {args.output}", file=sys.stderr)
        return 1

    _atomic_write_json(args.output, document)
    print(f"Wrote {args.output} with {len(records)} day(s) for {username}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
