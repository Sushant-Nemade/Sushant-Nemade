"""Clean a private source photo for ASCII-portrait rendering.

Never operates on or writes anything under version control by default:
both the source photo and this module's output are git-ignored (see
.gitignore: private/*, build/*). Requires the optional 'art' dependencies
(tools/requirements-art.txt); never imported by the daily/CI workflow.

Usage (from the repository root):
    python -m tools.clean_photo --input private/source-photo.jpg
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageOps

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT_PATH = REPO_ROOT / "private" / "source-photo.jpg"
DEFAULT_OUTPUT_PATH = REPO_ROOT / "build" / "photo-ready.png"


class PhotoCleaningError(ValueError):
    """Raised when the source photo is missing or not a readable image."""


def clean_photo(input_path: Path, output_path: Path) -> None:
    """Validate, correct orientation, and normalize a photo for ASCII rendering."""
    if not input_path.is_file():
        raise PhotoCleaningError(f"{input_path}: source photo not found")
    try:
        image = Image.open(input_path)
        image.load()
    except Exception as exc:  # noqa: BLE001 - Pillow raises varied decode errors
        raise PhotoCleaningError(f"{input_path}: not a readable image ({exc})") from exc

    image = ImageOps.exif_transpose(image) or image
    grayscale = ImageOps.grayscale(image)
    normalized = ImageOps.autocontrast(grayscale, cutoff=1)

    try:
        import cv2  # type: ignore[import-not-found]
        import numpy as np

        array = np.array(normalized)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        normalized = Image.fromarray(clahe.apply(array))
        print("Applied CLAHE contrast enhancement (OpenCV available).")
    except ImportError:
        print("OpenCV not installed; skipping optional CLAHE step (Pillow autocontrast still applied).")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    normalized.save(output_path)


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Clean a private source photo.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    args = parser.parse_args(argv)

    try:
        clean_photo(args.input, args.output)
    except PhotoCleaningError as exc:
        print(f"Photo cleaning failed: {exc}")
        return 1

    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
