"""Validate that generated SVG files are well-formed and accessible.

Used both as a library (imported by renderer tests) and as a CLI entry point
(``python -m tools.validate_svg <file> [<file> ...]``) invoked by the local
end-to-end check and the ``validate-profile`` GitHub Actions workflow.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from lxml import etree

SVG_NS = "{http://www.w3.org/2000/svg}"


class SvgValidationError(ValueError):
    """Raised when an SVG document fails structural or accessibility checks."""


def _local_name(tag: str) -> str:
    return tag.split("}", 1)[1] if tag.startswith("{") else tag


def validate_svg_bytes(data: bytes, *, source: str) -> None:
    """Validate SVG content. Raises :class:`SvgValidationError` on any failure."""
    try:
        root = etree.fromstring(data)
    except etree.XMLSyntaxError as exc:
        raise SvgValidationError(f"{source}: not well-formed XML ({exc})") from exc

    if _local_name(root.tag) != "svg":
        raise SvgValidationError(f"{source}: root element is {root.tag!r}, expected <svg>")

    if not root.get("viewBox"):
        raise SvgValidationError(f"{source}: missing required 'viewBox' attribute")

    children_names = [_local_name(child.tag) for child in root]
    if "title" not in children_names:
        raise SvgValidationError(f"{source}: missing accessible <title> element")
    if "desc" not in children_names:
        raise SvgValidationError(f"{source}: missing accessible <desc> element")

    title_index = children_names.index("title")
    if title_index != 0:
        raise SvgValidationError(f"{source}: <title> must be the first child of <svg>")

    for element in root.iter():
        for attr_name, attr_value in element.attrib.items():
            if _local_name(attr_name) in {"href", "src"} and (
                attr_value.startswith("http://") or attr_value.startswith("https://")
            ):
                raise SvgValidationError(f"{source}: references a remote resource ({attr_value})")

    text_content = data.decode("utf-8", errors="replace")
    if "<script" in text_content.lower():
        raise SvgValidationError(f"{source}: <script> elements are not permitted")


def validate_svg_file(path: Path) -> None:
    if not path.is_file():
        raise SvgValidationError(f"{path}: file not found")
    validate_svg_bytes(path.read_bytes(), source=str(path))


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate one or more SVG files.")
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args(argv)

    failures: list[str] = []
    for path in args.paths:
        try:
            validate_svg_file(path)
        except SvgValidationError as exc:
            failures.append(str(exc))
        else:
            print(f"OK: {path}")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
