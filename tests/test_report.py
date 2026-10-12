"""Tests for HTML report builder and acceptance criteria."""

import hashlib
import re
import tempfile
from pathlib import Path
from core.models import CompareOptions
from core.pipeline import run_compare
from report.builder import build_html_report


def test_html_report_sample01_acceptance():
    fixtures_dir = Path(__file__).parent / "fixtures" / "sample_01"
    word_path = str(fixtures_dir / "approved.docx")
    pdf_path = str(fixtures_dir / "wesign.pdf")

    # Tính toán SHA256 độc lập
    w_sha = hashlib.sha256(open(word_path, "rb").read()).hexdigest()
    p_sha = hashlib.sha256(open(pdf_path, "rb").read()).hexdigest()

    res = run_compare(word_path, pdf_path, CompareOptions())

    with tempfile.TemporaryDirectory() as tmp_dir:
        report_path = Path(tmp_dir) / "test_report.html"
        generated_path = build_html_report(res, str(report_path))
        assert Path(generated_path).is_file()

        content = open(generated_path, "r", encoding="utf-8").read()

        # 1. Bố cục: Tiêu đề
        assert "Báo cáo so sánh hợp đồng Word ↔ PDF" in content

        # 2. SHA-256 khớp chuẩn sha256sum
        assert w_sha in content
        assert p_sha in content

        # 3. Tóm tắt to, rõ
        assert "🔴 4 điểm khác biệt" in content
        assert "🟡 0 có thể là nhiễu" in content

        # 4. Highlight ở mức ký tự: 01 -> 08 chỉ tô 1 và 8
        assert '0<span class="char-del">1</span>' in content
        assert '0<span class="char-ins">8</span>' in content

        # 5. 100% Offline, không CDN hay link http/https bên ngoài
        assert "http://" not in content
        assert "https://" not in content

        # 6. CSS @media print
        assert "@media print" in content
        assert "break-inside: avoid" in content

        # 7. Metadata PDF & Cảnh báo Word
        assert "Aspose.Words" in content or "iText" in content or "PDF 1.7" in content
        assert "2 comment" in content

        # 8. Footer quy chuẩn
        assert "Quyết định cuối cùng thuộc về Legal." in content


def test_cli_output_report_flag():
    import subprocess
    import sys

    fixtures_dir = Path(__file__).parent / "fixtures" / "sample_01"
    word_path = str(fixtures_dir / "approved.docx")
    pdf_path = str(fixtures_dir / "wesign.pdf")

    with tempfile.TemporaryDirectory() as tmp_dir:
        out_html = Path(tmp_dir) / "out.html"
        cmd = [
            sys.executable,
            "cli.py",
            word_path,
            pdf_path,
            "-o",
            str(out_html),
        ]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        assert proc.returncode == 0
        assert out_html.is_file()
        assert out_html.stat().st_size > 1000
