"""Comparison pipeline orchestrating the end-to-end document comparison flow."""

import hashlib
import os
import shutil
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
import yaml

from core.differ import compute_diffs
from core.errors import InputFileError
from core.extractor import extract_metadata, extract_tokens
from core.models import CompareOptions, CompareResult, FilteredToken
from core.noise_filters import (
    apply_tier2_normalization,
    filter_n2_page_numbers,
    filter_n3_signatures,
    filter_n4_headers_footers,
)
from core.normalizer import docx_to_pdf
from core.word_inspector import extract_word_raw_text, inspect_word

TOOL_VERSION = "1.0.0"
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50MB


def calculate_sha256(filepath: str) -> str:
    """Computes SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def load_config(config_path: str) -> dict:
    """Loads YAML configuration file or returns defaults."""
    from core.resources import get_resource_path

    path = Path(config_path) if config_path else get_resource_path("config/filters.yaml")
    if not path.is_file():
        path = get_resource_path("config/filters.yaml")

    if path.is_file():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception:
            pass
    return {}



def validate_input_files(word_path: str, pdf_path: str) -> None:
    """Validates existence, extensions, and file sizes."""
    w_p = Path(word_path)
    p_p = Path(pdf_path)

    if not w_p.is_file():
        raise InputFileError(f"File Word không tồn tại: {word_path}")
    if not p_p.is_file():
        raise InputFileError(f"File PDF không tồn tại: {pdf_path}")

    if w_p.suffix.lower() not in {".docx", ".doc"}:
        raise InputFileError(f"File Word phải có đuôi .docx hoặc .doc: {word_path}")
    if p_p.suffix.lower() != ".pdf":
        raise InputFileError(f"File PDF phải có đuôi .pdf: {pdf_path}")

    if w_p.stat().st_size > MAX_FILE_SIZE_BYTES:
        raise InputFileError(f"File Word vượt quá giới hạn 50MB ({w_p.stat().st_size} bytes)")
    if p_p.stat().st_size > MAX_FILE_SIZE_BYTES:
        raise InputFileError(f"File PDF vượt quá giới hạn 50MB ({p_p.stat().st_size} bytes)")


def run_compare(
    word_path: str,
    pdf_path: str,
    options: CompareOptions,
    progress_cb: Callable[[int, str], None] | None = None,
) -> CompareResult:
    """Executes the full document comparison pipeline.
    
    Args:
        word_path: Path to the approved Word document.
        pdf_path: Path to the signed/converted PDF document.
        options: Comparison configuration options.
        progress_cb: Optional callback receiving (percent: int, message_vi: str).
        
    Returns:
        CompareResult containing diff items, filtered tokens, metadata, and statistics.
    """
    def report_progress(percent: int, message: str) -> None:
        if progress_cb:
            progress_cb(percent, message)

    report_progress(5, "Đang kiểm tra file đầu vào...")
    validate_input_files(word_path, pdf_path)

    config = load_config(options.config_path)

    report_progress(10, "Đang tính toán mã băm SHA-256...")
    word_sha256 = calculate_sha256(word_path)
    pdf_sha256 = calculate_sha256(pdf_path)

    report_progress(20, "Đang kiểm tra Track Changes và comment trong Word...")
    word_info, word_warnings = inspect_word(word_path)
    word_raw_text = extract_word_raw_text(word_path)
    warnings: list[str] = list(word_warnings)

    tmp_convert_dir = tempfile.mkdtemp(prefix="doc_compare_run_")
    try:
        report_progress(35, "Đang chuyển đổi Word sang PDF tạm thời...")
        word_tmp_pdf = docx_to_pdf(word_path, tmp_convert_dir)

        report_progress(50, "Đang đọc nội dung và metadata PDF...")
        pdf_meta = extract_metadata(pdf_path)

        tokens_word, page_info_word = extract_tokens(word_tmp_pdf, source="word")
        tokens_pdf, page_info_pdf = extract_tokens(pdf_path, source="pdf")

        report_progress(65, "Đang lọc nhiễu tầng 1 (số trang, chữ ký, header/footer)...")
        all_filtered: list[FilteredToken] = []

        # Tầng 1 cho bên Word
        tokens_word, f_w_n2 = filter_n2_page_numbers(tokens_word, config)
        tokens_word, f_w_n3 = filter_n3_signatures(tokens_word, page_info_word, config)
        page_cnt_word = max((t.page for t in tokens_word), default=1)
        tokens_word, f_w_n4 = filter_n4_headers_footers(tokens_word, page_cnt_word, config)
        all_filtered.extend(f_w_n2 + f_w_n3 + f_w_n4)

        # Tầng 1 cho bên PDF
        tokens_pdf, f_p_n2 = filter_n2_page_numbers(tokens_pdf, config)
        tokens_pdf, f_p_n3 = filter_n3_signatures(tokens_pdf, page_info_pdf, config)
        tokens_pdf, f_p_n4 = filter_n4_headers_footers(tokens_pdf, pdf_meta.page_count, config)
        all_filtered.extend(f_p_n2 + f_p_n3 + f_p_n4)

        report_progress(80, "Đang chuẩn hoá văn bản tầng 2 (Unicode, khoảng trắng, ký tự)...")
        tokens_word, f_w_t2 = apply_tier2_normalization(tokens_word, options, config)
        tokens_pdf, f_p_t2 = apply_tier2_normalization(tokens_pdf, options, config)
        all_filtered.extend(f_w_t2 + f_p_t2)

        report_progress(90, "Đang so khớp nội dung và phân loại khác biệt...")
        diffs = compute_diffs(tokens_word, tokens_pdf, config, word_raw_text=word_raw_text)

        report_progress(95, "Đang tổng hợp kết quả so sánh...")
        filter_stats = dict(Counter(f.filter_id for f in all_filtered))

        run_at_iso = datetime.now(timezone.utc).astimezone().isoformat()

        report_progress(100, "Hoàn tất so sánh.")
        return CompareResult(
            word_path=str(Path(word_path).resolve()),
            pdf_path=str(Path(pdf_path).resolve()),
            word_sha256=word_sha256,
            pdf_sha256=pdf_sha256,
            options=options,
            tool_version=TOOL_VERSION,
            run_at=run_at_iso,
            word_info=word_info,
            pdf_meta=pdf_meta,
            diffs=diffs,
            filtered=all_filtered,
            filter_stats=filter_stats,
            warnings=warnings,
        )

    finally:
        shutil.rmtree(tmp_convert_dir, ignore_errors=True)
