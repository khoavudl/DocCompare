"""Integration test for sample_01 against expected.json criteria."""

import json
from pathlib import Path
from core.models import CompareOptions
from core.pipeline import run_compare


def test_pipeline_sample01():
    fixtures_dir = Path(__file__).parent / "fixtures" / "sample_01"
    word_path = str(fixtures_dir / "approved.docx")
    pdf_path = str(fixtures_dir / "wesign.pdf")
    expected_path = fixtures_dir / "expected.json"

    with open(expected_path, "r", encoding="utf-8") as f:
        expected = json.load(f)

    options = CompareOptions(case_sensitive=False)
    res = run_compare(word_path, pdf_path, options)

    # 1. Đúng 4 diff loại đỏ
    red_diffs = [d for d in res.diffs if d.category == "diff"]
    assert len(red_diffs) == expected["diff_count"], f"Expected {expected['diff_count']} diffs, got {len(red_diffs)}"

    # 2. Maybe noise <= 2
    yellow_diffs = [d for d in res.diffs if d.category == "maybe_noise"]
    assert len(yellow_diffs) <= expected["maybe_noise_max"]

    # 3. Khớp từng diff mong đợi
    for exp_d in expected["diffs"]:
        matched = False
        for actual in red_diffs:
            clause_match = actual.clause == exp_d["clause"]
            word_match = exp_d["word_contains"] in actual.word_text
            pdf_match = exp_d["pdf_contains"] in actual.pdf_text
            ctx_match = True
            if "context_contains" in exp_d:
                ctx_match = (
                    exp_d["context_contains"] in actual.context_before
                    or exp_d["context_contains"] in actual.context_after
                )
            if clause_match and word_match and pdf_match and ctx_match:
                matched = True
                break
        assert matched, f"Diff expectation failed: {exp_d}"

    # 4. Word info
    assert res.word_info.comments == expected["word_info"]["comments"]

    # 5. PDF metadata
    assert res.pdf_meta.page_count == expected["pdf_meta"]["page_count"]
    assert res.pdf_meta.signature_fields == expected["pdf_meta"]["signature_fields"]
    assert expected["pdf_meta"]["format"] in res.pdf_meta.format

    # 6. Filtered tokens must include
    for req in expected["filtered_must_include"]:
        f_id = req["filter"]
        txt = req["text_contains"]
        filter_text = " ".join(f.token.raw for f in res.filtered if f.filter_id == f_id)
        assert txt in filter_text, f"Expected filtered text containing '{txt}' for filter '{f_id}' not found in: {filter_text}"

    # 7. Word tokens must not include comment text
    for forbidden in expected["word_tokens_must_not_include"]:
        # Không có trong diff của Word và không có trong filtered
        assert not any(forbidden in d.word_text for d in res.diffs)


def test_determinism_sample01():
    """Chạy 2 lần liên tiếp ra kết quả giống hệt nhau (trừ run_at)."""
    fixtures_dir = Path(__file__).parent / "fixtures" / "sample_01"
    word_path = str(fixtures_dir / "approved.docx")
    pdf_path = str(fixtures_dir / "wesign.pdf")
    options = CompareOptions(case_sensitive=False)

    res1 = run_compare(word_path, pdf_path, options)
    res2 = run_compare(word_path, pdf_path, options)

    assert len(res1.diffs) == len(res2.diffs)
    for d1, d2 in zip(res1.diffs, res2.diffs):
        assert d1.id == d2.id
        assert d1.clause == d2.clause
        assert d1.word_text == d2.word_text
        assert d1.pdf_text == d2.pdf_text
        assert d1.category == d2.category
        assert d1.context_before == d2.context_before
        assert d1.context_after == d2.context_after

    assert len(res1.filtered) == len(res2.filtered)
    assert res1.filter_stats == res2.filter_stats
    assert res1.word_sha256 == res2.word_sha256
    assert res1.pdf_sha256 == res2.pdf_sha256
