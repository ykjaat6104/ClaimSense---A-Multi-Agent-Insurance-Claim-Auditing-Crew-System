from pathlib import Path

import fitz  # PyMuPDF
from PIL import Image

from app.config import get_settings


def _ocr_image(img: Image.Image) -> str:
    import pytesseract

    return pytesseract.image_to_string(img) or ""


def extract_text_from_pdf(path: Path, min_chars_per_page: int | None = None) -> str:
    """Prefer digital text; fall back to rendered-page OCR when text layer is thin."""
    settings = get_settings()
    threshold = min_chars_per_page if min_chars_per_page is not None else settings.min_text_chars_per_page
    doc = fitz.open(path)
    parts: list[str] = []
    try:
        for page in doc:
            text = (page.get_text("text") or "").strip()
            if len(text) >= threshold:
                parts.append(text)
                continue
            pix = page.get_pixmap(dpi=200)
            mode = "RGB" if pix.alpha == 0 else "RGBA"
            img = Image.frombytes(mode, [pix.width, pix.height], pix.samples)
            if mode == "RGBA":
                img = img.convert("RGB")
            parts.append(_ocr_image(img))
    finally:
        doc.close()
    return "\n\n".join(p for p in parts if p)


def extract_text_from_image(path: Path) -> str:
    img = Image.open(path)
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    return _ocr_image(img)


def extract_text_auto(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".webp", ".bmp"}:
        return extract_text_from_image(path)
    if suffix == ".pdf":
        return extract_text_from_pdf(path)
    # Plain text / csv fallback
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""
