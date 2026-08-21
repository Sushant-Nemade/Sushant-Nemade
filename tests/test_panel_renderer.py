"""Tests for tools.render_panel: assets/sysinfo.svg generation."""

from __future__ import annotations

import json
from pathlib import Path

from tools.config import load_profile, load_theme
from tools.render_panel import build_rows, render_panel_svg
from tools.validate_svg import validate_svg_bytes

REPO_ROOT = Path(__file__).resolve().parent.parent
REAL_PROFILE = REPO_ROOT / "config" / "profile.json"
REAL_THEME = REPO_ROOT / "config" / "theme.json"
RENDER_PANEL_SOURCE = (REPO_ROOT / "tools" / "render_panel.py").read_text(encoding="utf-8")


def _profile_and_theme():
    return load_profile(REAL_PROFILE), load_theme(REAL_THEME)


def test_content_is_configuration_driven() -> None:
    profile, _ = _profile_and_theme()
    rows = build_rows(profile)
    flat = {key: value for row in rows if row for key, value in [row]}
    assert flat["user"] == profile.identity.github_username
    assert flat["role"] == profile.identity.role
    assert flat["status"] == profile.status


def test_render_panel_has_no_hardcoded_username() -> None:
    # The example username from the requirements ("sushant-nemade") must come
    # only from configuration, never be literally embedded in rendering code.
    assert "sushant-nemade" not in RENDER_PANEL_SOURCE.lower()


def test_rendered_svg_uses_configured_username(tmp_path: Path) -> None:
    profile, theme = _profile_and_theme()
    svg = render_panel_svg(profile, theme, static=True)
    assert profile.identity.github_username in svg


def test_xml_escaping_of_special_characters(tmp_path: Path) -> None:
    profile, theme = _profile_and_theme()
    data = json.loads(REAL_PROFILE.read_text(encoding="utf-8"))
    data["identity"]["role"] = 'R&D <Lead> "Engineer"'
    tmp_profile = tmp_path / "profile.json"
    tmp_profile.write_text(json.dumps(data), encoding="utf-8")
    from tools.config import ConfigError

    try:
        load_profile(tmp_profile)
    except ConfigError:
        # The placeholder-marker safety check correctly rejects '<'/'>' in
        # config content; verify escaping directly against the renderer
        # instead using a value that only needs ampersand escaping.
        data["identity"]["role"] = "R&D Engineering"
        tmp_profile.write_text(json.dumps(data), encoding="utf-8")
        profile = load_profile(tmp_profile)
        svg = render_panel_svg(profile, theme, static=True)
        assert "R&amp;D Engineering" in svg
        assert "R&D Engineering" not in svg
        return
    raise AssertionError("expected ConfigError for unescaped angle brackets")


def test_svg_is_valid_and_accessible() -> None:
    profile, theme = _profile_and_theme()
    svg = render_panel_svg(profile, theme, static=False)
    validate_svg_bytes(svg.encode("utf-8"), source="sysinfo.svg")
    assert 'viewBox="0 0' in svg


def test_static_mode_has_no_animation_classes() -> None:
    profile, theme = _profile_and_theme()
    svg = render_panel_svg(profile, theme, static=True)
    assert "lt-reveal" not in svg
    assert "@keyframes" not in svg


def test_animated_mode_supports_reduced_motion() -> None:
    profile, theme = _profile_and_theme()
    svg = render_panel_svg(profile, theme, static=False)
    assert "prefers-reduced-motion" in svg
    assert "lt-reveal" in svg


def test_deterministic_rendering() -> None:
    profile, theme = _profile_and_theme()
    first = render_panel_svg(profile, theme, static=False)
    second = render_panel_svg(profile, theme, static=False)
    assert first == second


def test_no_remote_resources() -> None:
    profile, theme = _profile_and_theme()
    svg = render_panel_svg(profile, theme, static=False)
    # The only permitted occurrence of "http://" is the SVG namespace URI itself.
    assert svg.count("http://") == 1
    assert "xmlns=\"http://www.w3.org/2000/svg\"" in svg
    assert "https://" not in svg
