"""Render assets/portrait.svg: an ASCII-character portrait, never a raster embed.

Reads the locally processed, git-ignored ``build/photo-ready.png`` produced by
``tools.clean_photo`` and converts it into a monochrome character grid. The
original photograph is never embedded in or referenced by the output SVG.
Requires the optional 'art' dependencies (tools/requirements-art.txt); never
imported by the daily/CI workflow.

Usage (from the repository root):
    python -m tools.clean_photo --input private/source-photo.jpg
    python -m tools.render_portrait
    python -m tools.render_portrait --static
"""

from __future__ import annotations

import argparse
import os
import tempfile
from pathlib import Path

from PIL import Image

from tools.config import DEFAULT_THEME_PATH, ThemeConfig, load_theme
from tools.svg_common import escape_text, reduced_motion_style, wrap_svg

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT_PATH = REPO_ROOT / "build" / "photo-ready.png"
DEFAULT_OUTPUT_PATH = REPO_ROOT / "assets" / "portrait.svg"

DEFAULT_GRID_WIDTH = 62
GLYPH_RAMP = " .,:;+*xX#@"
NEAR_WHITE_THRESHOLD = 245
# Monospace glyph cells are taller than they are wide; compensate so the
# rendered portrait keeps the source image's proportions.
CHAR_ASPECT_RATIO = 0.55
FONT_SIZE = 8
LINE_HEIGHT = FONT_SIZE * 1.05
CHAR_WIDTH = FONT_SIZE * 0.6
PADDING = 16
# Each visible glyph reveals individually, in reading order, like it is
# being typed; the whole portrait finishes within DEFAULT_MAX_REVEAL_SECONDS
# regardless of how many glyphs the grid contains.
DEFAULT_MAX_REVEAL_SECONDS = 4.0
MIN_CHAR_STAGGER_SECONDS = 0.006


class PortraitRenderError(ValueError):
    """Raised when an ASCII grid or SVG cannot be produced."""


def build_ascii_grid_from_image(image: Image.Image, *, grid_width: int = DEFAULT_GRID_WIDTH) -> list[str]:
    """Convert an image into a monochrome ASCII character grid.

    Deterministic for identical input: no randomness, no timestamps.
    """
    if grid_width < 10:
        raise PortraitRenderError("grid_width must be at least 10 for a recognizable portrait")

    grayscale = image.convert("L")
    if grayscale.width == 0 or grayscale.height == 0:
        raise PortraitRenderError("image has zero width or height")

    aspect = grayscale.height / grayscale.width
    grid_height = max(1, round(grid_width * aspect * CHAR_ASPECT_RATIO))
    resized = grayscale.resize((grid_width, grid_height))
    pixels = resized.load()

    ramp_max_index = len(GLYPH_RAMP) - 1
    rows: list[str] = []
    for y in range(grid_height):
        chars: list[str] = []
        for x in range(grid_width):
            intensity = pixels[x, y]
            if intensity >= NEAR_WHITE_THRESHOLD:
                chars.append(" ")
                continue
            # Darker pixel -> larger ramp index -> denser glyph.
            ramp_index = round((255 - intensity) / 255 * ramp_max_index)
            chars.append(GLYPH_RAMP[ramp_index])
        rows.append("".join(chars))
    return rows


def render_portrait_svg(grid: list[str], theme: ThemeConfig, *, static: bool) -> str:
    """Render the ASCII grid as a single-accent-colour portrait.

    Each non-blank glyph is its own SVG element that reveals individually, in
    reading order (left to right, top to bottom), so the portrait appears to
    be "typed" in one glyph at a time before holding its final state.
    """
    if not grid:
        raise PortraitRenderError("cannot render an empty ASCII grid")

    grid_width = max(len(row) for row in grid)
    width = int(PADDING * 2 + grid_width * CHAR_WIDTH)
    height = int(PADDING * 2 + len(grid) * LINE_HEIGHT)
    palette = theme.palette

    glyph_count = sum(1 for row in grid for ch in row if ch != " ")
    stagger_seconds = max(
        MIN_CHAR_STAGGER_SECONDS,
        min(0.02, DEFAULT_MAX_REVEAL_SECONDS / max(1, glyph_count)),
    )

    body_parts: list[str] = [
        f'<rect x="0" y="0" width="{width}" height="{height}" rx="10" '
        f'fill="{palette["panel_background"]}" stroke="{palette["border"]}" stroke-width="1"/>'
    ]
    glyph_index = 0
    for row_index, row in enumerate(grid):
        y = PADDING + (row_index + 1) * LINE_HEIGHT
        for col_index, ch in enumerate(row):
            if ch == " ":
                continue
            x = PADDING + col_index * CHAR_WIDTH
            reveal_class = "lt-glyph" if static else "lt-glyph lt-reveal"
            reveal_style = (
                "" if static else f' style="animation-delay:{glyph_index * stagger_seconds:.3f}s"'
            )
            body_parts.append(
                f'<text x="{x:.1f}" y="{y:.1f}" class="{reveal_class}"{reveal_style}>'
                f"{escape_text(ch)}</text>"
            )
            glyph_index += 1

    glyph_style = (
        f".lt-glyph{{font-family:monospace;font-size:{FONT_SIZE}px;"
        f'fill:{palette["accent_primary"]};}}'
    )
    style = f"<style>{glyph_style}</style>" if static else reduced_motion_style(extra_css=glyph_style)
    title = "ASCII portrait"
    description = (
        "A monochrome ASCII-character portrait rendered from a locally processed "
        "photograph; each character reveals individually, in reading order, as if "
        "being typed, and then the completed image holds. The original photograph "
        "is not embedded in this file."
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
    parser = argparse.ArgumentParser(description="Render assets/portrait.svg")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--theme", type=Path, default=DEFAULT_THEME_PATH)
    parser.add_argument("--grid-width", type=int, default=DEFAULT_GRID_WIDTH)
    parser.add_argument("--static", action="store_true")
    args = parser.parse_args(argv)

    static = args.static or os.environ.get("PREVIEW") == "1"

    if not args.input.is_file():
        print(
            f"No processed photo found at {args.input}.\n"
            "Run 'python -m tools.clean_photo --input private/source-photo.jpg' first."
        )
        return 1

    try:
        image = Image.open(args.input)
        grid = build_ascii_grid_from_image(image, grid_width=args.grid_width)
        theme = load_theme(args.theme)
        svg = render_portrait_svg(grid, theme, static=static)
    except PortraitRenderError as exc:
        print(f"Failed to render portrait: {exc}")
        return 1

    _atomic_write(args.output, svg)
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
