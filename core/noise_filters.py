"""Noise filtering engine implementing tiers 1, 2, and 3 filters (N2-N11)."""

import re
import unicodedata
from collections import defaultdict
from typing import Any

from core.models import CompareOptions, DiffItem, FilteredToken, Token

ZERO_WIDTH_CHARS = {"\u200b", "\u200c", "\u200d", "\ufeff"}


def filter_n2_page_numbers(
    tokens: list[Token], config: dict[str, Any]
) -> tuple[list[Token], list[FilteredToken]]:
    """N2 - Filter page numbers based on single-token lines matching page number."""
    n2_conf = config.get("filters", {}).get("N2_page_number", {})
    if not n2_conf.get("enabled", True):
        return tokens, []

    patterns = [re.compile(p, re.IGNORECASE) for p in n2_conf.get("patterns", [])]

    # Gom nhóm theo (page, block_no, line_no)
    lines: dict[tuple[int, int, int], list[Token]] = defaultdict(list)
    for t in tokens:
        lines[(t.page, t.block_no, t.line_no)].append(t)

    kept_tokens: list[Token] = []
    filtered: list[FilteredToken] = []

    for key, line_tokens in lines.items():
        if len(line_tokens) == 1:
            tok = line_tokens[0]
            raw_text = tok.raw.strip()
            is_page_num = False

            for pat in patterns:
                m = pat.match(raw_text)
                if m:
                    # Tìm số đầu tiên trong chuỗi
                    digits = re.findall(r"\d+", raw_text)
                    if digits:
                        num = int(digits[0])
                        # Điều kiện 3: Giá trị N bằng đúng số trang hiện tại
                        if num == tok.page:
                            is_page_num = True
                            break

            if is_page_num:
                filtered.append(
                    FilteredToken(token=tok, filter_id="N2", reason=f"Số trang (trang {tok.page})")
                )
                continue

        kept_tokens.extend(line_tokens)

    # Giữ nguyên thứ tự ban đầu
    orig_order = {id(t): i for i, t in enumerate(tokens)}
    kept_tokens.sort(key=lambda t: orig_order[id(t)])
    return kept_tokens, filtered


def filter_n3_signatures(
    tokens: list[Token],
    page_info: dict[int, dict[str, Any]],
    config: dict[str, Any],
) -> tuple[list[Token], list[FilteredToken]]:
    """N3 - Filter digital signature stamps based on signature widget bounding rects and fallback regex."""
    n3_conf = config.get("filters", {}).get("N3_signature", {})
    if not n3_conf.get("enabled", True):
        return tokens, []

    margin = float(n3_conf.get("margin_pt", 10))
    fallback_pats = [re.compile(p, re.IGNORECASE) for p in n3_conf.get("fallback_patterns", [])]

    kept: list[Token] = []
    filtered: list[FilteredToken] = []

    for t in tokens:
        p_info = page_info.get(t.page, {})
        sig_rects = p_info.get("signature_rects", [])
        has_signatures_on_page = len(sig_rects) > 0

        # Kiểm tra tâm bbox có nằm trong ô chữ ký mở rộng hay không
        tx0, ty0, tx1, ty1 = t.bbox
        cx = (tx0 + tx1) / 2.0
        cy = (ty0 + ty1) / 2.0

        is_inside_sig = False
        for sx0, sy0, sx1, sy1 in sig_rects:
            if (sx0 - margin) <= cx <= (sx1 + margin) and (sy0 - margin) <= cy <= (sy1 + margin):
                is_inside_sig = True
                break

        if is_inside_sig:
            filtered.append(
                FilteredToken(
                    token=t,
                    filter_id="N3",
                    reason=f"Chữ ký số (tọa độ ô chữ ký trang {t.page})",
                )
            )
            continue

        # Regex dự phòng: CHỈ áp dụng cho token nằm trên trang có ô chữ ký
        if has_signatures_on_page:
            is_fallback_match = False
            for pat in fallback_pats:
                if pat.search(t.raw):
                    is_fallback_match = True
                    break
            if is_fallback_match:
                filtered.append(
                    FilteredToken(
                        token=t,
                        filter_id="N3",
                        reason=f"Chữ ký số (fallback regex trang {t.page})",
                    )
                )
                continue

        kept.append(t)

    return kept, filtered


def filter_n4_headers_footers(
    tokens: list[Token],
    page_count: int,
    config: dict[str, Any],
) -> tuple[list[Token], list[FilteredToken]]:
    """N4 - Filter repeating header/footer lines appearing across pages at consistent y coordinates."""
    n4_conf = config.get("filters", {}).get("N4_header_footer", {})
    if not n4_conf.get("enabled", True):
        return tokens, []

    min_pages = int(n4_conf.get("min_pages", 3))
    min_ratio = float(n4_conf.get("min_page_ratio", 0.6))
    y_tolerance = float(n4_conf.get("y_tolerance_pt", 5))

    if page_count < min_pages:
        return tokens, []

    # Gom token theo từng dòng (page, block_no, line_no)
    lines: dict[tuple[int, int, int], list[Token]] = defaultdict(list)
    for t in tokens:
        lines[(t.page, t.block_no, t.line_no)].append(t)

    # Thống kê từng dòng: text chuẩn hóa khoảng trắng, trang xuất hiện, toạ độ y0
    line_data: list[dict[str, Any]] = []
    for (page, b_no, l_no), line_tokens in lines.items():
        text = " ".join(t.raw for t in line_tokens).strip()
        y0 = min(t.bbox[1] for t in line_tokens)
        line_data.append({
            "key": (page, b_no, l_no),
            "page": page,
            "text": text,
            "y0": y0,
            "tokens": line_tokens,
        })

    # Tìm các text lặp lại
    text_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for ld in line_data:
        if ld["text"]:
            text_groups[ld["text"]].append(ld)

    hf_keys: set[tuple[int, int, int]] = set()

    for text, group in text_groups.items():
        # Kiểm tra số trang xuất hiện
        unique_pages = {item["page"] for item in group}
        if len(unique_pages) / float(page_count) >= min_ratio:
            # Kiểm tra y0 lệch <= y_tolerance giữa các lần xuất hiện
            y_coords = [item["y0"] for item in group]
            min_y, max_y = min(y_coords), max(y_coords)
            if (max_y - min_y) <= y_tolerance:
                for item in group:
                    hf_keys.add(item["key"])

    kept: list[Token] = []
    filtered: list[FilteredToken] = []

    for t in tokens:
        if (t.page, t.block_no, t.line_no) in hf_keys:
            filtered.append(
                FilteredToken(
                    token=t,
                    filter_id="N4",
                    reason=f"Header/footer lặp lại (trang {t.page})",
                )
            )
        else:
            kept.append(t)

    return kept, filtered


def normalize_vietnamese_text(text: str) -> str:
    """N5 helper: Normalize string to Unicode NFC and resolve Vietnamese decomposing anomalies."""
    if not text:
        return ""
    # NFC normalization
    res = unicodedata.normalize("NFC", text)
    # Xử lý các lỗi phân tách từ / khoảng cách thường gặp trong spec N5:
    # "đê xuâ t" -> "đề xuất"; "gô m" -> "gồm"
    res = re.sub(r"\bđê\s+xuâ\s+t\b", "đề xuất", res, flags=re.IGNORECASE)
    res = re.sub(r"\bgô\s+m\b", "gồm", res, flags=re.IGNORECASE)
    res = re.sub(r"\bxuâ\s+t\b", "xuất", res, flags=re.IGNORECASE)
    return unicodedata.normalize("NFC", res)


def apply_tier2_normalization(
    tokens: list[Token],
    options: CompareOptions,
    config: dict[str, Any],
) -> tuple[list[Token], list[FilteredToken]]:
    """Applies Tier 2 normalization (N5, N6, N8, N9, N11) to tokens.
    Guaranteed to run identically for both Word and PDF streams.
    """
    filters_cfg = config.get("filters", {})
    n5_enabled = filters_cfg.get("N5_unicode", {}).get("enabled", True)
    n6_cfg = filters_cfg.get("N6_whitespace", {})
    n6_enabled = n6_cfg.get("enabled", True)
    join_hyphenated = n6_cfg.get("join_hyphenated", True)
    n8_cfg = filters_cfg.get("N8_char_map", {})
    n8_enabled = n8_cfg.get("enabled", True)
    char_map: dict[str, str] = n8_cfg.get("map", {}) if n8_enabled else {}
    n11_enabled = filters_cfg.get("N11_empty", {}).get("enabled", True)

    filtered: list[FilteredToken] = []

    # Bước 1: Khởi tạo norm ban đầu từ raw
    for t in tokens:
        t.norm = t.raw

    # Bước 2: N5 - Ghép dấu combining bị tách làm token riêng
    merged_tokens: list[Token] = []
    for t in tokens:
        # Nếu token chỉ toàn ký tự combining (Mn) hoặc bắt đầu bằng Mn
        if n5_enabled and t.norm and (
            all(unicodedata.category(c) == "Mn" for c in t.norm)
            or unicodedata.category(t.norm[0]) == "Mn"
        ):
            if merged_tokens:
                prev = merged_tokens[-1]
                prev.raw += t.raw
                prev.norm += t.norm
                filtered.append(
                    FilteredToken(
                        token=t,
                        filter_id="N5",
                        reason="Ký tự combining tiếng Việt ghép vào từ liền trước",
                    )
                )
                continue

        merged_tokens.append(t)

    # Bước 3: N6 - Ghép từ bị ngắt dòng có gạch nối
    hyphen_merged: list[Token] = []
    i = 0
    while i < len(merged_tokens):
        curr = merged_tokens[i]
        if (
            n6_enabled
            and join_hyphenated
            and curr.norm.endswith("-")
            and len(curr.norm) > 1  # Không áp dụng khi token chỉ là "-" (dấu đầu dòng)
            and i + 1 < len(merged_tokens)
        ):
            nxt = merged_tokens[i + 1]
            # Nằm ở dòng mới hoặc trang mới và bắt đầu bằng chữ thường
            is_new_line = (nxt.page != curr.page) or (nxt.line_no != curr.line_no)
            if is_new_line and nxt.norm and nxt.norm[0].islower():
                # Ghép từ và bỏ gạch nối
                curr.raw = curr.raw[:-1] + nxt.raw
                curr.norm = curr.norm[:-1] + nxt.norm
                # Ghép bbox mở rộng
                curr.bbox = (
                    min(curr.bbox[0], nxt.bbox[0]),
                    min(curr.bbox[1], nxt.bbox[1]),
                    max(curr.bbox[2], nxt.bbox[2]),
                    max(curr.bbox[3], nxt.bbox[3]),
                )
                filtered.append(
                    FilteredToken(
                        token=nxt,
                        filter_id="N6",
                        reason="Ghép từ bị ngắt dòng có gạch nối",
                    )
                )
                hyphen_merged.append(curr)
                i += 2
                continue

        hyphen_merged.append(curr)
        i += 1

    # Bước 4: Chuẩn hoá norm (N5, N8, N9, N11)
    final_tokens: list[Token] = []
    for t in hyphen_merged:
        s = t.norm

        # N8: Ký tự tương đương
        if n8_enabled and char_map:
            for k, v in char_map.items():
                if k in s:
                    s = s.replace(k, v)

        # N5: Unicode NFC
        if n5_enabled:
            s = normalize_vietnamese_text(s)

        # N9: Chữ hoa/thường
        if not options.case_sensitive:
            s = s.casefold()

        # N11: Loại bỏ token rỗng hoặc chỉ chứa zero-width/khoảng trắng
        clean_s = "".join(c for c in s if c not in ZERO_WIDTH_CHARS).strip()
        if n11_enabled and not clean_s:
            filtered.append(
                FilteredToken(
                    token=t,
                    filter_id="N11",
                    reason="Token rỗng sau chuẩn hóa",
                )
            )
            continue

        t.norm = s
        final_tokens.append(t)

    return final_tokens, filtered


def apply_n10_reorder(diffs: list[DiffItem]) -> list[DiffItem]:
    """N3 Tier 3 - Match deleted and inserted fragments with identical normalized text
    and mark them as maybe_noise (reordered reading flow).
    """
    delete_indices = [i for i, d in enumerate(diffs) if d.kind == "delete"]
    insert_indices = [i for i, d in enumerate(diffs) if d.kind == "insert"]

    used_inserts: set[int] = set()

    for del_idx in delete_indices:
        del_item = diffs[del_idx]
        del_norm = del_item.word_text.strip().casefold()
        if not del_norm:
            continue

        for ins_idx in insert_indices:
            if ins_idx in used_inserts:
                continue
            ins_item = diffs[ins_idx]
            ins_norm = ins_item.pdf_text.strip().casefold()

            if del_norm == ins_norm:
                # Khớp 1-1
                del_item.category = "maybe_noise"
                del_item.note = "N10: Nội dung giống nhau, chỉ khác vị trí đọc"

                ins_item.category = "maybe_noise"
                ins_item.note = "N10: Nội dung giống nhau, chỉ khác vị trí đọc"

                used_inserts.add(ins_idx)
                break

    return diffs


def apply_n0_word_cross_check(diffs: list[DiffItem], word_raw_text: str) -> list[DiffItem]:
    """Cross-checks 'insert' diffs against ground-truth text of the original Word document.

    If an insertion in PDF (e.g. dropped character/word) actually exists in the original
    Word XML along with surrounding context, it indicates LibreOffice layout omission
    rather than a real document divergence. Marks the item as maybe_noise with an explanatory note.
    """
    if not word_raw_text or not word_raw_text.strip():
        return diffs

    normalized_word_raw = unicodedata.normalize("NFC", word_raw_text)
    normalized_word_raw = re.sub(r"\s+", " ", normalized_word_raw)

    for item in diffs:
        # Only inspect insertions (where Word PDF had no text) that are currently marked as diff
        if item.kind != "insert" and item.word_text.strip():
            continue
        if item.category != "diff":
            continue

        pdf_text = item.pdf_text.strip()
        if not pdf_text:
            continue

        # Extract last token of context_before
        words_before = item.context_before.strip().split()
        tok_before = words_before[-1] if words_before else ""

        # Extract first token of context_after, stripping trailing punctuation
        words_after = item.context_after.strip().split()
        tok_after = words_after[0].rstrip(",.;:!?") if words_after else ""

        if tok_before and tok_after:
            pat_str = rf"{re.escape(tok_before)}\s+{re.escape(pdf_text)}\s+{re.escape(tok_after)}"
        elif tok_before:
            pat_str = rf"{re.escape(tok_before)}\s+{re.escape(pdf_text)}"
        elif tok_after:
            pat_str = rf"{re.escape(pdf_text)}\s+{re.escape(tok_after)}"
        else:
            pat_str = rf"\b{re.escape(pdf_text)}\b"

        try:
            pattern = re.compile(pat_str, re.IGNORECASE)
            if pattern.search(normalized_word_raw):
                item.category = "maybe_noise"
                item.note = "N0: Ký tự có trong bản Word gốc, LibreOffice không dàn trang ra PDF tạm"
        except Exception:
            pass

    return diffs

