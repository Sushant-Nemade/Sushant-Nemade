"""Tests for tools.validate_readme."""

from __future__ import annotations

from pathlib import Path

from tools.validate_readme import DEFAULT_README_PATH, REPO_ROOT, validate_readme_text

REAL_README_TEXT = DEFAULT_README_PATH.read_text(encoding="utf-8")


def test_real_readme_has_no_problems() -> None:
    problems = validate_readme_text(REAL_README_TEXT, repo_root=REPO_ROOT)
    assert problems == []


def test_real_readme_references_existing_assets() -> None:
    assert (REPO_ROOT / "assets" / "sysinfo.svg").is_file()
    assert (REPO_ROOT / "assets" / "contribution-graph.svg").is_file()


def test_missing_local_asset_detected(tmp_path: Path) -> None:
    text = "# Test\n\n![Alt text](assets/does-not-exist.svg)\n"
    problems = validate_readme_text(text, repo_root=tmp_path)
    assert any("does not exist" in p for p in problems)


def test_missing_alt_text_detected(tmp_path: Path) -> None:
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "x.svg").write_text("<svg/>", encoding="utf-8")
    text = "# Test\n\n![](assets/x.svg)\n"
    problems = validate_readme_text(text, repo_root=tmp_path)
    assert any("alt text" in p for p in problems)


def test_remote_image_rejected(tmp_path: Path) -> None:
    text = "# Test\n\n![Alt](https://example.com/image.svg)\n"
    problems = validate_readme_text(text, repo_root=tmp_path)
    assert any("remote image" in p for p in problems)


def test_private_path_image_rejected(tmp_path: Path) -> None:
    text = "# Test\n\n![Alt](private/source-photo.jpg)\n"
    problems = validate_readme_text(text, repo_root=tmp_path)
    assert any("git-ignored path" in p for p in problems)


def test_case_study_link_rejected(tmp_path: Path) -> None:
    text = "# Test\n\n[Case study in preparation](https://fake-repo.example.com)\n"
    problems = validate_readme_text(text, repo_root=tmp_path)
    assert any("must not be a hyperlink" in p for p in problems)


def test_unverified_metric_detected(tmp_path: Path) -> None:
    text = "# Test\n\nAchieved a 30 percent effort reduction in the pipeline.\n"
    problems = validate_readme_text(text, repo_root=tmp_path)
    assert any("forbidden unverified metric" in p for p in problems)


def test_banned_job_title_detected(tmp_path: Path) -> None:
    text = "# Test\n\nWorking as Senior Data Scientist at a large company.\n"
    problems = validate_readme_text(text, repo_root=tmp_path)
    assert any("forbidden job title" in p for p in problems)


def test_phone_number_detected(tmp_path: Path) -> None:
    text = "# Test\n\nCall me at +49 176 12345678 anytime.\n"
    problems = validate_readme_text(text, repo_root=tmp_path)
    assert any("phone-number-like" in p for p in problems)


def test_unresolved_placeholder_detected(tmp_path: Path) -> None:
    text = "# Test\n\nGitHub: https://github.com/<username>\n"
    problems = validate_readme_text(text, repo_root=tmp_path)
    assert any("unresolved placeholder" in p for p in problems)


def test_required_professional_text_missing_detected(tmp_path: Path) -> None:
    text = "# Someone Else\n\nNot the right profile at all.\n"
    problems = validate_readme_text(text, repo_root=tmp_path)
    assert any("required professional text missing" in p for p in problems)
