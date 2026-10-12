"""Extracts text tokens and metadata from PDF files using PyMuPDF."""

from pathlib import Path
from typing import Any
import pymupdf

from core.errors import InputFileError, PdfEncryptedError, PdfNoTextError
from core.models import PdfMetadata, Source, Token


def extract_metadata(pdf_path: str) -> PdfMetadata:
    """Extracts PDF metadata from file."""
    path = Path(pdf_path)
    if not path.is_file():
        raise InputFileError(f"File PDF không tồn tại: {pdf_path}")

    try:
        doc = pymupdf.open(str(path))
    except Exception as exc:
        raise InputFileError(f"Không thể mở file PDF: {exc}")

    try:
        if doc.is_encrypted or doc.needs_pass:
            raise PdfEncryptedError()

        meta = doc.metadata or {}
        sig_count = 0
        for page in doc:
            for widget in page.widgets():
                if widget.field_type_string == "Signature":
                    sig_count += 1

        return PdfMetadata(
            format=meta.get("format") or "PDF",
            producer=meta.get("producer") or "",
            creator=meta.get("creator") or "",
            author=meta.get("author") or "",
            creation_date=meta.get("creationDate") or "",
            mod_date=meta.get("modDate") or "",
            page_count=len(doc),
            signature_fields=sig_count,
            encrypted=doc.is_encrypted,
        )
    finally:
        doc.close()


def extract_tokens(pdf_path: str, source: Source) -> tuple[list[Token], dict[int, dict[str, Any]]]:
    """Extracts words as Token objects along with page geometry and signature rects.
    
    Args:
        pdf_path: Path to the PDF file.
        source: Source tag ("word" or "pdf").
        
    Returns:
        tuple containing:
            list[Token]: list of extracted word tokens.
            dict[int, dict]: page metadata mapping page_number (1-based) to
                {"page_no": int, "height": float, "width": float, "signature_rects": list[tuple]}.
    """
    path = Path(pdf_path)
    if not path.is_file():
        raise InputFileError(f"File PDF không tồn tại: {pdf_path}")

    try:
        doc = pymupdf.open(str(path))
    except Exception as exc:
        raise InputFileError(f"Không thể mở file PDF: {exc}")

    try:
        if doc.is_encrypted or doc.needs_pass:
            raise PdfEncryptedError()

        tokens: list[Token] = []
        page_info: dict[int, dict[str, Any]] = {}
        total_text_chars = 0

        for page_idx, page in enumerate(doc):
            page_no = page_idx + 1
            rect = page.rect
            sig_rects: list[tuple[float, float, float, float]] = []

            for widget in page.widgets():
                if widget.field_type_string == "Signature":
                    w_rect = widget.rect
                    sig_rects.append((w_rect.x0, w_rect.y0, w_rect.x1, w_rect.y1))

            page_info[page_no] = {
                "page_no": page_no,
                "height": rect.height,
                "width": rect.width,
                "signature_rects": sig_rects,
            }

            # get_text("words", sort=False) returns (x0, y0, x1, y1, word, block_no, line_no, word_no)
            words = page.get_text("words", sort=False)
            for w in words:
                x0, y0, x1, y1, word_str, block_no, line_no, _ = w
                total_text_chars += len(word_str)
                token = Token(
                    raw=word_str,
                    norm="",
                    page=page_no,
                    bbox=(float(x0), float(y0), float(x1), float(y1)),
                    block_no=int(block_no),
                    line_no=int(line_no),
                    source=source,
                )
                tokens.append(token)

        if total_text_chars < 50:
            raise PdfNoTextError()

        return tokens, page_info

    finally:
        doc.close()
