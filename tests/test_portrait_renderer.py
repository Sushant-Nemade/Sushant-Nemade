"""Tests for the portrait pipeline (tools.clean_photo, tools.render_portrait).

Uses only a small, programmatically generated, non-personal synthetic image -
never a real photograph - per the requirement to avoid fabricating or
committing anyone's actual portrait.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from tools.clean_photo import PhotoCleaningError, clean_photo
from tools.config import load_theme
from tools.render_portrait import (
    PortraitRenderError,
    build_ascii_grid_from_image,
    render_portrait_svg,
)
from tools.validate_svg import validate_svg_bytes

REPO_ROOT = Path(__file__).resolve().parent.parent
REAL_THEME = REPO_ROOT / "config" / "theme.json"


def _synthetic_gradient_image(width: int = 40, height: int = 60) -> Image.Image:
    """A deterministic left-dark-to-right-light gradient; not a photograph of any person."""
    image = Image.new("L", (width, height))
    pixels = image.load()
    for y in range(height):
        for x in range(width):
            pixels[x, y] = int(255 * x / (width - 1))
    return image


def _all_white_image(width: int = 20, height: int = 20) -> Image.Image:
    return Image.new("L", (width, height), color=255)


def test_missing_source_photo_raises() -> None:
    with pytest.raises(PhotoCleaningError, match="not found"):
        clean_photo(Path("no/such/photo.jpg"), Path("/tmp/unused.png"))


def test_invalid_image_raises(tmp_path: Path) -> None:
    bogus = tmp_path / "not-an-image.jpg"
    bogus.write_bytes(b"this is not image data")
    with pytest.raises(PhotoCleaningError, match="not a readable image"):
        clean_photo(bogus, tmp_path / "out.png")


def test_clean_photo_writes_grayscale_output(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    _synthetic_gradient_image().save(source)
    output = tmp_path / "cleaned.png"
    clean_photo(source, output)
    assert output.is_file()
    with Image.open(output) as cleaned:
        assert cleaned.mode == "L"


def test_ascii_grid_respects_aspect_ratio() -> None:
    image = _synthetic_gradient_image(width=40, height=60)
    grid = build_ascii_grid_from_image(image, grid_width=40)
    # height/width = 1.5; CHAR_ASPECT_RATIO compensates so rows < 60.
    assert 25 <= len(grid) <= 40
    assert all(len(row) == 40 for row in grid)


def test_near_white_pixels_render_as_blank_space() -> None:
    grid = build_ascii_grid_from_image(_all_white_image(), grid_width=20)
    assert all(set(row) <= {" "} for row in grid)


def test_grid_width_too_small_rejected() -> None:
    with pytest.raises(PortraitRenderError, match="grid_width"):
        build_ascii_grid_from_image(_synthetic_gradient_image(), grid_width=2)


def test_deterministic_grid_and_svg() -> None:
    image = _synthetic_gradient_image()
    theme = load_theme(REAL_THEME)
    grid_a = build_ascii_grid_from_image(image, grid_width=30)
    grid_b = build_ascii_grid_from_image(image, grid_width=30)
    assert grid_a == grid_b
    svg_a = render_portrait_svg(grid_a, theme, static=False)
    svg_b = render_portrait_svg(grid_b, theme, static=False)
    assert svg_a == svg_b


def test_svg_is_valid_with_title_and_desc() -> None:
    grid = build_ascii_grid_from_image(_synthetic_gradient_image(), grid_width=30)
    theme = load_theme(REAL_THEME)
    svg = render_portrait_svg(grid, theme, static=False)
    validate_svg_bytes(svg.encode("utf-8"), source="portrait.svg")
    assert "<title>" in svg
    assert "<desc>" in svg


def test_no_raster_or_embedded_image_data() -> None:
    grid = build_ascii_grid_from_image(_synthetic_gradient_image(), grid_width=30)
    theme = load_theme(REAL_THEME)
    svg = render_portrait_svg(grid, theme, static=False)
    assert "<image" not in svg
    assert "base64" not in svg
    assert "data:image" not in svg


def test_static_mode_has_no_animation_classes() -> None:
    grid = build_ascii_grid_from_image(_synthetic_gradient_image(), grid_width=30)
    theme = load_theme(REAL_THEME)
    svg = render_portrait_svg(grid, theme, static=True)
    assert "lt-reveal" not in svg
    assert "@keyframes" not in svg


def test_animated_mode_supports_reduced_motion() -> None:
    grid = build_ascii_grid_from_image(_synthetic_gradient_image(), grid_width=30)
    theme = load_theme(REAL_THEME)
    svg = render_portrait_svg(grid, theme, static=False)
    assert "prefers-reduced-motion" in svg
    assert "lt-reveal" in svg


def test_xml_escaping_for_ramp_characters() -> None:
    # Each glyph is now its own element, so escaped entities appear
    # separately rather than as one contiguous run.
    grid = ["<>&\"'"]  # pathological row content, exercised directly
    theme = load_theme(REAL_THEME)
    svg = render_portrait_svg(grid, theme, static=True)
    validate_svg_bytes(svg.encode("utf-8"), source="portrait.svg")
    for entity in ("&lt;", "&gt;", "&amp;"):
        assert entity in svg


def test_no_remote_resources() -> None:
    grid = build_ascii_grid_from_image(_synthetic_gradient_image(), grid_width=30)
    theme = load_theme(REAL_THEME)
    svg = render_portrait_svg(grid, theme, static=False)
    assert svg.count("http://") == 1  # only the SVG namespace declaration
    assert "https://" not in svg


def test_glyphs_reveal_individually_in_increasing_order() -> None:
    import re

    grid = build_ascii_grid_from_image(_synthetic_gradient_image(), grid_width=30)
    theme = load_theme(REAL_THEME)
    svg = render_portrait_svg(grid, theme, static=False)
    delays = [float(m) for m in re.findall(r'animation-delay:([\d.]+)s', svg)]
    non_space_glyphs = sum(1 for row in grid for ch in row if ch != " ")
    assert len(delays) == non_space_glyphs
    assert delays == sorted(delays)
    assert len(set(delays)) > 1
