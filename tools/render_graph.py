"""Render assets/contribution-graph.svg from assets/contributions.json.

Performs no network access - this module only reads the already-normalized
JSON produced by ``tools.pull_contributions`` and renders it.

Usage (from the repository root):
    python -m tools.render_graph
    python -m tools.render_graph --static
"""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import date, timedelta
from pathlib import Path

from tools.config import DEFAULT_THEME_PATH, ThemeConfig, load_theme
from tools.pull_contributions import DayRecord, ContributionDataError
from tools.svg_common import escape_text, reduced_motion_style, wrap_svg

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT_PATH = REPO_ROOT / "assets" / "contributions.json"
DEFAULT_OUTPUT_PATH = REPO_ROOT / "assets" / "contribution-graph.svg"

CELL_SIZE = 11
CELL_GAP = 3
CELL_RADIUS = 2
PADDING_X = 20
PADDING_TOP = 34
LEGEND_HEIGHT = 34
PADDING_BOTTOM = 16
WEEK_STAGGER_SECONDS = 0.05
WEEKDAY_ROW_LABELS = ("Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat")


class GraphRenderError(ValueError):
    """Raised when contribution data cannot be turned into a graph."""


def _blend_hex(color_a: str, color_b: str, ratio: float) -> str:
    """Linearly blend two '#RRGGBB' colours. ratio=0 -> color_a, ratio=1 -> color_b."""

    def _channels(color: str) -> tuple[int, int, int]:
        color = color.lstrip("#")
        return int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)

    a_r, a_g, a_b = _channels(color_a)
    b_r, b_g, b_b = _channels(color_b)
    r = round(a_r + (b_r - a_r) * ratio)
    g = round(a_g + (b_g - a_g) * ratio)
    b = round(a_b + (b_b - a_b) * ratio)
    return f"#{r:02X}{g:02X}{b:02X}"


def _level_colors(palette: dict[str, str]) -> dict[int, str]:
    return {
        0: palette["border"],
        1: _blend_hex(palette["border"], palette["accent_secondary"], 0.5),
        2: palette["accent_secondary"],
        3: palette["accent_primary"],
        4: palette["accent_positive"],
    }


def load_contribution_records(path: Path) -> tuple[list[DayRecord], dict]:
    """Load days + full document from assets/contributions.json."""
    if not path.is_file():
        raise GraphRenderError(f"{path}: contribution data file not found")
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise GraphRenderError(f"{path}: invalid JSON ({exc})") from exc

    days_raw = document.get("days")
    if not isinstance(days_raw, list) or not days_raw:
        raise GraphRenderError(f"{path}: 'days' must be a non-empty list")

    records: list[DayRecord] = []
    for entry in days_raw:
        try:
            records.append(
                DayRecord(date=entry["date"], level=int(entry["level"]), count=entry.get("count"))
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise GraphRenderError(f"{path}: malformed day entry {entry!r}") from exc
    records.sort(key=lambda r: r.date)

    # Defensive re-fill: even though tools.pull_contributions already fills
    # gaps, the graph renderer independently guards against a hand-edited or
    # externally produced JSON file that skips dates.
    by_date = {record.date: record for record in records}
    start = date.fromisoformat(records[0].date)
    end = date.fromisoformat(records[-1].date)
    filled: list[DayRecord] = []
    current = start
    while current <= end:
        iso = current.isoformat()
        filled.append(by_date.get(iso) or DayRecord(date=iso, level=0, count=None))
        current += timedelta(days=1)

    return filled, document


def _build_week_grid(records: list[DayRecord]) -> tuple[list[list[DayRecord | None]], date]:
    """Arrange records into week columns (Sun-Sat rows), handling leap years."""
    first_date = date.fromisoformat(records[0].date)
    # Align the first column to the Sunday on/before the first recorded date.
    grid_start = first_date - timedelta(days=(first_date.isoweekday() % 7))

    by_date = {record.date: record for record in records}
    last_date = date.fromisoformat(records[-1].date)
    total_days = (last_date - grid_start).days + 1
    week_count = (total_days + 6) // 7

    weeks: list[list[DayRecord | None]] = [[None] * 7 for _ in range(week_count)]
    cursor = grid_start
    for _ in range(total_days):
        week_index = (cursor - grid_start).days // 7
        row_index = cursor.isoweekday() % 7
        weeks[week_index][row_index] = by_date.get(cursor.isoformat())
        cursor += timedelta(days=1)

    return weeks, grid_start


def render_graph_svg(records: list[DayRecord], document: dict, theme: ThemeConfig, *, static: bool) -> str:
    if not records:
        raise GraphRenderError("cannot render a graph with zero contribution records")

    weeks, _grid_start = _build_week_grid(records)
    palette = theme.palette
    level_colors = _level_colors(palette)

    grid_width = len(weeks) * (CELL_SIZE + CELL_GAP)
    grid_height = 7 * (CELL_SIZE + CELL_GAP)
    width = PADDING_X * 2 + grid_width
    height = PADDING_TOP + grid_height + LEGEND_HEIGHT + PADDING_BOTTOM

    body_parts: list[str] = [
        f'<rect x="0" y="0" width="{width}" height="{height}" rx="10" '
        f'fill="{palette["panel_background"]}" stroke="{palette["border"]}" stroke-width="1"/>'
    ]

    for week_index, week in enumerate(weeks):
        x = PADDING_X + week_index * (CELL_SIZE + CELL_GAP)
        reveal_class = "" if static else ' class="lt-reveal"'
        reveal_style = (
            "" if static else f' style="animation-delay:{week_index * WEEK_STAGGER_SECONDS:.3f}s"'
        )
        cells: list[str] = []
        for row_index, record in enumerate(week):
            y = PADDING_TOP + row_index * (CELL_SIZE + CELL_GAP)
            level = record.level if record is not None else 0
            fill = level_colors[level]
            title_bit = f"{record.date}: level {level}" if record is not None else "no data"
            cells.append(
                f'<rect x="{x}" y="{y}" width="{CELL_SIZE}" height="{CELL_SIZE}" '
                f'rx="{CELL_RADIUS}" fill="{fill}"><title>{escape_text(title_bit)}</title></rect>'
            )
        body_parts.append(f"<g{reveal_class}{reveal_style}>{''.join(cells)}</g>")

    legend_y = PADDING_TOP + grid_height + 18
    legend_items = []
    legend_x = PADDING_X
    legend_items.append(
        f'<text x="{legend_x}" y="{legend_y}" font-size="11" fill="{palette["text_muted"]}" '
        f'font-family="monospace">Less</text>'
    )
    legend_x += 34
    for level in range(5):
        legend_items.append(
            f'<rect x="{legend_x}" y="{legend_y - 10}" width="{CELL_SIZE}" height="{CELL_SIZE}" '
            f'rx="{CELL_RADIUS}" fill="{level_colors[level]}"/>'
        )
        legend_x += CELL_SIZE + CELL_GAP
    legend_items.append(
        f'<text x="{legend_x + 4}" y="{legend_y}" font-size="11" fill="{palette["text_muted"]}" '
        f'font-family="monospace">More</text>'
    )
    retrieved_at = str(document.get("retrieved_at", ""))[:10]
    caption = f"Public GitHub contribution activity \u00b7 Updated {retrieved_at}" if retrieved_at else (
        "Public GitHub contribution activity"
    )
    legend_items.append(
        f'<text x="{PADDING_X}" y="{legend_y + 16}" font-size="11" '
        f'fill="{palette["text_muted"]}" font-family="monospace">{escape_text(caption)}</text>'
    )
    body_parts.append("".join(legend_items))

    style = "" if static else reduced_motion_style()
    username = document.get("username", "this account")
    title = f"Public GitHub contribution graph for {username}"
    description = (
        f"Self-hosted visualization of {username}'s public GitHub contribution "
        f"calendar across {len(weeks)} weeks."
    )
    return wrap_svg(
        width=width, height=height, title=title, description=description, style=style,
        body="".join(body_parts),
    )


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=".tmp-", suffix=".svg")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.remove(tmp_name)


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render assets/contribution-graph.svg")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--theme", type=Path, default=DEFAULT_THEME_PATH)
    parser.add_argument("--static", action="store_true")
    args = parser.parse_args(argv)

    static = args.static or os.environ.get("PREVIEW") == "1"

    try:
        records, document = load_contribution_records(args.input)
        theme = load_theme(args.theme)
        svg = render_graph_svg(records, document, theme, static=static)
    except (GraphRenderError, ContributionDataError) as exc:
        print(f"Failed to render contribution graph, leaving previous file untouched: {exc}")
        return 1

    _atomic_write(args.output, svg)
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
