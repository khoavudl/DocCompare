"""Mutation testing suite (M1-M12) to prove no true differences are incorrectly filtered."""

from pathlib import Path
from core.models import CompareOptions
from core.pipeline import run_compare

BASE_DIR = Path(__file__).parent
APPROVED_DOCX = str(BASE_DIR / "fixtures" / "sample_01" / "approved.docx")
MUTATIONS_DIR = BASE_DIR / "fixtures" / "mutations"


def get_mutation_pdf(mut_id: str) -> str:
    return str(MUTATIONS_DIR / mut_id / "fake_wesign.pdf")


def test_m1_percentage_change():
    """M1: Đổi 1 chữ số: '8%' → '9%' (Điều 4.6) -> 1 diff, Điều 4.6"""
    pdf_path = get_mutation_pdf("M1")
    res = run_compare(APPROVED_DOCX, pdf_path, CompareOptions())
    assert len(res.diffs) == 1
    d = res.diffs[0]
    assert d.clause == "Điều 4.6"
    assert "8%" in d.word_text
    assert "9%" in d.pdf_text


def test_m2_money_amount_change():
    """M2: Đổi số tiền: '500.000VNĐ' → '800.000VNĐ' (Điều 4.2) -> 1 diff, Điều 4.2"""
    pdf_path = get_mutation_pdf("M2")
    res = run_compare(APPROVED_DOCX, pdf_path, CompareOptions())
    assert len(res.diffs) == 1
    d = res.diffs[0]
    assert d.clause == "Điều 4.2"
    assert "500.000" in d.word_text
    assert "800.000" in d.pdf_text


def test_m3_delete_sentence():
    """M3: Xoá cả câu -> 1 diff delete"""
    pdf_path = get_mutation_pdf("M3")
    res = run_compare(APPROVED_DOCX, pdf_path, CompareOptions())
    assert len(res.diffs) == 1
    d = res.diffs[0]
    assert d.kind == "delete"
    assert "chuyển khoản lại" in d.word_text
    assert d.pdf_text == ""


def test_m4_insert_sentence():
    """M4: Thêm câu mới vào cuối Điều 7.2 -> 1 diff insert"""
    pdf_path = get_mutation_pdf("M4")
    res = run_compare(APPROVED_DOCX, pdf_path, CompareOptions())
    assert len(res.diffs) == 1
    d = res.diffs[0]
    assert d.kind == "insert"
    assert d.word_text == ""
    assert "confidentiality" in d.pdf_text


def test_m5_change_platform_name():
    """M5: Đổi 'Youtube' → 'Tiktok' -> 1 diff, Điều 2.1"""
    pdf_path = get_mutation_pdf("M5")
    res = run_compare(APPROVED_DOCX, pdf_path, CompareOptions())
    assert len(res.diffs) == 1
    d = res.diffs[0]
    assert d.clause == "Điều 2.1"
    assert "Youtube" in d.word_text
    assert "Tiktok" in d.pdf_text


def test_m6_change_word_at_last_line_of_page():
    """M6: Đổi 1 chữ ở dòng cuối cùng của một trang -> 1 diff (chứng minh không lọc theo vị trí)"""
    pdf_path = get_mutation_pdf("M6")
    res = run_compare(APPROVED_DOCX, pdf_path, CompareOptions())
    assert len(res.diffs) == 1
    d = res.diffs[0]
    assert "budgeting." in d.word_text
    assert "finance." in d.pdf_text


def test_m7_change_word_at_first_line_of_page():
    """M7: Đổi 1 chữ ở dòng đầu tiên của một trang -> 1 diff"""
    pdf_path = get_mutation_pdf("M7")
    res = run_compare(APPROVED_DOCX, pdf_path, CompareOptions())
    assert len(res.diffs) == 1
    d = res.diffs[0]
    assert "ADIGIT" in d.word_text
    assert "BDIGIT" in d.pdf_text


def test_m8_case_sensitivity_change():
    """M8: Đổi 'SONI' → 'Soni' -> case_sensitive=true: 1 diff, false: 0 diff"""
    pdf_path = get_mutation_pdf("M8")
    res_false = run_compare(APPROVED_DOCX, pdf_path, CompareOptions(case_sensitive=False))
    assert len(res_false.diffs) == 0

    res_true = run_compare(APPROVED_DOCX, pdf_path, CompareOptions(case_sensitive=True))
    assert len(res_true.diffs) == 1
    assert "SONI" in res_true.diffs[0].word_text
    assert "Soni" in res_true.diffs[0].pdf_text


def test_m9_change_bank_account_number():
    """M9: Đổi số tài khoản '612345688' → '612345699' -> 1 diff"""
    pdf_path = get_mutation_pdf("M9")
    res = run_compare(APPROVED_DOCX, pdf_path, CompareOptions())
    assert len(res.diffs) == 1
    d = res.diffs[0]
    assert "612345688" in d.word_text
    assert "612345699" in d.pdf_text


def test_m10_vietnamese_accent_placement():
    """M10: Đổi dấu: 'Bình Hòa' → 'Bình Hoà' -> Ghi nhận kết quả báo reviewer"""
    pdf_path = get_mutation_pdf("M10")
    res = run_compare(APPROVED_DOCX, pdf_path, CompareOptions())
    # Chuẩn NFC không đồng nhất dấu trên 'o' và dấu trên 'a'
    # Ghi nhận kết quả: tool phát hiện 1 diff replace 'Hòa' -> 'Hoà'
    assert len(res.diffs) == 1
    d = res.diffs[0]
    assert "Hòa" in d.word_text
    assert "Hoà" in d.pdf_text


def test_m11_isolated_number_on_single_line():
    """M11: Số '3' đứng riêng 1 dòng ở trang 2 -> Không bị N2 lọc nhầm vì số != số trang"""
    pdf_path = get_mutation_pdf("M11")
    res = run_compare(APPROVED_DOCX, pdf_path, CompareOptions())
    assert len(res.diffs) == 1
    d = res.diffs[0]
    assert d.kind == "insert"
    assert "3" in d.pdf_text


def test_m12_control_no_changes():
    """M12: Không đổi gì (bản đối chứng) -> 0 diff"""
    pdf_path = get_mutation_pdf("M12")
    res = run_compare(APPROVED_DOCX, pdf_path, CompareOptions())
    assert len(res.diffs) == 0
