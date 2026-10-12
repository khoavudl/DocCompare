"""Automated test suite verifying the UI logic and requirements for Phase P5."""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from ui.main_window import MainWindow, open_system_folder
from core.models import CompareOptions


@pytest.fixture
def app():
    """Creates a MainWindow instance with mocked mainloop and event loops."""
    with patch("ui.main_window.messagebox.showerror"), patch("ui.main_window.messagebox.showwarning"):
        app_instance = MainWindow()
        # Mock after to invoke callbacks synchronously during test
        app_instance.after = lambda delay, cb: cb() if cb else None
        yield app_instance
        try:
            app_instance.destroy()
        except Exception:
            pass



def test_ui_initial_state(app):
    """Verifies default widget values, dimensions, and button states."""
    assert "So sánh hợp đồng Word ↔ PDF" in app.title()
    assert app.compare_btn.cget("state") == "disabled"
    assert app.open_report_btn.cget("state") == "disabled"
    assert app.open_folder_btn.cget("state") == "disabled"
    assert app.case_sensitive_var.get() is False


def test_ui_ready_state_toggles(app):
    """Verifies that the compare button enables only when both files are selected."""
    assert app.compare_btn.cget("state") == "disabled"

    app.word_path_var.set("approved.docx")
    app._check_ready_state()
    assert app.compare_btn.cget("state") == "disabled"

    app.pdf_path_var.set("signed.pdf")
    app._check_ready_state()
    assert app.compare_btn.cget("state") == "normal"

    # Clearing one disables again
    app.word_path_var.set("")
    app._check_ready_state()
    assert app.compare_btn.cget("state") == "disabled"


def test_ui_sample01_run_and_badges(app, tmp_path):
    """Verifies executing sample_01 via UI worker produces identical results to CLI."""
    word_file = "tests/fixtures/sample_01/approved.docx"
    pdf_file = "tests/fixtures/sample_01/wesign.pdf"

    # Run the worker directly
    app._worker_run(word_file, pdf_file, case_sensitive=False)

    assert app.is_comparing is False
    assert app.generated_report_path is not None
    assert Path(app.generated_report_path).exists()
    assert app.open_report_btn.cget("state") == "normal"
    assert app.open_folder_btn.cget("state") == "normal"

    # Badges verification
    assert "🔴 4 điểm khác biệt" in app.diff_badge.cget("text")
    assert "🟡 0 có thể là nhiễu" in app.noise_badge.cget("text")
    assert "⚪" in app.filtered_badge.cget("text")
    assert "comment" in app.warning_lbl.cget("text")


def test_ui_case_sensitive_option_with_m8(app):
    """Verifies that the case_sensitive checkbox affects difference detection on M8 mutation."""
    word_file = "tests/fixtures/sample_01/approved.docx"
    pdf_file = "tests/fixtures/mutations/M8/fake_wesign.pdf"

    # Case 1: Insensitive (default) -> 0 diffs
    app._worker_run(word_file, pdf_file, case_sensitive=False)
    assert "🔴 0 điểm khác biệt" in app.diff_badge.cget("text")

    # Case 2: Sensitive -> 1 diff detected
    app._worker_run(word_file, pdf_file, case_sensitive=True)
    assert "🔴 1 điểm khác biệt" in app.diff_badge.cget("text")


def test_ui_error_handling_shows_vietnamese_message(app):
    """Verifies that invalid input files trigger a friendly Vietnamese error dialog."""
    with patch("ui.main_window.messagebox.showerror") as mock_err:
        app._worker_run("missing_word.docx", "missing_pdf.pdf", case_sensitive=False)

        assert mock_err.called
        title, message = mock_err.call_args[0]
        assert "Lỗi" in title
        assert "File không hợp lệ: File Word không tồn tại" in message

    # UI controls should be restored
    assert app.is_comparing is False
    assert app.word_btn.cget("state") == "normal"
    assert app.pdf_btn.cget("state") == "normal"


def test_ui_error_libreoffice_not_found(app):
    """Verifies Vietnamese message when LibreOffice soffice binary is missing."""
    from core.errors import LibreOfficeNotFoundError

    with patch("ui.main_window.run_compare", side_effect=LibreOfficeNotFoundError()), \
         patch("ui.main_window.messagebox.showerror") as mock_err:
        app._worker_run("tests/fixtures/sample_01/approved.docx", "tests/fixtures/sample_01/wesign.pdf", False)
        assert mock_err.called
        assert "Chưa cài LibreOffice" in mock_err.call_args[0][1]


def test_ui_error_pdf_encrypted(app):
    """Verifies Vietnamese message when PDF is password-protected."""
    from core.errors import PdfEncryptedError

    with patch("ui.main_window.run_compare", side_effect=PdfEncryptedError()), \
         patch("ui.main_window.messagebox.showerror") as mock_err:
        app._worker_run("tests/fixtures/sample_01/approved.docx", "tests/fixtures/sample_01/wesign.pdf", False)
        assert mock_err.called
        assert "PDF đang được khoá bằng mật khẩu" in mock_err.call_args[0][1]


def test_ui_error_pdf_scanned(app):
    """Verifies Vietnamese message when PDF has no selectable text."""
    from core.errors import PdfNoTextError

    with patch("ui.main_window.run_compare", side_effect=PdfNoTextError()), \
         patch("ui.main_window.messagebox.showerror") as mock_err:
        app._worker_run("tests/fixtures/sample_01/approved.docx", "tests/fixtures/sample_01/wesign.pdf", False)
        assert mock_err.called
        assert "PDF không có lớp chữ (có thể là bản scan)" in mock_err.call_args[0][1]


def test_ui_open_system_folder(tmp_path):
    """Verifies open_system_folder helper safely calls platform opener."""
    with patch("subprocess.run") as mock_sub:
        open_system_folder(str(tmp_path))
        if os.name != "nt":
            assert mock_sub.called

