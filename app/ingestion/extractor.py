import hashlib
from pathlib import Path

from pypdf import PdfReader


def extract_pdf(path: str | Path) -> dict:
    """Extract page text and retain half-open character intervals per page."""
    pdf_path = Path(path)
    reader = PdfReader(str(pdf_path))
    parts: list[str] = []
    page_info: list[tuple[int, int, int]] = []
    offset = 0

    for page_number, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if not text:
            continue
        if parts:
            parts.append("\n")
            offset += 1
        start = offset
        parts.append(text)
        offset += len(text)
        page_info.append((start, offset, page_number))

    text = "".join(parts)
    if not text.strip():
        raise ValueError(f"No extractable text found in {pdf_path.name}")

    return {
        "filename": pdf_path.name,
        "text": text,
        "page_info": page_info,
        "page_count": len(reader.pages),
        "sha256": hashlib.sha256(pdf_path.read_bytes()).hexdigest(),
    }
