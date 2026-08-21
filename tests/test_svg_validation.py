"""Tests for tools.validate_svg: structural and accessibility validation."""

from __future__ import annotations

import pytest

from tools.validate_svg import SvgValidationError, validate_svg_bytes

VALID_SVG = (
    b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 50">'
    b"<title>Sample</title><desc>Sample description</desc>"
    b'<rect width="10" height="10"/>'
    b"</svg>"
)


def test_valid_svg_passes() -> None:
    validate_svg_bytes(VALID_SVG, source="valid.svg")


def test_malformed_xml_rejected() -> None:
    with pytest.raises(SvgValidationError, match="not well-formed"):
        validate_svg_bytes(b"<svg><title>oops</svg>", source="broken.svg")


def test_missing_title_rejected() -> None:
    data = (
        b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
        b"<desc>Description only</desc></svg>"
    )
    with pytest.raises(SvgValidationError, match="title"):
        validate_svg_bytes(data, source="no-title.svg")


def test_missing_desc_rejected() -> None:
    data = (
        b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
        b"<title>Title only</title></svg>"
    )
    with pytest.raises(SvgValidationError, match="desc"):
        validate_svg_bytes(data, source="no-desc.svg")


def test_missing_viewbox_rejected() -> None:
    data = (
        b'<svg xmlns="http://www.w3.org/2000/svg">'
        b"<title>T</title><desc>D</desc></svg>"
    )
    with pytest.raises(SvgValidationError, match="viewBox"):
        validate_svg_bytes(data, source="no-viewbox.svg")


def test_remote_resource_rejected() -> None:
    data = (
        b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
        b"<title>T</title><desc>D</desc>"
        b'<image href="https://example.com/x.png"/>'
        b"</svg>"
    )
    with pytest.raises(SvgValidationError, match="remote resource"):
        validate_svg_bytes(data, source="remote.svg")


def test_script_tag_rejected() -> None:
    data = (
        b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
        b"<title>T</title><desc>D</desc>"
        b"<script>alert(1)</script>"
        b"</svg>"
    )
    with pytest.raises(SvgValidationError, match="script"):
        validate_svg_bytes(data, source="script.svg")


def test_title_must_be_first_child() -> None:
    data = (
        b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
        b"<desc>D</desc><title>T</title>"
        b"</svg>"
    )
    with pytest.raises(SvgValidationError, match="first child"):
        validate_svg_bytes(data, source="order.svg")
