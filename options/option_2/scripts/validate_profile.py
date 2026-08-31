"""Validate the isolated Option 2 candidate and generated assets."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from tools.config import DEFAULT_PROFILE_PATH, load_profile
from tools.validate_svg import validate_svg_bytes

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_README = REPO_ROOT / "README.option-2.md"
DEFAULT_OPTION_ROOT = REPO_ROOT / "options" / "option_2"

ASSET_BASES = (
    "portrait",
    "banner",
    "toolbox",
    "capability-radar",
    "language-signal",
    "activity",
    "stats",
    "project-01",
    "project-02",
    "project-03",
    "project-04",
)
HTML_IMAGE_PATTERN = re.compile(r"<img\s+[^>]*src=\"([^\"]+)\"[^>]*>", re.IGNORECASE)
HTML_SOURCE_PATTERN = re.compile(r"<source\s+[^>]*srcset=\"([^\"]+)\"[^>]*>", re.IGNORECASE)
ALT_PATTERN = re.compile(r"\balt=\"[^\"]+\"", re.IGNORECASE)
SECRET_PATTERN = re.compile(r"(?:ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})")
PLACEHOLDERS = ("YOUR_", "PROJECT_ONE", "TODO:", "FIXME", "lorem ipsum")


def validate_option_2(
    *, readme_path: Path = DEFAULT_README, option_root: Path = DEFAULT_OPTION_ROOT
) -> list[str]:
    problems: list[str] = []
    if not readme_path.is_file():
        return [f"candidate README not found: {readme_path}"]
    text = readme_path.read_text(encoding="utf-8")
    lowered = text.lower()

    for marker in PLACEHOLDERS:
        if marker.lower() in lowered:
            problems.append(f"unresolved placeholder marker: {marker}")
    if SECRET_PATTERN.search(text):
        problems.append("secret-like token found in candidate README")
    for required in ("Sushant Nemade", "Enterprise GenAI", "Option 1 remains preserved"):
        if required not in text:
            problems.append(f"required candidate content missing: {required}")

    for image_match in HTML_IMAGE_PATTERN.finditer(text):
        tag = image_match.group(0)
        target = image_match.group(1)
        if not ALT_PATTERN.search(tag):
            problems.append(f"HTML image is missing alt text: {target}")
        if target.startswith(("http://", "https://")):
            problems.append(f"remote image is not permitted: {target}")
        elif not (REPO_ROOT / target).is_file():
            problems.append(f"referenced image does not exist: {target}")
    for target in HTML_SOURCE_PATTERN.findall(text):
        if target.startswith(("http://", "https://")):
            problems.append(f"remote picture source is not permitted: {target}")
        elif not (REPO_ROOT / target).is_file():
            problems.append(f"referenced picture source does not exist: {target}")

    config_path = option_root / "config.json"
    repositories_path = option_root / "public-repos.json"
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
        repositories = json.loads(repositories_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        problems.append(f"Option 2 JSON could not be loaded: {exc}")
        return problems
    max_asset_bytes = int(config.get("max_asset_bytes", 500_000))
    if repositories.get("username") != load_profile(DEFAULT_PROFILE_PATH).identity.github_username:
        problems.append("public repository data belongs to a different username")

    assets_dir = option_root / "assets"
    for base in ASSET_BASES:
        for theme in ("dark", "light"):
            path = assets_dir / f"{base}-{theme}.svg"
            if not path.is_file():
                problems.append(f"missing generated asset: {path.relative_to(REPO_ROOT)}")
                continue
            if path.stat().st_size > max_asset_bytes:
                problems.append(
                    f"asset exceeds {max_asset_bytes} byte budget: {path.relative_to(REPO_ROOT)}"
                )
            try:
                validate_svg_bytes(path.read_bytes(), source=str(path))
            except ValueError as exc:
                problems.append(str(exc))
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate Option 2 profile candidate")
    parser.add_argument("--readme", type=Path, default=DEFAULT_README)
    parser.add_argument("--option-root", type=Path, default=DEFAULT_OPTION_ROOT)
    args = parser.parse_args(argv)
    problems = validate_option_2(readme_path=args.readme, option_root=args.option_root)
    if problems:
        for problem in problems:
            print(f"FAIL: {problem}")
        return 1
    print(f"OK: {args.readme} and {len(ASSET_BASES) * 2} generated assets")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
