"""Unit tests for PDF extractor."""

from pathlib import Path
from core.extractor import extract_metadata, extract_tokens


def test_extract_wesign_pdf():
    pdf_path = Path(__file__).parent / "fixtures" / "sample_01" / "wesign.pdf"
    meta = extract_metadata(str(pdf_path))
    assert meta.page_count == 13
    assert meta.signature_fields == 2
    assert "PDF 1.7" in meta.format

    tokens, page_info = extract_tokens(str(pdf_path), source="pdf")
    assert len(tokens) > 500
    assert 13 in page_info
    assert len(page_info[13]["signature_rects"]) == 2
