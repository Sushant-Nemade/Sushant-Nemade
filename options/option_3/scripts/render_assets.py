"""Render the dark Systems Console assets for Option 3."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
import textwrap
from pathlib import Path
from xml.sax.saxutils import escape

from PIL import Image

from tools.config import DEFAULT_PROFILE_PATH, ProfileConfig, load_profile

REPO_ROOT = Path(__file__).resolve().parents[3]
OPTION_ROOT = REPO_ROOT / "options" / "option_3"
DEFAULT_CONFIG = OPTION_ROOT / "config.json"
DEFAULT_PORTRAIT = REPO_ROOT / "build" / "photo-ready.png"
DEFAULT_OUTPUT = OPTION_ROOT / "assets"
FONT = "Segoe UI,Helvetica,Arial,sans-serif"
MONO = "Consolas,Liberation Mono,monospace"


def _load_json(path: Path) -> dict:
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return document


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent, prefix=".tmp-option3-", suffix=".svg"
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        os.replace(temporary_name, path)
    finally:
        if os.path.exists(temporary_name):
            os.remove(temporary_name)


def _svg(width: int, height: int, title: str, description: str, body: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" role="img" width="100%" '
        f'viewBox="0 0 {width} {height}" preserveAspectRatio="xMidYMid meet">'
        f"<title>{escape(title)}</title><desc>{escape(description)}</desc>{body}</svg>"
    )


def _text(
    x: float,
    y: float,
    value: str,
    *,
    size: int,
    fill: str,
    weight: int = 400,
    family: str = FONT,
    anchor: str = "start",
    css_class: str = "",
) -> str:
    class_attr = f' class="{css_class}"' if css_class else ""
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" font-family="{family}" font-size="{size}" '
        f'font-weight="{weight}" fill="{fill}" text-anchor="{anchor}"{class_attr}>'
        f"{escape(value)}</text>"
    )


def _frame(width: int, height: int, palette: dict[str, str]) -> str:
    return (
        f'<rect width="{width}" height="{height}" rx="8" fill="{palette["background"]}" '
        f'stroke="{palette["border"]}"/>'
        f'<path d="M1 46 H{width - 1}" stroke="{palette["border"]}"/>'
        f'<circle cx="20" cy="23" r="4" fill="{palette["red"]}"/>'
        f'<circle cx="36" cy="23" r="4" fill="{palette["amber"]}"/>'
        f'<circle cx="52" cy="23" r="4" fill="{palette["green"]}"/>'
    )


def _shared_style() -> str:
    return (
        "<style>"
        ".boot{opacity:1;animation:boot .45s ease-out both}"
        ".d1{animation-delay:.2s}.d2{animation-delay:.4s}.d3{animation-delay:.6s}"
        ".cursor{opacity:1;animation:blink 1.1s steps(2,end) infinite}"
        ".module{transform-box:fill-box;transform-origin:center;animation:breathe 4s ease-in-out infinite}"
        ".m2{animation-delay:.5s}.m3{animation-delay:1s}.m4{animation-delay:1.5s}.m5{animation-delay:2s}"
        ".scan{animation:scan 7s linear infinite}"
        "@keyframes boot{from{opacity:0;transform:translateY(7px)}to{opacity:1;transform:none}}"
        "@keyframes blink{50%{opacity:.15}}"
        "@keyframes breathe{0%,100%{opacity:.82}50%{opacity:1}}"
        "@keyframes scan{from{transform:translateY(0)}to{transform:translateY(430px)}}"
        "@media(prefers-reduced-motion:reduce){"
        ".boot,.cursor,.module,.scan{animation:none}.moving{display:none}}"
        "</style>"
    )


def _portrait_dots(
    image: Image.Image,
    *,
    columns: int,
    origin_x: float,
    origin_y: float,
    max_width: float,
    max_height: float,
    color: str,
) -> str:
    grayscale = image.convert("L")
    rows = max(1, round(columns * grayscale.height / grayscale.width * 0.7))
    sampled = grayscale.resize((columns, rows))
    cell = min(max_width / columns, max_height / rows)
    actual_width = columns * cell
    actual_height = rows * cell
    start_x = origin_x + (max_width - actual_width) / 2
    start_y = origin_y + (max_height - actual_height) / 2
    dots: list[str] = []
    for row in range(rows):
        for column in range(columns):
            darkness = (255 - sampled.getpixel((column, row))) / 255
            if darkness < 0.1:
                continue
            radius = 0.35 + darkness * min(1.65, cell * 0.32)
            dots.append(
                f'<circle cx="{start_x + (column + 0.5) * cell:.1f}" '
                f'cy="{start_y + (row + 0.5) * cell:.1f}" r="{radius:.2f}" '
                f'fill="{color}" fill-opacity="{0.24 + darkness * 0.76:.2f}"/>'
            )
    return "".join(dots)


def render_terminal_hero(
    profile: ProfileConfig, image: Image.Image, config: dict, palette: dict[str, str]
) -> str:
    width, height = 900, 390
    body = [_frame(width, height, palette), _shared_style()]
    body.append(_text(76, 28, "systems-console / identity", size=11, fill=palette["muted"], family=MONO))
    body.append(f'<rect x="24" y="68" width="286" height="292" rx="5" fill="{palette["panel"]}" stroke="{palette["border"]}"/>')
    body.append(
        _portrait_dots(
            image,
            columns=int(config["portrait_columns"]),
            origin_x=34,
            origin_y=77,
            max_width=266,
            max_height=268,
            color=palette["cyan"],
        )
    )
    body.append(_text(334, 93, "$ boot profile --mode professional", size=13, fill=palette["green"], family=MONO, css_class="boot"))
    body.append(_text(334, 133, profile.identity.name, size=32, fill=palette["text"], weight=700, css_class="boot d1"))
    body.append(_text(334, 166, profile.identity.headline, size=17, fill=palette["cyan"], weight=600, css_class="boot d2"))
    body.append(f'<path d="M334 186 H862" stroke="{palette["border"]}"/>')
    rows = [
        ("location", profile.identity.location),
        ("education", profile.identity.education),
        ("focus", " / ".join(profile.focus)),
        ("principles", " / ".join(profile.principles)),
        ("status", profile.status),
    ]
    y = 218
    for index, (key, value) in enumerate(rows):
        css_class = f"boot d{min(index + 1, 3)}"
        body.append(_text(334, y, f"{key:<11}", size=12, fill=palette["muted"], weight=700, family=MONO, css_class=css_class))
        body.append(_text(432, y, value, size=13, fill=palette["text"], family=MONO, css_class=css_class))
        y += 30
    body.append(f'<rect x="334" y="348" width="10" height="18" fill="{palette["green"]}" class="cursor"/>')
    return _svg(
        width,
        height,
        f"Systems Console identity for {profile.identity.name}",
        f"Dark terminal identity panel for {profile.identity.name}, {profile.identity.headline}.",
        "".join(body),
    )


def render_terminal_hero_mobile(
    profile: ProfileConfig, image: Image.Image, config: dict, palette: dict[str, str]
) -> str:
    width, height = 390, 720
    body = [_frame(width, height, palette), _shared_style()]
    body.append(_text(76, 28, "systems-console / identity", size=10, fill=palette["muted"], family=MONO))
    body.append(f'<rect x="44" y="66" width="302" height="286" rx="5" fill="{palette["panel"]}" stroke="{palette["border"]}"/>')
    body.append(
        _portrait_dots(
            image,
            columns=int(config["portrait_columns"]),
            origin_x=54,
            origin_y=76,
            max_width=282,
            max_height=266,
            color=palette["cyan"],
        )
    )
    body.append(_text(22, 388, "$ boot profile --mode professional", size=11, fill=palette["green"], family=MONO, css_class="boot"))
    body.append(_text(22, 430, profile.identity.name, size=27, fill=palette["text"], weight=700, css_class="boot d1"))
    body.append(_text(22, 462, "Enterprise GenAI / RAG / Analytics", size=13, fill=palette["cyan"], weight=700, css_class="boot d2"))
    body.append(_text(22, 483, "Automation", size=13, fill=palette["cyan"], weight=700, css_class="boot d2"))
    body.append(f'<path d="M22 503 H368" stroke="{palette["border"]}"/>')
    rows = [
        ("location", profile.identity.location),
        ("education", profile.identity.education),
        ("focus", "GenAI / RAG / Analytics / Automation"),
        ("principles", "Responsible AI / GDPR / Oversight"),
        ("status", "Open to full-time Data and AI roles"),
    ]
    y = 535
    for index, (key, value) in enumerate(rows):
        css_class = f"boot d{min(index + 1, 3)}"
        body.append(_text(22, y, key.upper(), size=9, fill=palette["muted"], weight=700, family=MONO, css_class=css_class))
        body.append(_text(112, y, value, size=10, fill=palette["text"], family=MONO, css_class=css_class))
        y += 31
    body.append(f'<rect x="22" y="690" width="9" height="16" fill="{palette["green"]}" class="cursor"/>')
    return _svg(width, height, f"Mobile Systems Console identity for {profile.identity.name}", "Mobile dark terminal identity panel with a dot-matrix portrait and professional profile facts.", "".join(body))


def _iso_cube(
    center_x: float,
    baseline_y: float,
    *,
    width: float,
    depth: float,
    height: float,
    palette: dict[str, str],
    accent: str,
    label: str,
    css_class: str,
) -> str:
    half = width / 2
    top = (
        f"{center_x - half:.1f},{baseline_y - height:.1f} "
        f"{center_x:.1f},{baseline_y - height - depth:.1f} "
        f"{center_x + half:.1f},{baseline_y - height:.1f} "
        f"{center_x:.1f},{baseline_y - height + depth:.1f}"
    )
    left = (
        f"{center_x - half:.1f},{baseline_y - height:.1f} "
        f"{center_x:.1f},{baseline_y - height + depth:.1f} "
        f"{center_x:.1f},{baseline_y + depth:.1f} "
        f"{center_x - half:.1f},{baseline_y:.1f}"
    )
    right = (
        f"{center_x:.1f},{baseline_y - height + depth:.1f} "
        f"{center_x + half:.1f},{baseline_y - height:.1f} "
        f"{center_x + half:.1f},{baseline_y:.1f} "
        f"{center_x:.1f},{baseline_y + depth:.1f}"
    )
    return (
        f'<g class="module {css_class}">'
        f'<ellipse cx="{center_x}" cy="{baseline_y + depth + 13}" rx="{half + 8}" ry="10" fill="#000000" fill-opacity=".3"/>'
        f'<polygon points="{left}" fill="{palette["panel_raised"]}" stroke="{palette["border"]}"/>'
        f'<polygon points="{right}" fill="{palette["panel"]}" stroke="{palette["border"]}"/>'
        f'<polygon points="{top}" fill="{accent}" fill-opacity=".72" stroke="{accent}"/>'
        f'<circle cx="{center_x}" cy="{baseline_y - height}" r="4" fill="{palette["text"]}"/>'
        f'</g>'
        + _text(center_x, baseline_y + depth + 43, label.upper(), size=11, fill=palette["text"], weight=700, family=MONO, anchor="middle")
    )


def render_system_architecture(profile: ProfileConfig, palette: dict[str, str]) -> str:
    width, height = 900, 540
    body = [_frame(width, height, palette), _shared_style()]
    body.append(_text(76, 28, "systems-console / delivery-architecture", size=11, fill=palette["muted"], family=MONO))
    body.append(_text(24, 82, "FROM AMBIGUITY TO ADOPTION", size=13, fill=palette["cyan"], weight=700, family=MONO))
    body.append(_text(876, 82, "LIVE SIGNAL PATH", size=10, fill=palette["green"], weight=700, family=MONO, anchor="end"))
    body.append(f'<polygon points="70,390 450,150 830,390 450,510" fill="{palette["panel"]}" stroke="{palette["border"]}"/>')
    for index in range(1, 9):
        ratio = index / 9
        left_x = 70 + (450 - 70) * ratio
        left_y = 390 + (510 - 390) * ratio
        right_x = 830 + (450 - 830) * ratio
        right_y = 390 + (510 - 390) * ratio
        body.append(f'<path d="M{left_x:.1f} {left_y:.1f} L{right_x:.1f} {right_y:.1f}" stroke="{palette["border"]}" stroke-opacity=".45"/>')
    for index in range(1, 9):
        ratio = index / 9
        top_x = 450 + (830 - 450) * ratio
        top_y = 150 + (390 - 150) * ratio
        bottom_x = 450 + (70 - 450) * ratio
        bottom_y = 510 + (390 - 510) * ratio
        body.append(f'<path d="M{top_x:.1f} {top_y:.1f} L{bottom_x:.1f} {bottom_y:.1f}" stroke="{palette["border"]}" stroke-opacity=".45"/>')
    positions = [(145, 363), (295, 310), (450, 260), (605, 310), (755, 363)]
    accents = [palette["cyan"], palette["green"], palette["amber"], palette["cyan"], palette["green"]]
    classes = ["", "m2", "m3", "m4", "m5"]
    heights = [42, 55, 74, 55, 42]
    for index, ((x, y), label) in enumerate(zip(positions, profile.approach)):
        body.append(
            _iso_cube(
                x,
                y,
                width=88,
                depth=25,
                height=heights[index],
                palette=palette,
                accent=accents[index],
                label=label,
                css_class=classes[index],
            )
        )
    path = "M145 315 C220 270 250 270 295 252 S400 190 450 185 S550 265 605 252 S700 280 755 315"
    body.append(f'<path d="{path}" fill="none" stroke="{palette["cyan"]}" stroke-width="2" stroke-dasharray="5 8" stroke-opacity=".45"/>')
    for begin, color in (("0s", palette["cyan"]), ("2.7s", palette["green"]), ("5.4s", palette["amber"])):
        body.append(
            f'<circle r="5" fill="{color}" class="moving"><animateMotion dur="8.1s" '
            f'begin="{begin}" repeatCount="indefinite" path="{path}"/></circle>'
        )
    body.append(f'<rect x="24" y="476" width="852" height="42" rx="4" fill="{palette["panel_raised"]}" stroke="{palette["border"]}"/>')
    body.append(_text(42, 502, "governance", size=11, fill=palette["muted"], weight=700, family=MONO))
    body.append(_text(132, 502, "RESPONSIBLE AI", size=11, fill=palette["green"], weight=700, family=MONO))
    body.append(_text(278, 502, "GDPR", size=11, fill=palette["cyan"], weight=700, family=MONO))
    body.append(_text(350, 502, "HUMAN OVERSIGHT", size=11, fill=palette["amber"], weight=700, family=MONO))
    body.append(_text(858, 502, "OUTPUT: USABLE SYSTEMS", size=11, fill=palette["text"], weight=700, family=MONO, anchor="end"))
    return _svg(
        width,
        height,
        "Pseudo-3D AI systems delivery architecture",
        "An isometric five-stage architecture from discovery through adoption, with responsible AI, GDPR, and human oversight as governing controls.",
        "".join(body),
    )


def render_system_architecture_mobile(profile: ProfileConfig, palette: dict[str, str]) -> str:
    width, height = 390, 690
    body = [_frame(width, height, palette), _shared_style()]
    body.append(_text(76, 28, "systems-console / architecture", size=10, fill=palette["muted"], family=MONO))
    body.append(_text(18, 78, "FROM AMBIGUITY TO ADOPTION", size=11, fill=palette["cyan"], weight=700, family=MONO))
    body.append(f'<polygon points="22,510 195,215 368,510 195,650" fill="{palette["panel"]}" stroke="{palette["border"]}"/>')
    positions = [(67, 500), (128, 423), (195, 340), (262, 423), (323, 500)]
    accents = [palette["cyan"], palette["green"], palette["amber"], palette["cyan"], palette["green"]]
    classes = ["", "m2", "m3", "m4", "m5"]
    heights = [34, 43, 58, 43, 34]
    for index, ((x, y), label) in enumerate(zip(positions, profile.approach)):
        body.append(
            _iso_cube(
                x,
                y,
                width=54,
                depth=16,
                height=heights[index],
                palette=palette,
                accent=accents[index],
                label=label,
                css_class=classes[index],
            )
        )
    path = "M67 460 C96 420 110 405 128 385 S170 300 195 278 S235 405 262 385 S302 420 323 460"
    body.append(f'<path d="{path}" fill="none" stroke="{palette["cyan"]}" stroke-width="2" stroke-dasharray="4 7" stroke-opacity=".5"/>')
    body.append(f'<circle r="5" fill="{palette["green"]}" class="moving"><animateMotion dur="8s" repeatCount="indefinite" path="{path}"/></circle>')
    body.append(f'<rect x="18" y="618" width="354" height="52" rx="4" fill="{palette["panel_raised"]}" stroke="{palette["border"]}"/>')
    body.append(_text(32, 640, "CONTROL PLANE", size=9, fill=palette["muted"], weight=700, family=MONO))
    body.append(_text(32, 657, "RESPONSIBLE AI / GDPR / HUMAN OVERSIGHT", size=9, fill=palette["green"], weight=700, family=MONO))
    return _svg(width, height, "Mobile pseudo-3D AI delivery architecture", "Mobile isometric five-stage delivery architecture with governance controls and a moving signal path.", "".join(body))


def render_capability_deck(profile: ProfileConfig, palette: dict[str, str]) -> str:
    width, height = 900, 290
    body = [_frame(width, height, palette), _shared_style()]
    body.append(_text(76, 28, "systems-console / capability-deck", size=11, fill=palette["muted"], family=MONO))
    colors = [palette["cyan"], palette["green"], palette["amber"], palette["red"], palette["cyan"], palette["green"]]
    for index, group in enumerate(profile.capability_groups):
        column = index % 3
        row = index // 3
        x = 24 + column * 290
        y = 68 + row * 100
        body.append(f'<rect x="{x}" y="{y}" width="272" height="78" rx="5" fill="{palette["panel"]}" stroke="{palette["border"]}"/>')
        body.append(f'<rect x="{x}" y="{y}" width="5" height="78" rx="2" fill="{colors[index]}"/>')
        body.append(_text(x + 20, y + 26, group.label.upper(), size=10, fill=colors[index], weight=700, family=MONO))
        body.append(_text(x + 20, y + 52, " / ".join(group.items), size=13, fill=palette["text"], weight=600))
        body.append(_text(x + 252, y + 26, f"0{index + 1}", size=10, fill=palette["muted"], family=MONO, anchor="end"))
    body.append(f'<rect x="24" y="264" width="852" height="2" fill="{palette["cyan"]}" fill-opacity=".15" class="scan"/>')
    return _svg(width, height, "Capability command deck", "Six verified capability groups from the profile configuration.", "".join(body))


def render_capability_deck_mobile(profile: ProfileConfig, palette: dict[str, str]) -> str:
    width, height = 390, 690
    body = [_frame(width, height, palette), _shared_style()]
    body.append(_text(76, 28, "systems-console / capabilities", size=10, fill=palette["muted"], family=MONO))
    colors = [palette["cyan"], palette["green"], palette["amber"], palette["red"], palette["cyan"], palette["green"]]
    for index, group in enumerate(profile.capability_groups):
        x = 18
        y = 62 + index * 101
        body.append(f'<rect x="{x}" y="{y}" width="354" height="82" rx="5" fill="{palette["panel"]}" stroke="{palette["border"]}"/>')
        body.append(f'<rect x="{x}" y="{y}" width="5" height="82" rx="2" fill="{colors[index]}"/>')
        body.append(_text(x + 20, y + 28, group.label.upper(), size=10, fill=colors[index], weight=700, family=MONO))
        body.append(_text(x + 20, y + 57, " / ".join(group.items), size=12, fill=palette["text"], weight=600))
        body.append(_text(x + 334, y + 28, f"0{index + 1}", size=10, fill=palette["muted"], family=MONO, anchor="end"))
    return _svg(width, height, "Mobile capability command deck", "Six readable capability groups arranged vertically for narrow screens.", "".join(body))


def render_project_board(profile: ProfileConfig, palette: dict[str, str]) -> str:
    width, height = 900, 590
    body = [_frame(width, height, palette), _shared_style()]
    body.append(_text(76, 28, "systems-console / selected-work", size=11, fill=palette["muted"], family=MONO))
    accents = [palette["cyan"], palette["green"], palette["amber"], palette["red"]]
    for index, project in enumerate(profile.projects[:4]):
        column = index % 2
        row = index // 2
        x = 24 + column * 438
        y = 68 + row * 252
        body.append(f'<rect x="{x}" y="{y}" width="414" height="226" rx="6" fill="{palette["panel"]}" stroke="{palette["border"]}"/>')
        body.append(f'<path d="M{x} {y + 48} H{x + 414}" stroke="{palette["border"]}"/>')
        body.append(_text(x + 18, y + 29, f"CASE / {index + 1:02d}", size=10, fill=accents[index], weight=700, family=MONO))
        body.append(_text(x + 394, y + 29, "IN PREPARATION", size=9, fill=palette["muted"], family=MONO, anchor="end"))
        title_y = y + 78
        for line in textwrap.wrap(project.name, width=39)[:2]:
            body.append(_text(x + 18, title_y, line, size=17, fill=palette["text"], weight=700))
            title_y += 22
        description_y = title_y + 12
        for line in textwrap.wrap(project.description, width=58)[:3]:
            body.append(_text(x + 18, description_y, line, size=11, fill=palette["muted"]))
            description_y += 17
        body.append(_text(x + 18, y + 204, " / ".join(project.technologies[:4]), size=9, fill=accents[index], weight=700, family=MONO))
    body.append(_text(450, 573, "VERIFIED DESCRIPTIONS / PUBLIC LINKS ADDED ONLY WHEN READY", size=10, fill=palette["muted"], family=MONO, anchor="middle"))
    return _svg(width, height, "Selected work system board", "Four sanitized professional case studies, each marked as in preparation until a public repository is available.", "".join(body))


def render_project_board_mobile(profile: ProfileConfig, palette: dict[str, str]) -> str:
    width, height = 390, 1080
    body = [_frame(width, height, palette), _shared_style()]
    body.append(_text(76, 28, "systems-console / selected-work", size=10, fill=palette["muted"], family=MONO))
    accents = [palette["cyan"], palette["green"], palette["amber"], palette["red"]]
    for index, project in enumerate(profile.projects[:4]):
        x = 18
        y = 62 + index * 250
        body.append(f'<rect x="{x}" y="{y}" width="354" height="226" rx="6" fill="{palette["panel"]}" stroke="{palette["border"]}"/>')
        body.append(f'<path d="M{x} {y + 48} H{x + 354}" stroke="{palette["border"]}"/>')
        body.append(_text(x + 16, y + 29, f"CASE / {index + 1:02d}", size=10, fill=accents[index], weight=700, family=MONO))
        body.append(_text(x + 336, y + 29, "IN PREPARATION", size=8, fill=palette["muted"], family=MONO, anchor="end"))
        title_y = y + 77
        for line in textwrap.wrap(project.name, width=34)[:2]:
            body.append(_text(x + 16, title_y, line, size=15, fill=palette["text"], weight=700))
            title_y += 20
        description_y = title_y + 10
        for line in textwrap.wrap(project.description, width=50)[:4]:
            body.append(_text(x + 16, description_y, line, size=10, fill=palette["muted"]))
            description_y += 16
        body.append(_text(x + 16, y + 207, " / ".join(project.technologies[:3]), size=9, fill=accents[index], weight=700, family=MONO))
    return _svg(width, height, "Mobile selected work system board", "Four professional case studies arranged vertically for narrow screens.", "".join(body))


def render_all(
    *, profile_path: Path, config_path: Path, portrait_path: Path, output_dir: Path
) -> list[Path]:
    profile = load_profile(profile_path)
    config = _load_json(config_path)
    palette = config["palette"]
    if not portrait_path.is_file():
        raise ValueError(f"portrait input not found: {portrait_path}")
    with Image.open(portrait_path) as image:
        assets = {
            "terminal-hero.svg": render_terminal_hero(profile, image, config, palette),
            "terminal-hero-mobile.svg": render_terminal_hero_mobile(profile, image, config, palette),
            "system-architecture.svg": render_system_architecture(profile, palette),
            "system-architecture-mobile.svg": render_system_architecture_mobile(profile, palette),
            "capability-deck.svg": render_capability_deck(profile, palette),
            "capability-deck-mobile.svg": render_capability_deck_mobile(profile, palette),
            "project-board.svg": render_project_board(profile, palette),
            "project-board-mobile.svg": render_project_board_mobile(profile, palette),
        }
    written: list[Path] = []
    for name, content in assets.items():
        path = output_dir / name
        _write(path, content)
        written.append(path)
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render Option 3 Systems Console assets")
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE_PATH)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--portrait", type=Path, default=DEFAULT_PORTRAIT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    try:
        written = render_all(
            profile_path=args.profile,
            config_path=args.config,
            portrait_path=args.portrait,
            output_dir=args.output_dir,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Option 3 rendering failed: {exc}")
        return 1
    print(f"Wrote {len(written)} Option 3 assets to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())