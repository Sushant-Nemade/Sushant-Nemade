"""Typed configuration loading and validation for the Living Terminal profile.

All personal/profile content lives in ``config/profile.json`` and
``config/theme.json``. Rendering modules must import the dataclasses defined
here instead of hard-coding personal data.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PROFILE_PATH = REPO_ROOT / "config" / "profile.json"
DEFAULT_THEME_PATH = REPO_ROOT / "config" / "theme.json"

# Display states a project may declare.
ProjectDisplayState = Literal["active", "case_study_in_preparation", "hidden"]
_VALID_DISPLAY_STATES = {"active", "case_study_in_preparation", "hidden"}

# Defence-in-depth: reject any configured text that matches an unverified
# metric, a banned job title, or an unresolved template placeholder, even
# though these should never be entered in config/profile.json in the first
# place. See requirements section "CLAIMS AND ACCURACY RULES".
FORBIDDEN_METRIC_TERMS = (
    "30 percent effort reduction",
    "40 percent effort reduction",
    "98 percent incident resolution",
    "model accuracy",
    "f1 score",
    "precision",
    "recall",
    "roi",
    "adoption rate",
    "financial saving",
    "process volume",
    "number of users",
)
FORBIDDEN_TITLES = (
    "senior data scientist",
    "ai architect",
    "ai strategy manager",
    "enterprise ai platform lead",
)
# Loosely matches phone-number-shaped strings (7+ digits with common separators).
PHONE_LIKE_PATTERN = re.compile(r"(\+?\d[\d\-\s()]{6,}\d)")
_UNRESOLVED_PLACEHOLDER_PATTERN = re.compile(r"[<>]")


class ConfigError(ValueError):
    """Raised when a configuration file is missing, malformed, or unsafe."""


@dataclass(frozen=True)
class Identity:
    name: str
    github_username: str
    role: str
    location: str
    education: str
    headline: str
    value_proposition: str


@dataclass(frozen=True)
class Contact:
    linkedin: str | None
    github: str | None
    email: str | None


@dataclass(frozen=True)
class CapabilityGroup:
    key: str
    label: str
    items: tuple[str, ...]


@dataclass(frozen=True)
class ExperienceEntry:
    organisation: str
    summary: str


@dataclass(frozen=True)
class EducationEntry:
    institution: str
    degree: str


@dataclass(frozen=True)
class Project:
    name: str
    description: str
    technologies: tuple[str, ...]
    repository_url: str | None
    display_state: ProjectDisplayState


@dataclass(frozen=True)
class ProfileConfig:
    identity: Identity
    focus: tuple[str, ...]
    approach: tuple[str, ...]
    principles: tuple[str, ...]
    languages_spoken: str
    status: str
    capability_groups: tuple[CapabilityGroup, ...]
    contact: Contact
    experience: tuple[ExperienceEntry, ...]
    education_entries: tuple[EducationEntry, ...]
    projects: tuple[Project, ...]


@dataclass(frozen=True)
class ThemeConfig:
    palette: dict[str, str]
    font_stack: str
    animation: dict[str, float] = field(default_factory=dict)


def _iter_strings(value: Any) -> list[str]:
    """Recursively collect every string found in a JSON-decoded structure."""
    found: list[str] = []
    if isinstance(value, str):
        found.append(value)
    elif isinstance(value, dict):
        for v in value.values():
            found.extend(_iter_strings(v))
    elif isinstance(value, list):
        for v in value:
            found.extend(_iter_strings(v))
    return found


def _validate_no_forbidden_content(raw: dict[str, Any], *, source: str) -> None:
    """Reject unverified metrics, banned titles, phone numbers, placeholders."""
    violations: list[str] = []
    for text in _iter_strings(raw):
        lowered = text.lower()
        for term in FORBIDDEN_METRIC_TERMS:
            if term in lowered:
                violations.append(f"forbidden unverified metric {term!r} in: {text!r}")
        for title in FORBIDDEN_TITLES:
            if title in lowered:
                violations.append(f"forbidden job title {title!r} in: {text!r}")
        if _UNRESOLVED_PLACEHOLDER_PATTERN.search(text):
            violations.append(f"unresolved placeholder marker (< or >) in: {text!r}")
        if PHONE_LIKE_PATTERN.search(text):
            violations.append(f"phone-number-like content in: {text!r}")
    if violations:
        details = "\n  - ".join(violations)
        raise ConfigError(f"{source} failed content-safety validation:\n  - {details}")


def _require_str(data: dict[str, Any], key: str, *, source: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{source}: field {key!r} must be a non-empty string")
    return value


_USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$")


def is_plausible_github_username(username: str) -> bool:
    """Return True if ``username`` looks like a real (non-placeholder) GitHub username."""
    return bool(_USERNAME_PATTERN.match(username))


def _validate_github_username(username: str, *, source: str) -> None:
    if not is_plausible_github_username(username):
        raise ConfigError(
            f"{source}: github_username {username!r} is not a plausible GitHub username"
        )


def load_profile(path: Path = DEFAULT_PROFILE_PATH) -> ProfileConfig:
    """Load and strictly validate ``config/profile.json``."""
    source = str(path)
    if not path.is_file():
        raise ConfigError(f"{source}: profile configuration file not found")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"{source}: invalid JSON ({exc})") from exc
    if not isinstance(raw, dict):
        raise ConfigError(f"{source}: top-level JSON value must be an object")

    if "phone" in raw or "phone" in raw.get("contact", {}):
        raise ConfigError(f"{source}: a 'phone' field is not permitted in profile configuration")
    if "work_authorisation" in raw or "work_authorization" in raw:
        raise ConfigError(f"{source}: work-authorisation fields are not permitted")

    _validate_no_forbidden_content(raw, source=source)

    identity_raw = raw.get("identity")
    if not isinstance(identity_raw, dict):
        raise ConfigError(f"{source}: 'identity' object is required")
    identity = Identity(
        name=_require_str(identity_raw, "name", source=source),
        github_username=_require_str(identity_raw, "github_username", source=source),
        role=_require_str(identity_raw, "role", source=source),
        location=_require_str(identity_raw, "location", source=source),
        education=_require_str(identity_raw, "education", source=source),
        headline=_require_str(identity_raw, "headline", source=source),
        value_proposition=_require_str(identity_raw, "value_proposition", source=source),
    )
    _validate_github_username(identity.github_username, source=source)

    focus = tuple(raw.get("focus") or ())
    approach = tuple(raw.get("approach") or ())
    principles = tuple(raw.get("principles") or ())
    if not focus or not all(isinstance(item, str) for item in focus):
        raise ConfigError(f"{source}: 'focus' must be a non-empty list of strings")

    languages_spoken = _require_str(raw, "languages_spoken", source=source)
    status = _require_str(raw, "status", source=source)

    capability_groups: list[CapabilityGroup] = []
    for group_raw in raw.get("capability_groups") or ():
        if not isinstance(group_raw, dict):
            raise ConfigError(f"{source}: each capability group must be an object")
        items = tuple(group_raw.get("items") or ())
        if not items:
            raise ConfigError(f"{source}: capability group {group_raw.get('key')!r} has no items")
        capability_groups.append(
            CapabilityGroup(
                key=_require_str(group_raw, "key", source=source),
                label=_require_str(group_raw, "label", source=source),
                items=items,
            )
        )
    if not capability_groups:
        raise ConfigError(f"{source}: at least one capability group is required")

    contact_raw = raw.get("contact") or {}
    if not isinstance(contact_raw, dict):
        raise ConfigError(f"{source}: 'contact' must be an object")
    email = contact_raw.get("email")
    if email is not None and (not isinstance(email, str) or "@" not in email):
        raise ConfigError(f"{source}: contact.email must be null or contain '@'")
    contact = Contact(
        linkedin=contact_raw.get("linkedin"),
        github=contact_raw.get("github"),
        email=email,
    )

    experience = tuple(
        ExperienceEntry(
            organisation=_require_str(item, "organisation", source=source),
            summary=_require_str(item, "summary", source=source),
        )
        for item in raw.get("experience") or ()
    )
    education_entries = tuple(
        EducationEntry(
            institution=_require_str(item, "institution", source=source),
            degree=_require_str(item, "degree", source=source),
        )
        for item in raw.get("education_entries") or ()
    )

    projects: list[Project] = []
    for project_raw in raw.get("projects") or ():
        if not isinstance(project_raw, dict):
            raise ConfigError(f"{source}: each project must be an object")
        display_state = project_raw.get("display_state")
        if display_state not in _VALID_DISPLAY_STATES:
            raise ConfigError(
                f"{source}: project {project_raw.get('name')!r} has invalid "
                f"display_state {display_state!r}"
            )
        repository_url = project_raw.get("repository_url")
        if display_state == "active" and not repository_url:
            raise ConfigError(
                f"{source}: project {project_raw.get('name')!r} is 'active' but has no "
                "repository_url"
            )
        if display_state != "active" and repository_url:
            raise ConfigError(
                f"{source}: project {project_raw.get('name')!r} must not set repository_url "
                f"while display_state is {display_state!r}"
            )
        technologies = tuple(project_raw.get("technologies") or ())
        if not technologies:
            raise ConfigError(f"{source}: project {project_raw.get('name')!r} has no technologies")
        projects.append(
            Project(
                name=_require_str(project_raw, "name", source=source),
                description=_require_str(project_raw, "description", source=source),
                technologies=technologies,
                repository_url=repository_url,
                display_state=display_state,
            )
        )
    if not projects:
        raise ConfigError(f"{source}: at least one project is required")

    return ProfileConfig(
        identity=identity,
        focus=focus,
        approach=approach,
        principles=principles,
        languages_spoken=languages_spoken,
        status=status,
        capability_groups=tuple(capability_groups),
        contact=contact,
        experience=experience,
        education_entries=education_entries,
        projects=tuple(projects),
    )


_HEX_COLOR_PATTERN = re.compile(r"^#[0-9A-Fa-f]{6}$")
_REQUIRED_PALETTE_KEYS = (
    "background",
    "panel_background",
    "text_primary",
    "text_muted",
    "accent_primary",
    "accent_secondary",
    "accent_positive",
    "border",
)


def load_theme(path: Path = DEFAULT_THEME_PATH) -> ThemeConfig:
    """Load and validate ``config/theme.json``."""
    source = str(path)
    if not path.is_file():
        raise ConfigError(f"{source}: theme configuration file not found")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"{source}: invalid JSON ({exc})") from exc
    if not isinstance(raw, dict):
        raise ConfigError(f"{source}: top-level JSON value must be an object")

    palette = raw.get("palette")
    if not isinstance(palette, dict):
        raise ConfigError(f"{source}: 'palette' object is required")
    for key in _REQUIRED_PALETTE_KEYS:
        value = palette.get(key)
        if not isinstance(value, str) or not _HEX_COLOR_PATTERN.match(value):
            raise ConfigError(f"{source}: palette.{key} must be a '#RRGGBB' hex colour")

    font_stack = _require_str(raw, "font_stack", source=source)
    if "http://" in font_stack or "https://" in font_stack:
        raise ConfigError(f"{source}: font_stack must not reference remote resources")

    animation_raw = raw.get("animation") or {}
    if not isinstance(animation_raw, dict):
        raise ConfigError(f"{source}: 'animation' must be an object")
    animation: dict[str, float] = {}
    for key, value in animation_raw.items():
        if not isinstance(value, (int, float)) or value < 0:
            raise ConfigError(f"{source}: animation.{key} must be a non-negative number")
        animation[key] = float(value)

    return ThemeConfig(palette=dict(palette), font_stack=font_stack, animation=animation)


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate Living Terminal configuration files.")
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE_PATH)
    parser.add_argument("--theme", type=Path, default=DEFAULT_THEME_PATH)
    args = parser.parse_args(argv)

    try:
        profile = load_profile(args.profile)
        theme = load_theme(args.theme)
    except ConfigError as exc:
        print(f"Configuration validation failed: {exc}", file=sys.stderr)
        return 1

    print(f"OK: profile for {profile.identity.name} ({profile.identity.github_username})")
    print(f"OK: {len(profile.projects)} project(s), {len(profile.capability_groups)} capability group(s)")
    print(f"OK: theme palette with {len(theme.palette)} colours")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
