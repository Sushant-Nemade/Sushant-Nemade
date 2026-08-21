"""Tests for tools.config: configuration loading and validation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.config import ConfigError, load_profile, load_theme

REPO_ROOT = Path(__file__).resolve().parent.parent
REAL_PROFILE = REPO_ROOT / "config" / "profile.json"
REAL_THEME = REPO_ROOT / "config" / "theme.json"


def _write_json(path: Path, data: dict) -> Path:
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _minimal_profile() -> dict:
    return {
        "identity": {
            "name": "Test Person",
            "github_username": "test-person",
            "role": "Data & AI Engineer",
            "location": "Erlangen, Germany",
            "education": "M.Sc. ICT @ FAU",
            "headline": "Headline",
            "value_proposition": "Value proposition text.",
        },
        "focus": ["GenAI"],
        "approach": ["Discover"],
        "principles": ["Responsible AI"],
        "languages_spoken": "English C1",
        "status": "Open to opportunities",
        "capability_groups": [{"key": "ai_ml", "label": "ai_ml", "items": ["PyTorch"]}],
        "contact": {"linkedin": "https://linkedin.com/in/x", "github": "https://github.com/x", "email": None},
        "experience": [{"organisation": "Acme", "summary": "Did things"}],
        "education_entries": [{"institution": "FAU", "degree": "M.Sc."}],
        "projects": [
            {
                "name": "Project One",
                "description": "A sanitized description.",
                "technologies": ["Python"],
                "repository_url": None,
                "display_state": "case_study_in_preparation",
            }
        ],
    }


def _minimal_theme() -> dict:
    return {
        "palette": {
            "background": "#0D1117",
            "panel_background": "#111827",
            "text_primary": "#E6EDF3",
            "text_muted": "#8B949E",
            "accent_primary": "#38BDF8",
            "accent_secondary": "#60A5FA",
            "accent_positive": "#2DD4BF",
            "border": "#30363D",
        },
        "font_stack": "ui-monospace, monospace",
        "animation": {"total_duration_seconds": 4.0},
    }


def test_real_profile_and_theme_are_valid() -> None:
    profile = load_profile(REAL_PROFILE)
    theme = load_theme(REAL_THEME)
    assert profile.identity.github_username == "Sushant-Nemade"
    assert 1 <= len(profile.projects) <= 4
    assert theme.palette["accent_primary"] == "#38BDF8"


def test_missing_profile_file_raises(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="not found"):
        load_profile(tmp_path / "missing.json")


def test_missing_username_raises(tmp_path: Path) -> None:
    data = _minimal_profile()
    del data["identity"]["github_username"]
    path = _write_json(tmp_path / "profile.json", data)
    with pytest.raises(ConfigError, match="github_username"):
        load_profile(path)


def test_malformed_json_raises(tmp_path: Path) -> None:
    path = tmp_path / "profile.json"
    path.write_text("{not valid json", encoding="utf-8")
    with pytest.raises(ConfigError, match="invalid JSON"):
        load_profile(path)


def test_phone_field_rejected(tmp_path: Path) -> None:
    data = _minimal_profile()
    data["phone"] = "+49 123 456789"
    path = _write_json(tmp_path / "profile.json", data)
    with pytest.raises(ConfigError, match="phone"):
        load_profile(path)


def test_work_authorisation_field_rejected(tmp_path: Path) -> None:
    data = _minimal_profile()
    data["work_authorisation"] = "EU citizen"
    path = _write_json(tmp_path / "profile.json", data)
    with pytest.raises(ConfigError, match="work-authorisation"):
        load_profile(path)


def test_unverified_metric_rejected(tmp_path: Path) -> None:
    data = _minimal_profile()
    data["projects"][0]["description"] = "Achieved a 30 percent effort reduction."
    path = _write_json(tmp_path / "profile.json", data)
    with pytest.raises(ConfigError, match="forbidden unverified metric"):
        load_profile(path)


def test_banned_job_title_rejected(tmp_path: Path) -> None:
    data = _minimal_profile()
    data["identity"]["role"] = "Senior Data Scientist"
    path = _write_json(tmp_path / "profile.json", data)
    with pytest.raises(ConfigError, match="forbidden job title"):
        load_profile(path)


def test_unresolved_placeholder_rejected(tmp_path: Path) -> None:
    data = _minimal_profile()
    data["identity"]["github_username"] = "<username>"
    path = _write_json(tmp_path / "profile.json", data)
    with pytest.raises(ConfigError):
        load_profile(path)


def test_phone_like_string_rejected(tmp_path: Path) -> None:
    data = _minimal_profile()
    data["identity"]["value_proposition"] = "Call me at 0912-3456789 for details."
    path = _write_json(tmp_path / "profile.json", data)
    with pytest.raises(ConfigError, match="phone-number-like"):
        load_profile(path)


def test_active_project_requires_repository_url(tmp_path: Path) -> None:
    data = _minimal_profile()
    data["projects"][0]["display_state"] = "active"
    data["projects"][0]["repository_url"] = None
    path = _write_json(tmp_path / "profile.json", data)
    with pytest.raises(ConfigError, match="repository_url"):
        load_profile(path)


def test_case_study_project_must_not_set_repository_url(tmp_path: Path) -> None:
    data = _minimal_profile()
    data["projects"][0]["repository_url"] = "https://github.com/example/repo"
    path = _write_json(tmp_path / "profile.json", data)
    with pytest.raises(ConfigError, match="must not set repository_url"):
        load_profile(path)


def test_theme_missing_palette_key_raises(tmp_path: Path) -> None:
    data = _minimal_theme()
    del data["palette"]["border"]
    path = _write_json(tmp_path / "theme.json", data)
    with pytest.raises(ConfigError, match="border"):
        load_theme(path)


def test_theme_remote_font_rejected(tmp_path: Path) -> None:
    data = _minimal_theme()
    data["font_stack"] = "url(https://fonts.example.com/font.woff2)"
    path = _write_json(tmp_path / "theme.json", data)
    with pytest.raises(ConfigError, match="remote resources"):
        load_theme(path)
