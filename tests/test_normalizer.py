"""Unit tests for Word to PDF normalizer."""

import tempfile
from pathlib import Path
from core.extractor import extract_tokens
from core.normalizer import docx_to_pdf


def test_docx_to_pdf_conversion_and_no_comments():
    docx_path = Path(__file__).parent / "fixtures" / "sample_01" / "approved.docx"
    with tempfile.TemporaryDirectory() as tmp_dir:
        pdf_path = docx_to_pdf(str(docx_path), tmp_dir)
        assert Path(pdf_path).is_file()
        assert Path(pdf_path).stat().st_size > 0

        # N1 Test: Comment text does NOT get printed to PDF
        tokens, _ = extract_tokens(pdf_path, source="word")
        assert not any("Em đề xuất bổ sung nội dung này" in t.raw for t in tokens)
