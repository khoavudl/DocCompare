"""Unit tests for differ engine."""

from core.differ import compute_diffs, find_clause, get_context_text
from core.models import Token


def test_find_clause_section_numbering():
    tokens = [
        Token(raw="ĐIỀU"),
        Token(raw="1"),
        Token(raw="Định"),
        Token(raw="nghĩa"),
        Token(raw="1.1"),
        Token(raw="Hợp"),
        Token(raw="đồng"),
    ]
    # Dò từ vị trí "Hợp đồng" (index 5) -> "Điều 1.1"
    assert find_clause(tokens, 5) == "Điều 1.1"


def test_find_clause_article_heading():
    tokens = [
        Token(raw="ĐIỀU"),
        Token(raw="2"),
        Token(raw="Giá"),
        Token(raw="trị"),
    ]
    assert find_clause(tokens, 3) == "Điều 2"


def test_find_clause_preamble():
    tokens = [
        Token(raw="CỘNG"),
        Token(raw="HÒA"),
        Token(raw="XÃ"),
        Token(raw="HỘI"),
    ]
    assert find_clause(tokens, 3) == "Phần mở đầu"


def test_get_context_text():
    tokens = [Token(raw=f"w{i}") for i in range(10)]
    # diff ở index 4..6
    ctx_before, ctx_after = get_context_text(tokens, start_idx=4, end_idx=6, context_tokens=3)
    assert ctx_before == "w1 w2 w3"
    assert ctx_after == "w6 w7 w8"


def test_compute_diffs_merge_gap():
    # Hai thay đổi cách nhau 1 token equal
    tokens_w = [
        Token(raw="A", norm="a"),
        Token(raw="equal1", norm="eq1"),
        Token(raw="B", norm="b"),
    ]
    tokens_p = [
        Token(raw="X", norm="x"),
        Token(raw="equal1", norm="eq1"),
        Token(raw="Y", norm="y"),
    ]
    config = {
        "diff": {"merge_gap_tokens": 2, "context_tokens": 2}
    }
    diffs = compute_diffs(tokens_w, tokens_p, config)
    # Vì khoảng cách equal1 chỉ là 1 token (<= merge_gap=2) nên được gộp thành 1 DiffItem
    assert len(diffs) == 1
    assert diffs[0].word_text == "A equal1 B"
    assert diffs[0].pdf_text == "X equal1 Y"


def test_n0_converter_cross_check_marks_maybe_noise():
    # Giả lập tình huống Word PDF tạm rớt mất chữ 'B' giữa 'Bên' và 'phải'
    tokens_w = [
        Token(raw="Bên", norm="bên"),
        Token(raw="phải", norm="phải"),
    ]
    tokens_p = [
        Token(raw="Bên", norm="bên"),
        Token(raw="B", norm="b"),
        Token(raw="phải", norm="phải"),
    ]
    config = {"diff": {"merge_gap_tokens": 0, "context_tokens": 2}}

    # Bản Word XML thực tế CÓ chữ "B"
    word_raw_xml = "quyền và nghĩa vụ của Bên B phải tuân thủ"
    diffs = compute_diffs(tokens_w, tokens_p, config, word_raw_text=word_raw_xml)

    assert len(diffs) == 1
    item = diffs[0]
    assert item.kind == "insert"
    assert item.pdf_text == "B"
    assert item.category == "maybe_noise"
    assert "N0:" in item.note

