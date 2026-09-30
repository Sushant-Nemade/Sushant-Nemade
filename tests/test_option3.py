"""Focused tests for the Option 3 Systems Console profile."""

from __future__ import annotations

from pathlib import Path

from options.option_3.scripts.validate_profile import REPO_ROOT, validate_option_3

PUBLIC_REPOSITORIES = (
    "ai-chief-of-staff",
    "voice-note-idea-catcher",
    "whatsapp-assistant",
    "ai-receptionist",
    "ai-trip-planner",
    "public-ship-log",
    "comment-idea-generator",
    "creator-collab-matchmaker",
    "link-in-bio",
    "money-dashboard",
    "subscription-auditor",
    "security-checker",
    "applied-ai-systems-portfolio",
    "forgeai-production-engine",
    "sushant-nemade.github.io",
    "Sushant-Nemade",
    "dsss_homework_2",
)
FEATURED_PROJECTS = (
    "Applied AI Systems Portfolio",
    "ForgeAI Production Engine",
    "Security Checker",
    "Subscription Auditor",
)


def test_real_option_3_candidate_is_valid() -> None:
    assert validate_option_3() == []


def test_candidate_catalogues_all_public_repositories() -> None:
    text = (REPO_ROOT / "README.option-3.md").read_text(encoding="utf-8")
    for repository in PUBLIC_REPOSITORIES:
        assert f"https://github.com/Sushant-Nemade/{repository}" in text


def test_candidate_has_professional_information_hierarchy() -> None:
    text = (REPO_ROOT / "README.option-3.md").read_text(encoding="utf-8")
    headings = (
        "## 01 / Mission",
        "## 02 / Delivery architecture",
        "## 03 / Featured engineering systems",
        "## 04 / Portfolio map",
        "## 05 / Research case studies",
        "## 06 / Operating context",
        "## 07 / Contact",
    )
    anchors = (
        "#01--mission",
        "#02--delivery-architecture",
        "#03--featured-engineering-systems",
        "#04--portfolio-map",
        "#05--research-case-studies",
        "#07--contact",
    )

    assert all(heading in text for heading in headings)
    assert all(anchor in text for anchor in anchors)
    assert "trycloudflare.com" not in text


def test_project_boards_show_public_flagships() -> None:
    assets = REPO_ROOT / "options" / "option_3" / "assets"
    for name in ("project-board.svg", "project-board-mobile.svg"):
        text = (assets / name).read_text(encoding="utf-8")
        assert all(project in text for project in FEATURED_PROJECTS)


def test_previous_options_remain_available() -> None:
    assert (REPO_ROOT / "README.option-1.md").is_file()
    assert (REPO_ROOT / "README.option-2.md").is_file()


def test_candidate_removes_public_activity_visuals() -> None:
    text = (REPO_ROOT / "README.option-3.md").read_text(encoding="utf-8").lower()
    assert "public activity" not in text
    assert "contribution-graph.svg" not in text
    assert "activity-dark.svg" not in text


def test_architecture_has_motion_and_reduced_motion_fallback() -> None:
    path = REPO_ROOT / "options" / "option_3" / "assets" / "system-architecture.svg"
    text = path.read_text(encoding="utf-8")
    assert "<animateMotion" in text
    assert "prefers-reduced-motion" in text
    assert 'class="moving"' in text


def test_validator_rejects_remote_images(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text(
        'Sushant Nemade Enterprise GenAI Delivery architecture '
        '<img src="https://example.com/a.svg" alt="remote">',
        encoding="utf-8",
    )
    problems = validate_option_3(readme_path=readme)
    assert any("remote image" in problem for problem in problems)


def test_all_assets_fit_mobile_budget() -> None:
    assets = REPO_ROOT / "options" / "option_3" / "assets"
    assert all(path.stat().st_size < 500_000 for path in assets.glob("*.svg"))


def test_terminal_heroes_use_animated_sn_signal_core() -> None:
    assets = REPO_ROOT / "options" / "option_3" / "assets"
    for name in ("terminal-hero.svg", "terminal-hero-mobile.svg"):
        text = (assets / name).read_text(encoding="utf-8")
        assert 'id="sn-signal-core"' in text
        assert text.count("<animateMotion") >= 3
        assert "prefers-reduced-motion" in text
        assert "github mark" not in text.lower()