"""Shared SVG building blocks used by the panel, graph, and portrait renderers.

Centralising XML escaping, the accessible document skeleton, and the
reduced-motion/"run once and hold" animation CSS keeps the three renderers
visually consistent and avoids re-implementing security-sensitive escaping
logic three times.
"""

from __future__ import annotations

from xml.sax.saxutils import escape as _xml_escape

from tools.config import ThemeConfig

SVG_NAMESPACE = "http://www.w3.org/2000/svg"


def escape_text(value: str) -> str:
    """Escape a string for safe inclusion as SVG/XML character data."""
    return _xml_escape(value)


def escape_attr(value: str) -> str:
    """Escape a string for safe inclusion inside a double-quoted XML attribute."""
    return _xml_escape(value, {'"': "&quot;"})


def font_family_attr(theme: ThemeConfig) -> str:
    """Return an escaped font-family value safe for a double-quoted XML attribute."""
    return escape_attr(theme.font_stack)


def svg_open_tag(*, width: int, height: int, extra_attrs: str = "") -> str:
    """Return a responsive, namespaced ``<svg>`` opening tag.

    ``width="100%"`` with a matching ``viewBox`` lets the image scale to the
    container (GitHub README column) instead of clipping or leaving gaps.
    """
    return (
        f'<svg xmlns="{SVG_NAMESPACE}" role="img" width="100%" '
        f'viewBox="0 0 {width} {height}" preserveAspectRatio="xMidYMid meet"'
        f'{(" " + extra_attrs) if extra_attrs else ""}>'
    )


def title_and_desc(title: str, description: str) -> str:
    """Return ``<title>``/``<desc>`` elements. Must be the first children of ``<svg>``."""
    return (
        f"<title>{escape_text(title)}</title>"
        f"<desc>{escape_text(description)}</desc>"
    )


def reduced_motion_style(*, extra_css: str = "") -> str:
    """CSS shared by all animated renderers.

    Animations run once (default ``animation-iteration-count: 1``), hold
    their final state, and are fully disabled - with content shown at full
    opacity - when the user has requested reduced motion. Content is visible
    by default so clients that ignore animation rules still show every item;
    ``animation-fill-mode: both`` applies the transparent first keyframe only
    when the reveal animation itself is supported.
    """
    return (
        "<style>"
        ".lt-reveal{opacity:1;animation-name:lt-fade-in;"
        "animation-duration:0.35s;animation-timing-function:ease-out;"
        "animation-fill-mode:both;animation-iteration-count:1;}"
        "@keyframes lt-fade-in{from{opacity:0;}to{opacity:1;}}"
        "@media (prefers-reduced-motion: reduce){"
        ".lt-reveal{animation:none;opacity:1;}}"
        f"{extra_css}"
        "</style>"
    )


def wrap_svg(
    *,
    width: int,
    height: int,
    title: str,
    description: str,
    style: str,
    body: str,
) -> str:
    """Assemble a complete, well-formed SVG document string."""
    return (
        f"{svg_open_tag(width=width, height=height)}"
        f"{title_and_desc(title, description)}"
        f"{style}"
        f"{body}"
        "</svg>"
    )
