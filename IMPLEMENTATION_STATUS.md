# Implementation Status — Living Terminal Profile

Tracks phase progress, deliberate structural deviations, blocked items, and
required manual follow-up. Updated as each phase completes.

## Phase progress

| Phase | Description | Status |
|---|---|---|
| 1 | Safe project scaffold | complete |
| 2 | Terminal system information panel | complete |
| 3 | Public contribution data retrieval | complete |
| 4 | Contribution graph SVG | complete |
| 5 | ASCII portrait pipeline | complete (portrait generation itself pending a real photo; see below) |
| 6 | Recruiter-friendly README | complete |
| 7 | Profile validation workflow | complete |
| 8 | Daily contribution refresh workflow | complete |

## Structural deviations from the tree in the authorisation message

- Added `tools/svg_common.py`: shared XML-escaping, palette loading, and
  reduced-motion/animation CSS helpers used by the panel, graph, and portrait
  renderers. Without this, the same palette/escaping logic would be
  duplicated three times and could drift out of sync, violating the design
  system's "same palette" requirement.
- Added `tests/__init__.py` (empty) so `tools.*` imports resolve consistently
  under pytest regardless of invocation directory.

## Blocked / pending items requiring your input

- **Remote GitHub repository does not exist yet.** The local repository is
  initialized, committed (branch `main`), and has `origin` pointed at
  `https://github.com/Sushant-Nemade/Sushant-Nemade.git`, but `git ls-remote`
  confirms that repository does not exist yet on GitHub. To finish publishing
  as your profile README:
  1. Create a **public** repository on GitHub named exactly `Sushant-Nemade`
     (must match your username exactly for GitHub to render it as your
     profile README) — do not initialize it with a README, license, or
     .gitignore from the GitHub UI.
  2. Run `git push -u origin main` from this workspace (a Git Credential
     Manager / browser sign-in prompt will appear on first push).
  3. In the new repository's settings, enable **Settings → Actions →
     General → Workflow permissions → Read and write permissions** so
     `refresh-contributions.yml` can commit updated contribution data.

- **Portrait photo not present in the repository.** You mentioned a local
  file at `Downloads\Sushant-Nemade.png`, but no photo currently exists at
  `private/source-photo.jpg` in this workspace. The Phase 5 pipeline (photo
  cleanup + ASCII rendering) is implemented and tested against synthetic,
  non-personal fixtures only, and `README.md` currently omits the portrait
  (an HTML comment marks exactly where to add it). **To generate your real
  portrait after this session:**
  1. Copy your photo to `private/source-photo.jpg` (this path is git-ignored).
  2. Run: `python -m tools.clean_photo --input private/source-photo.jpg`
  3. Run: `python -m tools.render_portrait`
  4. Re-run `python -m tools.validate_svg assets/portrait.svg`
  5. Add the portrait `<img>`/Markdown image back into `README.md` at the
     location marked with an HTML comment.

- **Contribution data is currently seeded, not live.** `assets/contributions.json`
  and `assets/contribution-graph.svg` were generated from a local sample
  fixture (`source_description: "local dev seed (sample fixture, not a live
  fetch)"`) to prove the rendering pipeline end-to-end offline. Once Phase 8's
  refresh workflow runs (or you run `python -m tools.pull_contributions`
  locally with network access), these two files will be overwritten with real
  public contribution data for `Sushant-Nemade`.

## Required manual security follow-up

- GitHub Actions in `.github/workflows/` are pinned to full commit SHAs, each
  with a `# vX.Y.Z` comment recording the tag it was verified against:
  - `actions/checkout` → `3d3c42e5aac5ba805825da76410c181273ba90b1` (v7.0.1),
    verified against the GitHub Releases page's signed-commit reference.
  - `actions/setup-python` → `5fda3b95a4ea91299a34e894583c3862153e4b97` (v7.0.0),
    verified the same way.
  If either action publishes a new release before you push this repository,
  re-verify the SHA on the action's GitHub Releases page and update the
  comment alongside the hash.
- Repository setting required for `refresh-contributions.yml` to be able to
  push commits: **Settings → Actions → General → Workflow permissions → Read
  and write permissions** must be enabled (or an equivalent branch-protection
  allowance granted), otherwise the built-in `GITHUB_TOKEN` cannot push even
  though the workflow declares `contents: write`.
- `refresh-contributions.yml` only ever stages `assets/contributions.json`
  and `assets/contribution-graph.svg`; it never touches `assets/sysinfo.svg`
  or `assets/portrait.svg`, and uses only the built-in `GITHUB_TOKEN` (no
  personal access token).
- `validate-profile.yml` runs on `pull_request`, `push` to `main`, and manual
  `workflow_dispatch`, with `contents: read` only.

## Local environment note

Local development/test runs were performed with the only Python interpreter
available on this machine (3.14 via `py -0p`), since `pyproject.toml` requires
`>=3.12` and all required wheels (httpx, lxml, Pillow, numpy) are available
for 3.14 on Windows. CI workflows pin to Python 3.12 for a stable, widely
supported baseline.
