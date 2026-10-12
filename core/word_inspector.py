"""Inspects Word document for Track Changes and comments."""

import zipfile
from pathlib import Path
from lxml import etree
from core.models import WordInfo

WORD_SCHEMA_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


def inspect_word(docx_path: str) -> tuple[WordInfo, list[str]]:
    """Inspects a Word (.docx/.doc) document.
    Returns:
        WordInfo: counts of tracked insertions, deletions, and comments.
        list[str]: warning messages generated based on inspection findings.
    """
    path = Path(docx_path)
    warnings: list[str] = []

    # Handle legacy .doc format
    if path.suffix.lower() == ".doc":
        warnings.append("Định dạng .doc cũ. Khuyến nghị lưu sang .docx để có kết quả chính xác nhất.")
        return WordInfo(tracked_insertions=0, tracked_deletions=0, comments=0), warnings

    try:
        with zipfile.ZipFile(docx_path, "r") as zf:
            if "word/document.xml" not in zf.namelist():
                return WordInfo(tracked_insertions=0, tracked_deletions=0, comments=0), warnings

            xml_content = zf.read("word/document.xml")
            tree = etree.fromstring(xml_content)

            ins_nodes = tree.xpath("//w:ins", namespaces=WORD_SCHEMA_NS)
            del_nodes = tree.xpath("//w:del", namespaces=WORD_SCHEMA_NS)
            comment_nodes = tree.xpath("//w:commentReference", namespaces=WORD_SCHEMA_NS)

            tracked_ins = len(ins_nodes)
            tracked_del = len(del_nodes)
            comments_count = len(comment_nodes)

            total_tracked = tracked_ins + tracked_del
            if total_tracked > 0:
                warnings.append(
                    f"File Word còn {total_tracked} thay đổi chưa Accept/Reject (Track Changes). "
                    "Tool so sánh theo bản hiển thị khi đã Accept tất cả."
                )

            if comments_count > 0:
                warnings.append(
                    f"File Word có {comments_count} comment (đã bỏ qua khi so sánh)."
                )

            return (
                WordInfo(
                    tracked_insertions=tracked_ins,
                    tracked_deletions=tracked_del,
                    comments=comments_count,
                ),
                warnings,
            )
    except (zipfile.BadZipFile, Exception) as exc:
        warnings.append(f"Không thể đọc chi tiết cấu trúc Word: {exc}")
        return WordInfo(tracked_insertions=0, tracked_deletions=0, comments=0), warnings


def extract_word_raw_text(docx_path: str) -> str:
    """Extracts all raw text directly from word/document.xml if available."""
    path = Path(docx_path)
    if path.suffix.lower() == ".doc":
        return ""

    try:
        with zipfile.ZipFile(docx_path, "r") as zf:
            if "word/document.xml" not in zf.namelist():
                return ""

            xml_content = zf.read("word/document.xml")
            tree = etree.fromstring(xml_content)
            texts = tree.xpath("//w:t/text()", namespaces=WORD_SCHEMA_NS)
            return " ".join(texts)
    except Exception:
        return ""

