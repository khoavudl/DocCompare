"""Unit tests for noise filters N2 through N11."""

import re
import yaml
from pathlib import Path
from core.models import CompareOptions, DiffItem, Token
from core.noise_filters import (
    apply_n10_reorder,
    apply_tier2_normalization,
    filter_n2_page_numbers,
    filter_n3_signatures,
    filter_n4_headers_footers,
    normalize_vietnamese_text,
)


def load_test_config() -> dict:
    cfg_path = Path(__file__).parent.parent / "config" / "filters.yaml"
    with open(cfg_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# --- N2: Page Numbers ---
def test_n2_page_number_should_filter():
    config = load_test_config()
    tokens = [
        Token(raw="13", page=13, block_no=0, line_no=0),
    ]
    kept, filtered = filter_n2_page_numbers(tokens, config)
    assert len(kept) == 0
    assert len(filtered) == 1
    assert filtered[0].filter_id == "N2"


def test_n2_page_number_should_not_filter_when_number_differs():
    config = load_test_config()
    # Token "5" ở trang 13 (không khớp số trang)
    tokens = [
        Token(raw="5", page=13, block_no=0, line_no=0),
    ]
    kept, filtered = filter_n2_page_numbers(tokens, config)
    assert len(kept) == 1
    assert len(filtered) == 0


def test_n2_page_number_should_not_filter_when_multiple_tokens_in_line():
    config = load_test_config()
    tokens = [
        Token(raw="Điều", page=1, block_no=0, line_no=0),
        Token(raw="1", page=1, block_no=0, line_no=0),
    ]
    kept, filtered = filter_n2_page_numbers(tokens, config)
    assert len(kept) == 2
    assert len(filtered) == 0


# --- N3: Digital Signatures ---
def test_n3_signature_should_filter_inside_rect():
    config = load_test_config()
    page_info = {
        13: {"signature_rects": [(100.0, 100.0, 200.0, 200.0)]}
    }
    tokens = [
        Token(raw="SignedBy", page=13, bbox=(120.0, 120.0, 180.0, 180.0)),
    ]
    kept, filtered = filter_n3_signatures(tokens, page_info, config)
    assert len(kept) == 0
    assert len(filtered) == 1
    assert filtered[0].filter_id == "N3"


def test_n3_signature_should_not_filter_outside_rect():
    config = load_test_config()
    page_info = {
        13: {"signature_rects": [(100.0, 100.0, 200.0, 200.0)]}
    }
    tokens = [
        Token(raw="ContractText", page=13, bbox=(10.0, 10.0, 50.0, 50.0)),
    ]
    kept, filtered = filter_n3_signatures(tokens, page_info, config)
    assert len(kept) == 1
    assert len(filtered) == 0


# --- N4: Headers/Footers ---
def test_n4_header_footer_should_filter():
    config = load_test_config()
    # 5 trang, header "HỢP ĐỒNG KINH TẾ" xuất hiện ở y0=30 trên cả 5 trang (> 60%)
    tokens = []
    for p in range(1, 6):
        tokens.append(Token(raw="HỢP ĐỒNG KINH TẾ", page=p, bbox=(100.0, 30.0, 300.0, 45.0), block_no=0, line_no=0))
        tokens.append(Token(raw=f"Nội dung trang {p}", page=p, bbox=(100.0, 100.0, 300.0, 120.0), block_no=1, line_no=0))

    kept, filtered = filter_n4_headers_footers(tokens, page_count=5, config=config)
    assert len(filtered) == 5
    assert all(f.filter_id == "N4" for f in filtered)
    assert all("HỢP ĐỒNG KINH TẾ" in f.token.raw for f in filtered)


def test_n4_header_footer_should_not_filter_when_not_frequent():
    config = load_test_config()
    # Chỉ xuất hiện ở trang 1 trên tổng 5 trang (< 60%)
    tokens = [
        Token(raw="Tiêu đề một lần", page=1, bbox=(100.0, 30.0, 300.0, 45.0), block_no=0, line_no=0),
        Token(raw="Nội dung", page=1, bbox=(100.0, 100.0, 300.0, 120.0), block_no=1, line_no=0),
    ]
    kept, filtered = filter_n4_headers_footers(tokens, page_count=5, config=config)
    assert len(kept) == 2
    assert len(filtered) == 0


# --- N5: Unicode tiếng Việt ---
def test_n5_vietnamese_unicode_examples():
    # Acceptance criteria: "đê xuâ t" -> "đề xuất", "gô m" -> "gồm"
    assert normalize_vietnamese_text("đê xuâ t") == "đề xuất"
    assert normalize_vietnamese_text("gô m") == "gồm"


def test_n5_combining_mark_merging():
    config = load_test_config()
    options = CompareOptions()
    # Token "ê" và token combining grave "\u0300"
    tokens = [
        Token(raw="đ", norm="đ"),
        Token(raw="e", norm="e"),
        Token(raw="\u0302\u0300", norm="\u0302\u0300"),  # combining circumflex + grave
    ]
    kept, filtered = apply_tier2_normalization(tokens, options, config)
    assert len(filtered) == 1
    assert filtered[0].filter_id == "N5"


# --- N6: Khoảng trắng & Ngắt dòng ---
def test_n6_hyphen_joining():
    config = load_test_config()
    options = CompareOptions()
    tokens = [
        Token(raw="chuyển-", page=1, line_no=1, bbox=(10, 10, 50, 20)),
        Token(raw="khoản", page=1, line_no=2, bbox=(10, 25, 60, 35)),
    ]
    kept, filtered = apply_tier2_normalization(tokens, options, config)
    assert len(kept) == 1
    assert "chuyểnkhoản" in kept[0].norm
    assert len(filtered) == 1
    assert filtered[0].filter_id == "N6"


def test_n6_hyphen_bullet_not_joined():
    config = load_test_config()
    options = CompareOptions()
    tokens = [
        Token(raw="-", page=1, line_no=1),
        Token(raw="điều", page=1, line_no=2),
    ]
    kept, filtered = apply_tier2_normalization(tokens, options, config)
    assert len(kept) == 2


# --- N8: Ký tự tương đương ---
def test_n8_no_letters_or_digits_in_char_map():
    """Acceptance criteria: Bảng thay thế không có chữ cái hay chữ số nào."""
    config = load_test_config()
    char_map = config["filters"]["N8_char_map"]["map"]

    for src_char, target_char in char_map.items():
        # Source character không được là chữ cái hoặc chữ số
        assert not re.match(r"^[a-zA-Z0-9]$", src_char), f"Source '{src_char}' contains ASCII letter/digit"
        # Target character không được là chữ số
        assert not re.search(r"\d", target_char), f"Target '{target_char}' contains digits"
        # Nếu target có chữ cái thì chỉ được phép là ligature fi, fl
        letters = re.findall(r"[a-zA-Z]", target_char)
        if letters:
            assert target_char in {"fi", "fl"}, f"Unexpected letters in target '{target_char}'"


def test_n8_smart_quotes_and_dashes_replaced():
    config = load_test_config()
    options = CompareOptions(case_sensitive=True)
    tokens = [
        Token(raw="“Hợp–đồng”"),
    ]
    kept, _ = apply_tier2_normalization(tokens, options, config)
    assert kept[0].norm == '"Hợp-đồng"'


# --- N9: Chữ hoa/thường ---
def test_n9_case_sensitivity():
    config = load_test_config()

    # Case 1: Tắt case_sensitive (mặc định) -> cùng norm
    opt_off = CompareOptions(case_sensitive=False)
    t1 = Token(raw="SONI")
    t2 = Token(raw="Soni")
    res_off, _ = apply_tier2_normalization([t1, t2], opt_off, config)
    assert res_off[0].norm == res_off[1].norm == "soni"

    # Case 2: Bật case_sensitive -> khác norm
    opt_on = CompareOptions(case_sensitive=True)
    t3 = Token(raw="SONI")
    t4 = Token(raw="Soni")
    res_on, _ = apply_tier2_normalization([t3, t4], opt_on, config)
    assert res_on[0].norm != res_on[1].norm


# --- N10: Lệch thứ tự đọc ---
def test_n10_reorder():
    diffs = [
        DiffItem(
            id=1,
            kind="delete",
            word_text="Điều khoản phụ",
            pdf_text="",
            context_before="",
            context_after="",
            clause="Điều 1",
            page_word=1,
            page_pdf=None,
        ),
        DiffItem(
            id=2,
            kind="insert",
            word_text="",
            pdf_text="Điều khoản phụ",
            context_before="",
            context_after="",
            clause="Điều 5",
            page_word=None,
            page_pdf=3,
        ),
    ]
    processed = apply_n10_reorder(diffs)
    assert processed[0].category == "maybe_noise"
    assert "N10" in processed[0].note
    assert processed[1].category == "maybe_noise"
    assert "N10" in processed[1].note


# --- N11: Token rỗng ---
def test_n11_empty_token_filtered():
    config = load_test_config()
    options = CompareOptions()
    tokens = [
        Token(raw="\u200b"),  # Zero-width space
        Token(raw="   "),
        Token(raw="Hợp đồng"),
    ]
    kept, filtered = apply_tier2_normalization(tokens, options, config)
    assert len(kept) == 1
    assert kept[0].norm == "hợp đồng"
    assert len(filtered) >= 1
