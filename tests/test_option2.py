"""Focused tests for the isolated Option 2 profile implementation."""

from __future__ import annotations

import hashlib
from pathlib import Path

from options.option_2.scripts.render_assets import _filtered_languages
from options.option_2.scripts.validate_profile import REPO_ROOT, validate_option_2


def test_real_option_2_candidate_is_valid() -> None:
    assert validate_option_2() == []


def test_option_1_is_preserved_semantically() -> None:
    backup = (REPO_ROOT / "README.option-1.md").read_text(encoding="utf-8")
    normalized = backup.replace("\r\n", "\n").rstrip("\n").encode()
    assert hashlib.sha256(normalized).hexdigest() == (
        "f1b17a8ddd1de94c7e7893c5889b34ab51095626a640587aaceac59afc37cfaa"
    )


def test_language_exclusions_are_case_insensitive() -> None:
    document = {"language_bytes": {"Python": 100, "Shell": 50, "Makefile": 20}}
    assert _filtered_languages(document, {"shell", "makefile"}) == [("Python", 100)]


def test_validator_rejects_remote_images(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text(
        'Sushant Nemade Enterprise GenAI Option 1 remains preserved '
        '<img src="https://example.com/x.svg" alt="x">',
        encoding="utf-8",
    )
    problems = validate_option_2(readme_path=readme)
    assert any("remote image" in problem for problem in problems)


def test_portrait_assets_fit_mobile_budget() -> None:
    for theme in ("dark", "light"):
        path = REPO_ROOT / "options" / "option_2" / "assets" / f"portrait-{theme}.svg"
        assert path.stat().st_size < 500_000