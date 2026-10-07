from __future__ import annotations

from pathlib import Path

import pytesseract
from PIL import Image


def image_to_text(image_path: str | Path) -> str:
    """Extract text from an image with OCR. Requires Tesseract to be installed."""
    image = Image.open(image_path)
    text = pytesseract.image_to_string(image, lang="ara+eng")
    return text.strip()


__all__ = ["image_to_text"]
