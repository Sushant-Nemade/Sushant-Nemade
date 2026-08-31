"""Validate the Option 3 Systems Console candidate and assets."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from tools.validate_svg import validate_svg_bytes

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_README = REPO_ROOT / "README.option-3.md"
DEFAULT_OPTION_ROOT = REPO_ROOT / "options" / "option_3"
ASSETS = (
    "terminal-hero.svg",
    "terminal-hero-mobile.svg",
    "capability-deck.svg",
    "capability-deck-mobile.svg",
    "system-architecture.svg",
    "system-architecture-mobile.svg",
    "project-board.svg",
    "project-board-mobile.svg",
)
IMAGE_PATTERN = re.compile(r"<img\s+[^>]*src=\"([^\"]+)\"[^>]*>", re.IGNORECASE)
SOURCE_PATTERN = re.compile(r"<source\s+[^>]*srcset=\"([^\"]+)\"[^>]*>", re.IGNORECASE)
ALT_PATTERN = re.compile(r"\balt=\"[^\"]+\"", re.IGNORECASE)
SECRET_PATTERN = re.compile(r"(?:ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})")


def validate_option_3(
    *, readme_path: Path = DEFAULT_README, option_root: Path = DEFAULT_OPTION_ROOT
) -> list[str]:
    if not readme_path.is_file():
        return [f"candidate README not found: {readme_path}"]
    problems: list[str] = []
    text = readme_path.read_text(encoding="utf-8")
    lowered = text.lower()
    for required in ("Sushant Nemade", "Enterprise GenAI", "Delivery architecture"):
        if required not in text:
            problems.append(f"required candidate content missing: {required}")
    for forbidden in ("public activity", "contribution-graph.svg", "activity-dark.svg"):
        if forbidden in lowered:
            problems.append(f"removed activity content is still referenced: {forbidden}")
    if SECRET_PATTERN.search(text):
        problems.append("secret-like token found in candidate README")

    for match in IMAGE_PATTERN.finditer(text):
        tag = match.group(0)
        target = match.group(1)
        if not ALT_PATTERN.search(tag):
            problems.append(f"HTML image is missing alt text: {target}")
        if target.startswith(("http://", "https://")):
            problems.append(f"remote image is not permitted: {target}")
        elif not (REPO_ROOT / target).is_file():
            problems.append(f"referenced image does not exist: {target}")
    for target in SOURCE_PATTERN.findall(text):
        if target.startswith(("http://", "https://")):
            problems.append(f"remote picture source is not permitted: {target}")
        elif not (REPO_ROOT / target).is_file():
            problems.append(f"referenced picture source does not exist: {target}")

    try:
        config = json.loads((option_root / "config.json").read_text(encoding="utf-8"))
        max_bytes = int(config["max_asset_bytes"])
    except (OSError, KeyError, ValueError, json.JSONDecodeError) as exc:
        problems.append(f"Option 3 configuration could not be loaded: {exc}")
        return problems

    for name in ASSETS:
        path = option_root / "assets" / name
        if not path.is_file():
            problems.append(f"missing generated asset: {path.relative_to(REPO_ROOT)}")
            continue
        if path.stat().st_size > max_bytes:
            problems.append(f"asset exceeds {max_bytes} byte budget: {path.relative_to(REPO_ROOT)}")
        try:
            validate_svg_bytes(path.read_bytes(), source=str(path))
        except ValueError as exc:
            problems.append(str(exc))

    architecture_path = option_root / "assets" / "system-architecture.svg"
    if architecture_path.is_file():
        architecture = architecture_path.read_text(encoding="utf-8")
        if "<animateMotion" not in architecture:
            problems.append("system architecture is missing native SVG motion")
        if "prefers-reduced-motion" not in architecture or 'class="moving"' not in architecture:
            problems.append("system architecture is missing its reduced-motion fallback")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate Option 3 Systems Console")
    parser.add_argument("--readme", type=Path, default=DEFAULT_README)
    parser.add_argument("--option-root", type=Path, default=DEFAULT_OPTION_ROOT)
    args = parser.parse_args(argv)
    problems = validate_option_3(readme_path=args.readme, option_root=args.option_root)
    if problems:
        for problem in problems:
            print(f"FAIL: {problem}")
        return 1
    print(f"OK: {args.readme} and {len(ASSETS)} Systems Console assets")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
