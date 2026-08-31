"""Render all self-hosted SVG assets for the Applied AI Dossier profile."""

from __future__ import annotations

import argparse
import json
import math
import os
import tempfile
import textwrap
from datetime import date, timedelta
from pathlib import Path
from typing import TYPE_CHECKING
from xml.sax.saxutils import escape

from tools.config import DEFAULT_PROFILE_PATH, CapabilityGroup, ProfileConfig, load_profile

if TYPE_CHECKING:
    from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[3]
OPTION_ROOT = REPO_ROOT / "options" / "option_2"
DEFAULT_CONFIG = OPTION_ROOT / "config.json"
DEFAULT_REPOSITORIES = OPTION_ROOT / "public-repos.json"
DEFAULT_CONTRIBUTIONS = REPO_ROOT / "assets" / "contributions.json"
DEFAULT_PORTRAIT = REPO_ROOT / "build" / "photo-ready.png"
DEFAULT_OUTPUT = OPTION_ROOT / "assets"

DARK = {
    "background": "#101418",
    "panel": "#171C21",
    "text": "#F4F4F5",
    "muted": "#A1A1AA",
    "border": "#343A40",
    "accent": "#FB7185",
}
LIGHT = {
    "background": "#F7F8FA",
    "panel": "#FFFFFF",
    "text": "#18181B",
    "muted": "#52525B",
    "border": "#D4D4D8",
    "accent": "#BE123C",
}
FONT = "Segoe UI,Helvetica,Arial,sans-serif"
MONO = "Consolas,Liberation Mono,monospace"


def _load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        document = json.load(handle)
    if not isinstance(document, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return document


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent, prefix=".tmp-option2-", suffix=".svg"
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        os.replace(temporary_name, path)
    finally:
        if os.path.exists(temporary_name):
            os.remove(temporary_name)


def _svg(width: int, height: int, title: str, description: str, body: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" role="img" width="100%" '
        f'viewBox="0 0 {width} {height}" preserveAspectRatio="xMidYMid meet">'
        f"<title>{escape(title)}</title><desc>{escape(description)}</desc>{body}</svg>"
    )


def _panel(width: int, height: int, palette: dict[str, str], *, radius: int = 8) -> str:
    return (
        f'<rect width="{width}" height="{height}" rx="{radius}" '
        f'fill="{palette["panel"]}" stroke="{palette["border"]}"/>'
    )


def _text(
    x: float,
    y: float,
    value: str,
    *,
    size: int,
    fill: str,
    weight: int = 400,
    family: str = FONT,
    anchor: str = "start",
    extra: str = "",
) -> str:
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" font-family="{family}" font-size="{size}" '
        f'font-weight="{weight}" fill="{fill}" text-anchor="{anchor}"{extra}>'
        f"{escape(value)}</text>"
    )


def _blend(base: str, accent: str, ratio: float) -> str:
    base_rgb = tuple(int(base[index : index + 2], 16) for index in (1, 3, 5))
    accent_rgb = tuple(int(accent[index : index + 2], 16) for index in (1, 3, 5))
    channels = [round(a + (b - a) * ratio) for a, b in zip(base_rgb, accent_rgb)]
    return "#" + "".join(f"{channel:02X}" for channel in channels)


def _render_banner(profile: ProfileConfig, config: dict, palette: dict[str, str]) -> str:
    width, height = 900, 205
    lines = config["banner_lines"]
    style = (
        "<style>"
        ".line{opacity:1;animation:arrive .5s ease-out both}"
        ".l2{animation-delay:.35s}.l3{animation-delay:.7s}"
        "@keyframes arrive{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}"
        "@media(prefers-reduced-motion:reduce){.line{animation:none}}"
        "</style>"
    )
    body = [_panel(width, height, palette), style]
    body.append(f'<rect x="0" y="0" width="8" height="{height}" fill="{palette["accent"]}"/>')
    body.append(_text(34, 38, "APPLIED AI DOSSIER / 02", size=12, fill=palette["accent"], weight=700, family=MONO))
    body.append(_text(34, 88, lines[0], size=34, fill=palette["text"], weight=700, extra=' class="line"'))
    body.append(_text(34, 127, lines[1], size=20, fill=palette["text"], weight=600, extra=' class="line l2"'))
    body.append(_text(34, 166, lines[2], size=16, fill=palette["muted"], extra=' class="line l3"'))
    body.append(_text(866, 38, profile.identity.location.upper(), size=11, fill=palette["muted"], family=MONO, anchor="end"))
    return _svg(width, height, f"Professional introduction for {profile.identity.name}", profile.identity.value_proposition, "".join(body))


def _render_portrait(image: "Image.Image", columns: int, palette: dict[str, str]) -> str:
    grayscale = image.convert("L")
    rows = max(1, round(columns * grayscale.height / grayscale.width * 0.72))
    sampled = grayscale.resize((columns, rows))
    cell = 5
    padding = 15
    width = columns * cell + padding * 2
    height = rows * cell + padding * 2
    body = [_panel(width, height, palette)]
    for row in range(rows):
        for column in range(columns):
            darkness = (255 - sampled.getpixel((column, row))) / 255
            if darkness < 0.08:
                continue
            radius = 0.45 + darkness * 1.75
            opacity = 0.35 + darkness * 0.65
            body.append(
                f'<circle cx="{padding + column * cell + cell / 2:.1f}" '
                f'cy="{padding + row * cell + cell / 2:.1f}" r="{radius:.2f}" '
                f'fill="{palette["accent"]}" fill-opacity="{opacity:.2f}"/>'
            )
    return _svg(
        width,
        height,
        "Dot-matrix portrait of Sushant Nemade",
        "A locally generated dot-matrix portrait made from a private source image; the source photograph is not embedded.",
        "".join(body),
    )


def _render_toolbox(profile: ProfileConfig, palette: dict[str, str]) -> str:
    width, height = 900, 180
    body = [_panel(width, height, palette)]
    body.append(_text(24, 34, "WORKING TOOLBOX", size=12, fill=palette["accent"], weight=700, family=MONO))
    positions = [(24, 70), (314, 70), (604, 70), (24, 125), (314, 125), (604, 125)]
    for (x, y), group in zip(positions, profile.capability_groups):
        body.append(_text(x, y, group.label.upper(), size=11, fill=palette["muted"], weight=700, family=MONO))
        body.append(_text(x, y + 24, " / ".join(group.items), size=14, fill=palette["text"], weight=600))
    return _svg(width, height, "Focused technology toolbox", "Capabilities listed in the verified profile configuration.", "".join(body))


def _radar_points(groups: tuple[CapabilityGroup, ...], center_x: float, center_y: float, radius: float) -> tuple[list[tuple[float, float]], list[tuple[float, float]]]:
    maximum = max(len(group.items) for group in groups)
    outer: list[tuple[float, float]] = []
    values: list[tuple[float, float]] = []
    for index, group in enumerate(groups):
        angle = -math.pi / 2 + index * 2 * math.pi / len(groups)
        outer.append((center_x + radius * math.cos(angle), center_y + radius * math.sin(angle)))
        value_radius = radius * len(group.items) / maximum
        values.append((center_x + value_radius * math.cos(angle), center_y + value_radius * math.sin(angle)))
    return outer, values


def _points(points: list[tuple[float, float]]) -> str:
    return " ".join(f"{x:.1f},{y:.1f}" for x, y in points)


def _render_capability_radar(profile: ProfileConfig, palette: dict[str, str]) -> str:
    width, height = 520, 430
    center_x, center_y, radius = 260.0, 220.0, 125.0
    groups = profile.capability_groups
    outer, values = _radar_points(groups, center_x, center_y, radius)
    body = [_panel(width, height, palette)]
    body.append(_text(22, 32, "PROFILE EMPHASIS", size=12, fill=palette["accent"], weight=700, family=MONO))
    for ring in (0.33, 0.66, 1.0):
        ring_points = [
            (center_x + (x - center_x) * ring, center_y + (y - center_y) * ring)
            for x, y in outer
        ]
        body.append(f'<polygon points="{_points(ring_points)}" fill="none" stroke="{palette["border"]}"/>')
    for x, y in outer:
        body.append(f'<line x1="{center_x}" y1="{center_y}" x2="{x:.1f}" y2="{y:.1f}" stroke="{palette["border"]}"/>')
    body.append(f'<polygon points="{_points(values)}" fill="{palette["accent"]}" fill-opacity="0.22" stroke="{palette["accent"]}" stroke-width="2"/>')
    for index, (x, y) in enumerate(outer):
        label_radius = radius + 34
        angle = -math.pi / 2 + index * 2 * math.pi / len(groups)
        label_x = center_x + label_radius * math.cos(angle)
        label_y = center_y + label_radius * math.sin(angle) + 4
        body.append(_text(label_x, label_y, groups[index].label.upper(), size=10, fill=palette["text"], weight=700, family=MONO, anchor="middle"))
    body.append(_text(260, 407, "Relative breadth of listed capabilities - not a proficiency score", size=11, fill=palette["muted"], anchor="middle"))
    return _svg(width, height, "Profile emphasis radar", "Relative breadth calculated from configured capability entries, not self-rated proficiency.", "".join(body))


def _filtered_languages(repositories: dict, exclusions: set[str]) -> list[tuple[str, int]]:
    raw = repositories.get("language_bytes") or {}
    return sorted(
        ((str(name), int(value)) for name, value in raw.items() if name.lower() not in exclusions and int(value) > 0),
        key=lambda item: item[1],
        reverse=True,
    )


def _render_language_signal(repositories: dict, config: dict, palette: dict[str, str]) -> str:
    width, height = 520, 430
    exclusions = {item.lower() for item in config["public_repo_language_exclusions"]}
    languages = _filtered_languages(repositories, exclusions)
    total = sum(value for _, value in languages) or 1
    body = [_panel(width, height, palette)]
    body.append(_text(22, 32, "PUBLIC REPOSITORY SIGNAL", size=12, fill=palette["accent"], weight=700, family=MONO))
    body.append(_text(22, 72, f"{len(repositories.get('repositories') or [])} public repositories", size=28, fill=palette["text"], weight=700))
    body.append(_text(22, 99, "Observed language bytes from GitHub's public API", size=13, fill=palette["muted"]))
    y = 145
    for index, (name, byte_count) in enumerate(languages[:7]):
        ratio = byte_count / total
        bar_color = _blend(palette["border"], palette["accent"], max(0.3, 1 - index * 0.1))
        body.append(_text(22, y, name, size=13, fill=palette["text"], weight=600))
        body.append(_text(494, y, f"{ratio * 100:.1f}%", size=12, fill=palette["muted"], family=MONO, anchor="end"))
        body.append(f'<rect x="22" y="{y + 10}" width="472" height="13" rx="3" fill="{palette["border"]}"/>')
        body.append(f'<rect x="22" y="{y + 10}" width="{472 * ratio:.1f}" height="13" rx="3" fill="{bar_color}"/>')
        y += 50
    if not languages:
        body.append(_text(22, 160, "No public language bytes were returned.", size=15, fill=palette["muted"]))
    note = "A bar is used because one detected language cannot form a meaningful radar."
    body.append(_text(260, 407, note, size=11, fill=palette["muted"], anchor="middle"))
    return _svg(width, height, "Public repository language signal", note, "".join(body))


def _week_grid(days: list[dict]) -> tuple[list[list[dict | None]], date]:
    ordered = sorted(days, key=lambda item: item["date"])
    start = date.fromisoformat(ordered[0]["date"])
    grid_start = start - timedelta(days=start.isoweekday() % 7)
    end = date.fromisoformat(ordered[-1]["date"])
    week_count = ((end - grid_start).days + 7) // 7
    weeks: list[list[dict | None]] = [[None] * 7 for _ in range(week_count)]
    for item in ordered:
        current = date.fromisoformat(item["date"])
        week = (current - grid_start).days // 7
        row = current.isoweekday() % 7
        weeks[week][row] = item
    return weeks, grid_start


def _render_activity(contributions: dict, palette: dict[str, str]) -> str:
    width, height = 900, 250
    weeks, _ = _week_grid(contributions["days"])
    cell, gap = 11, 4
    left, top = 28, 70
    colors = {level: _blend(palette["border"], palette["accent"], level / 4) for level in range(5)}
    body = [_panel(width, height, palette)]
    body.append(_text(24, 34, "PUBLIC ACTIVITY / 12 MONTHS", size=12, fill=palette["accent"], weight=700, family=MONO))
    active_points: list[tuple[float, float]] = []
    for week_index, week in enumerate(weeks):
        for row_index, item in enumerate(week):
            x = left + week_index * (cell + gap)
            y = top + row_index * (cell + gap)
            level = int(item["level"]) if item else 0
            body.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2" fill="{colors[level]}"/>')
            if item and level > 0:
                active_points.append((x + cell / 2, y + cell / 2))
    if len(active_points) > 1:
        path = "M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in active_points)
        body.append(f'<path d="{path}" fill="none" stroke="{palette["accent"]}" stroke-opacity="0.2" stroke-width="1"/>')
        body.append(
            f'<circle r="4" fill="{palette["accent"]}"><animateMotion dur="9s" '
            f'repeatCount="indefinite" path="{path}"/></circle>'
        )
    updated = str(contributions.get("retrieved_at") or "")[:10]
    body.append(_text(24, 217, f"Source: public GitHub contribution levels | refreshed {updated}", size=11, fill=palette["muted"], family=MONO))
    body.append(_text(876, 217, "signal trace follows active days", size=11, fill=palette["muted"], family=MONO, anchor="end"))
    return _svg(width, height, "Public GitHub contribution activity", "Theme-aware contribution calendar with a decorative signal tracing public active days.", "".join(body))


def _render_stats(contributions: dict, repositories: dict, palette: dict[str, str]) -> str:
    width, height = 900, 150
    days = contributions["days"]
    statistics = contributions.get("statistics") or {}
    active_days = sum(1 for item in days if int(item["level"]) > 0)
    languages = repositories.get("language_bytes") or {}
    leading_language = max(languages, key=languages.get) if languages else "No data"
    values = [
        (str(len(repositories.get("repositories") or [])), "public repositories"),
        (str(active_days), "active public days"),
        (str(statistics.get("current_streak_days", 0)), "current public streak"),
        (leading_language, "leading public language"),
    ]
    body = [_panel(width, height, palette)]
    for index, (value, label) in enumerate(values):
        x = 24 + index * 219
        if index:
            body.append(f'<line x1="{x - 14}" y1="24" x2="{x - 14}" y2="126" stroke="{palette["border"]}"/>')
        body.append(_text(x, 72, value, size=28 if len(value) < 12 else 20, fill=palette["text"], weight=700))
        body.append(_text(x, 103, label.upper(), size=10, fill=palette["muted"], weight=700, family=MONO))
    return _svg(width, height, "Public profile statistics", "Conservative statistics derived from public GitHub repository and contribution data.", "".join(body))


def _render_project_card(project, index: int, palette: dict[str, str]) -> str:
    width, height = 430, 235
    body = [_panel(width, height, palette)]
    body.append(_text(22, 32, f"CASE STUDY / {index:02d}", size=11, fill=palette["accent"], weight=700, family=MONO))
    title_lines = textwrap.wrap(project.name, width=38)[:2]
    y = 70
    for line in title_lines:
        body.append(_text(22, y, line, size=19, fill=palette["text"], weight=700))
        y += 24
    y += 10
    for line in textwrap.wrap(project.description, width=61)[:3]:
        body.append(_text(22, y, line, size=12, fill=palette["muted"]))
        y += 18
    technology_text = " / ".join(project.technologies[:4])
    body.append(_text(22, 207, technology_text, size=10, fill=palette["text"], weight=600, family=MONO))
    body.append(_text(408, 32, "IN PREPARATION", size=9, fill=palette["muted"], family=MONO, anchor="end"))
    return _svg(width, height, project.name, f"Case study in preparation. {project.description}", "".join(body))


def render_all(
    *,
    profile_path: Path,
    config_path: Path,
    repositories_path: Path,
    contributions_path: Path,
    portrait_path: Path | None,
    output_dir: Path,
) -> list[Path]:
    profile = load_profile(profile_path)
    config = _load_json(config_path)
    repositories = _load_json(repositories_path)
    contributions = _load_json(contributions_path)
    renderers = {
        "banner": lambda palette: _render_banner(profile, config, palette),
        "toolbox": lambda palette: _render_toolbox(profile, palette),
        "capability-radar": lambda palette: _render_capability_radar(profile, palette),
        "language-signal": lambda palette: _render_language_signal(repositories, config, palette),
        "activity": lambda palette: _render_activity(contributions, palette),
        "stats": lambda palette: _render_stats(contributions, repositories, palette),
    }
    if portrait_path is not None:
        from PIL import Image

        if not portrait_path.is_file():
            raise ValueError(f"portrait input not found: {portrait_path}")
        image = Image.open(portrait_path)
        renderers["portrait"] = lambda palette: _render_portrait(
            image, int(config["portrait_columns"]), palette
        )
    written: list[Path] = []
    for theme_name, palette in (("dark", DARK), ("light", LIGHT)):
        for asset_name, renderer in renderers.items():
            output_path = output_dir / f"{asset_name}-{theme_name}.svg"
            _write(output_path, renderer(palette))
            written.append(output_path)
        for index, project in enumerate(profile.projects[:4], start=1):
            output_path = output_dir / f"project-{index:02d}-{theme_name}.svg"
            _write(output_path, _render_project_card(project, index, palette))
            written.append(output_path)
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render Option 2 profile assets")
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE_PATH)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--repositories", type=Path, default=DEFAULT_REPOSITORIES)
    parser.add_argument("--contributions", type=Path, default=DEFAULT_CONTRIBUTIONS)
    parser.add_argument("--portrait", type=Path, default=DEFAULT_PORTRAIT)
    parser.add_argument(
        "--skip-portrait",
        action="store_true",
        help="Preserve checked-in portrait assets when the private source is unavailable",
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    try:
        written = render_all(
            profile_path=args.profile,
            config_path=args.config,
            repositories_path=args.repositories,
            contributions_path=args.contributions,
            portrait_path=None if args.skip_portrait else args.portrait,
            output_dir=args.output_dir,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Option 2 rendering failed: {exc}")
        return 1
    print(f"Wrote {len(written)} Option 2 SVG assets to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())