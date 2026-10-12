"""Command-line interface (CLI) for DocCompare."""

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from core.errors import DocCompareError
from core.models import CompareOptions
from core.pipeline import run_compare


def build_parser() -> argparse.ArgumentParser:
    """Builds CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="DocCompare: Công cụ so sánh hợp đồng Word (đã duyệt) và PDF (WeSign ký)"
    )
    parser.add_argument("word", help="Đường dẫn tới file Word (.docx / .doc)")
    parser.add_argument("pdf", help="Đường dẫn tới file PDF (.pdf)")
    parser.add_argument(
        "--case-sensitive",
        action="store_true",
        help="Bật phân biệt chữ hoa/thường (mặc định tắt)",
    )
    parser.add_argument(
        "-c",
        "--config",
        default="config/filters.yaml",
        help="Đường dẫn file cấu hình bộ lọc (mặc định config/filters.yaml)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Xuất kết quả chi tiết dưới dạng JSON ra stdout",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Đường dẫn file báo cáo đầu ra (HTML)",
    )
    return parser


def format_console_summary(res) -> str:
    """Formats human-readable summary for console output."""
    lines = []
    lines.append("=" * 60)
    lines.append("           BÁO CÁO SO SÁNH HỢP ĐỒNG WORD ↔ PDF")
    lines.append("=" * 60)
    lines.append(f"File Word: {Path(res.word_path).name} (SHA-256: {res.word_sha256[:12]}...)")
    lines.append(f"File PDF:  {Path(res.pdf_path).name} (SHA-256: {res.pdf_sha256[:12]}...)")
    lines.append(f"Thời gian: {res.run_at}")
    lines.append(f"Phân biệt hoa/thường: {'BẬT' if res.options.case_sensitive else 'TẮT'}")
    lines.append("-" * 60)

    diffs_red = [d for d in res.diffs if d.category == "diff"]
    diffs_yellow = [d for d in res.diffs if d.category == "maybe_noise"]
    total_filtered = len(res.filtered)

    lines.append(f"🔴 Khác biệt nội dung (diff):       {len(diffs_red)}")
    lines.append(f"🟡 Nghi vấn nhiễu (maybe_noise):    {len(diffs_yellow)}")
    lines.append(f"⚪ Token đã lọc nhiễu (filtered):   {total_filtered}")

    if res.warnings:
        lines.append("-" * 60)
        lines.append("CẢNH BÁO:")
        for w in res.warnings:
            lines.append(f"  ⚠️  {w}")

    if diffs_red:
        lines.append("-" * 60)
        lines.append("DANH SÁCH KHÁC BIỆT CHÍNH (🔴):")
        for d in diffs_red:
            w_disp = d.word_text if d.word_text else "(không có)"
            p_disp = d.pdf_text if d.pdf_text else "(không có)"
            lines.append(f"  #{d.id} [{d.clause}] (Trang W:{d.page_word}/P:{d.page_pdf})")
            lines.append(f"     - Word: {w_disp}")
            lines.append(f"     + PDF:  {p_disp}")
            if d.context_before or d.context_after:
                lines.append(f"     * Ngữ cảnh: ...{d.context_before} [...] {d.context_after}...")

    if diffs_yellow:
        lines.append("-" * 60)
        lines.append("DANH SÁCH NGHI VẤN NHIỄU (🟡):")
        for d in diffs_yellow:
            lines.append(f"  #{d.id} [{d.clause}] {d.note}")
            lines.append(f"     - Word: {d.word_text}")
            lines.append(f"     + PDF:  {d.pdf_text}")

    lines.append("=" * 60)
    return "\n".join(lines)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    options = CompareOptions(
        case_sensitive=args.case_sensitive,
        config_path=args.config,
    )

    try:
        result = run_compare(args.word, args.pdf, options)
    except DocCompareError as err:
        print(f"LỖI: {err.message_vi}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"LỖI KHÔNG XÁC ĐỊNH: {exc}", file=sys.stderr)
        return 2

    if args.output:
        from report.builder import build_html_report
        html_path = build_html_report(result, args.output)
        if not args.json:
            print(f"\n[Báo cáo HTML đã tạo]: {html_path}")

    if args.json:
        data = asdict(result)
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(format_console_summary(result))

    return 0


if __name__ == "__main__":
    sys.exit(main())
