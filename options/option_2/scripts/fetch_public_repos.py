"""Fetch normalized public repository metadata for Option 2.

The built-in GitHub token is optional. Without one, this uses GitHub's public
REST API allowance and still produces the reduced public-data view.
"""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import httpx

from tools.config import DEFAULT_PROFILE_PATH, load_profile

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUTPUT = REPO_ROOT / "options" / "option_2" / "public-repos.json"
API_ROOT = "https://api.github.com"


class PublicRepoError(ValueError):
    """Raised when public repository metadata cannot be normalized."""


def fetch_public_repositories(username: str, *, token: str | None = None) -> dict:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "sushant-option-2-profile/1.0",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    with httpx.Client(headers=headers, timeout=15.0, follow_redirects=True) as client:
        response = client.get(
            f"{API_ROOT}/users/{username}/repos",
            params={"per_page": 100, "sort": "updated", "type": "public"},
        )
        response.raise_for_status()
        raw_repositories = response.json()
        if not isinstance(raw_repositories, list):
            raise PublicRepoError("GitHub repository response was not a list")

        repositories: list[dict] = []
        language_totals: dict[str, int] = {}
        for raw in raw_repositories:
            if raw.get("fork"):
                continue
            name = raw.get("name")
            if not isinstance(name, str) or not name:
                continue
            language_response = client.get(f"{API_ROOT}/repos/{username}/{name}/languages")
            language_response.raise_for_status()
            languages = language_response.json()
            if not isinstance(languages, dict):
                languages = {}
            normalized_languages = {
                str(language): int(byte_count)
                for language, byte_count in languages.items()
                if isinstance(byte_count, int) and byte_count >= 0
            }
            for language, byte_count in normalized_languages.items():
                language_totals[language] = language_totals.get(language, 0) + byte_count
            repositories.append(
                {
                    "name": name,
                    "url": str(raw.get("html_url") or ""),
                    "description": raw.get("description"),
                    "primary_language": raw.get("language"),
                    "languages": normalized_languages,
                    "stars": int(raw.get("stargazers_count") or 0),
                    "forks": int(raw.get("forks_count") or 0),
                    "archived": bool(raw.get("archived")),
                }
            )

    return {
        "schema_version": 1,
        "username": username,
        "retrieved_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "source": f"{API_ROOT}/users/{username}/repos",
        "repositories": repositories,
        "language_bytes": dict(
            sorted(language_totals.items(), key=lambda item: item[1], reverse=True)
        ),
    }


def _atomic_write(path: Path, document: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent, prefix=".tmp-option2-", suffix=".json"
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(document, handle, indent=2)
            handle.write("\n")
        os.replace(temporary_name, path)
    finally:
        if os.path.exists(temporary_name):
            os.remove(temporary_name)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fetch Option 2 public repository data")
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    profile = load_profile(args.profile)
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("METRICS_TOKEN")
    try:
        document = fetch_public_repositories(profile.identity.github_username, token=token)
        _atomic_write(args.output, document)
    except (httpx.HTTPError, PublicRepoError) as exc:
        print(f"Failed to fetch public repository metadata: {exc}")
        return 1
    print(f"Wrote {args.output} with {len(document['repositories'])} public repositories")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
