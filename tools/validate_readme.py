"""Validate README.md against the Living Terminal content and safety rules.

Checks that:
  - every locally referenced image exists on disk and has meaningful alt text;
  - no image references a git-ignored private/build path (would render broken);
  - no remote image is used;
  - "Case study in preparation" is never rendered as a clickable hyperlink;
  - no unverified metric, banned job title, phone-like content, or unresolved
    placeholder is present;
  - required professional identity text is present.

Usage (from the repository root):
    python -m tools.validate_readme
    python -m tools.validate_readme --readme README.md
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from tools.config import FORBIDDEN_METRIC_TERMS, FORBIDDEN_TITLES, PHONE_LIKE_PATTERN

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_README_PATH = REPO_ROOT / "README.md"

_IMAGE_REF_PATTERN = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)\)")
_LINK_PATTERN = re.compile(r"(?<!!)\[([^\]]*)\]\(([^)\s]+)\)")
_UNRESOLVED_PLACEHOLDERS = ("<username>", "<your-", "TODO:", "FIXME", "lorem ipsum")
_REQUIRED_SNIPPETS = ("Sushant Nemade", "Data & AI Engineer")
_IGNORED_ASSET_PREFIXES = ("private/", "build/")


class ReadmeValidationError(ValueError):
    """Raised by the CLI when validation finds one or more problems."""


_HTML_COMMENT_PATTERN = re.compile(r"<!--.*?-->", re.DOTALL)


def validate_readme_text(text: str, *, repo_root: Path) -> list[str]:
    """Return a list of human-readable problems; empty list means valid.

    HTML comments are stripped first since GitHub does not render their
    content (e.g. documentation notes about a pending asset).
    """
    problems: list[str] = []
    text = _HTML_COMMENT_PATTERN.sub("", text)

    for alt_text, target in _IMAGE_REF_PATTERN.findall(text):
        if target.startswith("http://") or target.startswith("https://"):
            problems.append(f"remote image reference is not permitted: {target}")
            continue
        if not alt_text.strip():
            problems.append(f"image {target!r} is missing meaningful alt text")
        if target.startswith(_IGNORED_ASSET_PREFIXES):
            problems.append(f"must not reference a git-ignored path as a visible image: {target}")
        elif not (repo_root / target).is_file():
            problems.append(f"referenced local asset does not exist: {target}")

    for label, target in _LINK_PATTERN.findall(text):
        if "case study in preparation" in label.lower():
            problems.append(f"'Case study in preparation' must not be a hyperlink (points to {target})")

    lowered = text.lower()
    for term in FORBIDDEN_METRIC_TERMS:
        if term in lowered:
            problems.append(f"forbidden unverified metric present: {term!r}")
    for title in FORBIDDEN_TITLES:
        if title in lowered:
            problems.append(f"forbidden job title present: {title!r}")
    if PHONE_LIKE_PATTERN.search(text):
        problems.append("phone-number-like content present")
    for placeholder in _UNRESOLVED_PLACEHOLDERS:
        if placeholder.lower() in lowered:
            problems.append(f"unresolved placeholder marker present: {placeholder!r}")

    for snippet in _REQUIRED_SNIPPETS:
        if snippet not in text:
            problems.append(f"required professional text missing: {snippet!r}")

    return problems


def validate_readme_file(path: Path, *, repo_root: Path = REPO_ROOT) -> list[str]:
    if not path.is_file():
        raise ReadmeValidationError(f"{path}: README file not found")
    return validate_readme_text(path.read_text(encoding="utf-8"), repo_root=repo_root)


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate README.md")
    parser.add_argument("--readme", type=Path, default=DEFAULT_README_PATH)
    args = parser.parse_args(argv)

    try:
        problems = validate_readme_file(args.readme)
    except ReadmeValidationError as exc:
        print(f"README validation failed: {exc}", file=sys.stderr)
        return 1

    if problems:
        for problem in problems:
            print(f"FAIL: {problem}", file=sys.stderr)
        return 1

    print(f"OK: {args.readme}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
