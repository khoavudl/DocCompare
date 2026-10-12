"""Diff engine comparing token streams, clustering diff items, and resolving clauses."""

import difflib
import re
from typing import Any

from core.models import DiffItem, Token
from core.noise_filters import apply_n10_reorder, apply_n0_word_cross_check


def find_clause(tokens: list[Token], start_idx: int) -> str:
    """Finds the nearest clause/article heading by scanning backwards from start_idx.
    
    Rules:
    - Match section numbering like '2.2' or '5.1.' -> 'Điều 2.2'
    - Match 'ĐIỀU' + number -> 'Điều X'
    - If neither is found before reaching index 0 -> 'Phần mở đầu'
    """
    if not tokens:
        return "Phần mở đầu"

    idx = min(start_idx, len(tokens) - 1)
    clause_section_pat = re.compile(r"^(\d+\.\d+)\.?$")
    dieu_single_pat = re.compile(r"^[Đđ][Iii][Êê][Uu]\s*(\d+)", re.IGNORECASE)

    for i in range(idx, -1, -1):
        tok_str = tokens[i].raw.strip()
        tok_cf = tok_str.casefold()

        # Kiểm tra dạng số mục: 2.2, 5.1.
        m_sec = clause_section_pat.match(tok_str)
        if m_sec:
            sec_num = m_sec.group(1)
            return f"Điều {sec_num}"

        # Kiểm tra token có chứa chữ Điều + số: "Điều 2" hoặc "ĐIỀU 1"
        m_dieu = re.match(r"^điều\s*(\d+)", tok_cf)
        if m_dieu:
            dieu_num = m_dieu.group(1)
            return f"Điều {dieu_num}"

        # Trường hợp token là "Điều" và token liền sau là số
        if tok_cf == "điều":
            if i + 1 < len(tokens):
                next_tok = tokens[i + 1].raw.strip()
                m_next = re.match(r"^(\d+)", next_tok)
                if m_next:
                    return f"Điều {m_next.group(1)}"

    return "Phần mở đầu"


def get_context_text(
    tokens: list[Token],
    start_idx: int,
    end_idx: int,
    context_tokens: int,
) -> tuple[str, str]:
    """Retrieves context_before and context_after strings using raw token text."""
    if not tokens:
        return "", ""

    before_start = max(0, start_idx - context_tokens)
    before_tokens = tokens[before_start:start_idx]
    context_before = " ".join(t.raw for t in before_tokens)

    after_end = min(len(tokens), end_idx + context_tokens)
    after_tokens = tokens[end_idx:after_end]
    context_after = " ".join(t.raw for t in after_tokens)

    return context_before, context_after


def compute_diffs(
    tokens_word: list[Token],
    tokens_pdf: list[Token],
    config: dict[str, Any],
    word_raw_text: str = "",
) -> list[DiffItem]:
    """Compares tokens_word with tokens_pdf and generates clusterized DiffItems.
    
    Steps:
    1. Extract norm text streams
    2. SequenceMatcher with autojunk=False
    3. Filter out 'equal' opcodes -> raw diffs
    4. Merge nearby diffs within merge_gap_tokens
    5. Resolve context, clause, pages
    6. Apply N10 reorder detection
    7. Apply N0 ground-truth Word cross check
    8. Assign sequential 1-based IDs
    """
    diff_cfg = config.get("diff", {})
    merge_gap = int(diff_cfg.get("merge_gap_tokens", 2))
    context_count = int(diff_cfg.get("context_tokens", 6))

    a_norm = [t.norm for t in tokens_word]
    b_norm = [t.norm for t in tokens_pdf]

    matcher = difflib.SequenceMatcher(None, a_norm, b_norm, autojunk=False)
    opcodes = matcher.get_opcodes()

    # Chỉ giữ các opcode khác biệt
    raw_diffs: list[tuple[str, int, int, int, int]] = []
    for tag, i1, i2, j1, j2 in opcodes:
        if tag != "equal":
            raw_diffs.append((tag, i1, i2, j1, j2))

    if not raw_diffs:
        return []

    # 4. Gộp các diff liền kề nếu khoảng cách equal <= merge_gap_tokens
    merged_diffs: list[list[int]] = []  # [i1, i2, j1, j2]
    for tag, i1, i2, j1, j2 in raw_diffs:
        if not merged_diffs:
            merged_diffs.append([i1, i2, j1, j2])
        else:
            prev = merged_diffs[-1]
            gap_word = i1 - prev[1]
            gap_pdf = j1 - prev[3]

            if 0 <= gap_word <= merge_gap and 0 <= gap_pdf <= merge_gap:
                # Gộp diff
                prev[1] = i2
                prev[3] = j2
            else:
                merged_diffs.append([i1, i2, j1, j2])

    # Chuyển đổi thành DiffItem
    diff_items: list[DiffItem] = []

    for i1, i2, j1, j2 in merged_diffs:
        w_slice = tokens_word[i1:i2]
        p_slice = tokens_pdf[j1:j2]

        word_text = " ".join(t.raw for t in w_slice)
        pdf_text = " ".join(t.raw for t in p_slice)

        if not w_slice and p_slice:
            kind = "insert"
        elif w_slice and not p_slice:
            kind = "delete"
        else:
            kind = "replace"

        # Ngữ cảnh lấy từ phía Word (nếu có) hoặc từ phía PDF nếu là insert
        if w_slice:
            ctx_before, ctx_after = get_context_text(tokens_word, i1, i2, context_count)
            clause = find_clause(tokens_word, i1)
        else:
            ctx_before, ctx_after = get_context_text(tokens_pdf, j1, j2, context_count)
            clause = find_clause(tokens_pdf, j1)

        page_word = w_slice[0].page if w_slice else None
        page_pdf = p_slice[0].page if p_slice else None

        item = DiffItem(
            id=0,  # Sẽ gán sau khi sắp xếp
            kind=kind,
            word_text=word_text,
            pdf_text=pdf_text,
            context_before=ctx_before,
            context_after=ctx_after,
            clause=clause,
            page_word=page_word,
            page_pdf=page_pdf,
            category="diff",
            note="",
        )
        diff_items.append(item)

    # 6. Chạy bộ lọc N10
    diff_items = apply_n10_reorder(diff_items)

    # 7. Chạy N0 Ground-truth cross-check với Word XML
    if word_raw_text:
        diff_items = apply_n0_word_cross_check(diff_items, word_raw_text)

    # 8. Đánh id tăng dần theo thứ tự xuất hiện
    for idx, item in enumerate(diff_items, start=1):
        item.id = idx

    return diff_items

