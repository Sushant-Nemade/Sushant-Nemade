"""Render assets/sysinfo.svg from config/profile.json and config/theme.json.

Usage (from the repository root):
    python -m tools.render_panel
    python -m tools.render_panel --static
    PREVIEW=1 python -m tools.render_panel
"""

from __future__ import annotations

import argparse
import os
import tempfile
from pathlib import Path

from tools.config import (
    DEFAULT_PROFILE_PATH,
    DEFAULT_THEME_PATH,
    ProfileConfig,
    ThemeConfig,
    load_profile,
    load_theme,
)
from tools.svg_common import (
    escape_text,
    font_family_attr,
    reduced_motion_style,
    wrap_svg,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_PATH = REPO_ROOT / "assets" / "sysinfo.svg"

FONT_SIZE = 14
LINE_HEIGHT = 20
PADDING_X = 20
PADDING_TOP = 34
PADDING_BOTTOM = 20
CHAR_WIDTH = FONT_SIZE * 0.6
STAGGER_SECONDS = 0.045

Row = tuple[str, str] | None  # (key, value) or None for a blank separator row


def build_rows(profile: ProfileConfig) -> list[Row]:
    """Build the ordered key/value rows shown in the terminal panel."""
    rows: list[Row] = [
        ("user", profile.identity.github_username),
        ("role", profile.identity.role),
        ("location", profile.identity.location),
        ("education", profile.identity.education),
        ("focus", " \u00b7 ".join(profile.focus)),
        None,
    ]
    for group in profile.capability_groups:
        rows.append((group.label, " \u00b7 ".join(group.items)))
    rows.append(None)
    rows.append(("approach", " \u2192 ".join(profile.approach)))
    rows.append(("principles", " \u00b7 ".join(profile.principles)))
    rows.append(("spoken", profile.languages_spoken))
    rows.append(("status", profile.status))
    return rows


def _panel_dimensions(rows: list[Row]) -> tuple[int, int, int]:
    key_col_chars = max((len(key) for row in rows if row for key, _ in [row]), default=0)
    max_line_chars = max(
        (len(key) + 3 + len(value) for row in rows if row for key, value in [row]),
        default=0,
    )
    width = int(PADDING_X * 2 + max_line_chars * CHAR_WIDTH)
    height_units = sum(1 if row else 0.5 for row in rows)
    height = int(PADDING_TOP + height_units * LINE_HEIGHT + PADDING_BOTTOM)
    return width, height, key_col_chars


def render_panel_svg(profile: ProfileConfig, theme: ThemeConfig, *, static: bool) -> str:
    """Render the full sysinfo.svg document as a string."""
    rows = build_rows(profile)
    width, height, key_col_chars = _panel_dimensions(rows)
    value_x = PADDING_X + int((key_col_chars + 3) * CHAR_WIDTH)
    font_family = font_family_attr(theme)
    palette = theme.palette

    body_parts: list[str] = [
        f'<rect x="0" y="0" width="{width}" height="{height}" rx="10" '
        f'fill="{palette["panel_background"]}" stroke="{palette["border"]}" stroke-width="1"/>'
    ]

    y = PADDING_TOP
    row_index = 0
    for row in rows:
        if row is None:
            y += LINE_HEIGHT * 0.5
            continue
        key, value = row
        reveal_class = "" if static else ' class="lt-reveal"'
        reveal_style = (
            "" if static else f' style="animation-delay:{row_index * STAGGER_SECONDS:.3f}s"'
        )
        body_parts.append(
            f'<text x="{PADDING_X}" y="{y}" font-family="{font_family}" '
            f'font-size="{FONT_SIZE}"{reveal_class}{reveal_style}>'
            f'<tspan fill="{palette["accent_secondary"]}">{escape_text(key)}</tspan>'
            f'<tspan x="{value_x}" fill="{palette["text_primary"]}">{escape_text(value)}</tspan>'
            "</text>"
        )
        y += LINE_HEIGHT
        row_index += 1

    style = "" if static else reduced_motion_style()
    title = f"Terminal system information panel for {profile.identity.name}"
    description = (
        f"{profile.identity.role} based in {profile.identity.location}. "
        f"Focus: {', '.join(profile.focus)}."
    )
    return wrap_svg(
        width=width,
        height=height,
        title=title,
        description=description,
        style=style,
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
    parser = argparse.ArgumentParser(description="Render assets/sysinfo.svg")
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE_PATH)
    parser.add_argument("--theme", type=Path, default=DEFAULT_THEME_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--static", action="store_true", help="Render without animation classes")
    args = parser.parse_args(argv)

    static = args.static or os.environ.get("PREVIEW") == "1"

    try:
        profile = load_profile(args.profile)
        theme = load_theme(args.theme)
        svg = render_panel_svg(profile, theme, static=static)
        _atomic_write(args.output, svg)
    except Exception as exc:  # noqa: BLE001 - top-level CLI error boundary
        print(f"Failed to render panel: {exc}")
        return 1

    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
