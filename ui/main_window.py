"""Main GUI window implemented with CustomTkinter for DocCompare."""

import os
from pathlib import Path
import subprocess
import sys
import threading
from tkinter import filedialog, messagebox
import tkinter as tk
import webbrowser

import customtkinter as ctk
import pymupdf

from core.errors import DocCompareError
from core.models import CompareOptions, CompareResult
from core.pipeline import run_compare
from report.builder import build_html_report


def open_system_folder(folder_path: str | Path) -> None:
    """Opens folder in native file explorer across Windows, macOS, and Linux."""
    path = Path(folder_path).resolve()
    target = str(path if path.is_dir() else path.parent)
    try:
        if sys.platform == "win32":
            os.startfile(target)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.run(["open", target], check=False)
        else:
            subprocess.run(["xdg-open", target], check=False)
    except Exception as exc:
        messagebox.showerror("Lỗi mở thư mục", f"Không thể mở thư mục: {exc}")


class MainWindow(ctk.CTk):
    """CustomTkinter main application window for comparing Word and PDF documents."""

    def __init__(self) -> None:
        super().__init__()

        # Window configuration
        self.title("So sánh hợp đồng Word ↔ PDF")
        self.geometry("660x540")
        self.resizable(False, False)

        # Appearance
        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")

        # State variables
        self.word_path_var = ctk.StringVar(value="")
        self.pdf_path_var = ctk.StringVar(value="")
        self.case_sensitive_var = ctk.BooleanVar(value=False)
        self.status_text_var = ctk.StringVar(value="Sẵn sàng")
        self.generated_report_path: str | None = None
        self.is_comparing = False
        self.logo_img: tk.PhotoImage | None = None

        self._build_ui()

    def _load_logo_image(self) -> tk.PhotoImage | None:
        """Loads and scales Logo-fes.png with antialiasing using PyMuPDF."""
        candidates = [
            Path("Logo-fes.png"),
            Path(__file__).resolve().parent.parent / "Logo-fes.png",
            getattr(sys, "_MEIPASS", Path(".")) / "Logo-fes.png" if hasattr(sys, "_MEIPASS") else None,
        ]
        for p in candidates:
            if p and p.is_file():
                try:
                    doc = pymupdf.open(str(p))
                    page = doc[0]
                    # Scale to ~105px width
                    target_width = 105.0
                    scale = target_width / page.rect.width
                    pix = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale))
                    return tk.PhotoImage(data=pix.tobytes("png"))
                except Exception:
                    pass
        return None

    def _build_ui(self) -> None:
        """Constructs widgets and layout."""
        # Main container with padding
        self.container = ctk.CTkFrame(self, corner_radius=10)
        self.container.pack(fill="both", expand=True, padx=16, pady=16)

        # Header Frame (Logo on top-left, title next to it)
        header_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        header_frame.pack(fill="x", padx=16, pady=(8, 14))

        self.logo_img = self._load_logo_image()
        if self.logo_img:
            logo_card = ctk.CTkFrame(header_frame, fg_color="#FFFFFF", corner_radius=6)
            logo_card.pack(side="left", padx=(0, 16))
            logo_lbl = tk.Label(logo_card, image=self.logo_img, bg="#FFFFFF", borderwidth=0)
            logo_lbl.pack(padx=4, pady=2)

        title_lbl = ctk.CTkLabel(
            header_frame,
            text="So sánh hợp đồng Word ↔ PDF",
            font=ctk.CTkFont(size=18, weight="bold"),
            anchor="w",
        )
        title_lbl.pack(side="left", fill="x", expand=True)

        # Input Frame (Word & PDF file selection)
        files_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        files_frame.pack(fill="x", padx=16, pady=4)


        # 1. Word File Row
        word_lbl = ctk.CTkLabel(files_frame, text="File Word (đã duyệt):", width=145, anchor="w")
        word_lbl.grid(row=0, column=0, padx=(0, 8), pady=6, sticky="w")

        self.word_entry = ctk.CTkEntry(
            files_frame,
            textvariable=self.word_path_var,
            placeholder_text="Chọn file .docx hoặc .doc...",
            state="readonly",
            width=320,
        )
        self.word_entry.grid(row=0, column=1, padx=4, pady=6, sticky="ew")

        self.word_btn = ctk.CTkButton(
            files_frame,
            text="Chọn…",
            width=80,
            command=self._choose_word_file,
        )
        self.word_btn.grid(row=0, column=2, padx=(8, 0), pady=6)

        # 2. PDF File Row
        pdf_lbl = ctk.CTkLabel(files_frame, text="File PDF (WeSign):", width=145, anchor="w")
        pdf_lbl.grid(row=1, column=0, padx=(0, 8), pady=6, sticky="w")

        self.pdf_entry = ctk.CTkEntry(
            files_frame,
            textvariable=self.pdf_path_var,
            placeholder_text="Chọn file .pdf...",
            state="readonly",
            width=320,
        )
        self.pdf_entry.grid(row=1, column=1, padx=4, pady=6, sticky="ew")

        self.pdf_btn = ctk.CTkButton(
            files_frame,
            text="Chọn…",
            width=80,
            command=self._choose_pdf_file,
        )
        self.pdf_btn.grid(row=1, column=2, padx=(8, 0), pady=6)

        files_frame.columnconfigure(1, weight=1)

        # Options Row
        options_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        options_frame.pack(fill="x", padx=16, pady=(4, 10))

        self.case_chk = ctk.CTkCheckBox(
            options_frame,
            text="Phân biệt chữ hoa/thường",
            variable=self.case_sensitive_var,
        )
        self.case_chk.pack(side="left", padx=4)

        # Action: Compare Button
        self.compare_btn = ctk.CTkButton(
            self.container,
            text="So sánh",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=36,
            command=self._start_compare_thread,
            state="disabled",
        )
        self.compare_btn.pack(fill="x", padx=16, pady=8)

        # Progress Section
        progress_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        progress_frame.pack(fill="x", padx=16, pady=(4, 10))

        self.progress_bar = ctk.CTkProgressBar(progress_frame, height=12)
        self.progress_bar.pack(fill="x", pady=(2, 4))
        self.progress_bar.set(0.0)

        self.status_lbl = ctk.CTkLabel(
            progress_frame,
            textvariable=self.status_text_var,
            font=ctk.CTkFont(size=12),
            text_color="gray",
            anchor="w",
        )
        self.status_lbl.pack(fill="x")

        # Result Section Frame
        self.result_frame = ctk.CTkFrame(self.container)
        self.result_frame.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        result_header = ctk.CTkLabel(
            self.result_frame,
            text="Kết quả:",
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w",
        )
        result_header.pack(fill="x", padx=12, pady=(8, 2))

        # Badges Row
        self.badges_frame = ctk.CTkFrame(self.result_frame, fg_color="transparent")
        self.badges_frame.pack(fill="x", padx=12, pady=2)

        self.diff_badge = ctk.CTkLabel(
            self.badges_frame,
            text="🔴 0 điểm khác biệt",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=("#C62828", "#EF5350"),
        )
        self.diff_badge.pack(side="left", padx=(0, 16))

        self.noise_badge = ctk.CTkLabel(
            self.badges_frame,
            text="🟡 0 có thể là nhiễu",
            font=ctk.CTkFont(size=13),
            text_color=("#EF6C00", "#FFA726"),
        )
        self.noise_badge.pack(side="left", padx=(0, 16))

        self.filtered_badge = ctk.CTkLabel(
            self.badges_frame,
            text="⚪ 0 đã lọc",
            font=ctk.CTkFont(size=13),
            text_color="gray",
        )
        self.filtered_badge.pack(side="left")

        # Warning text label
        self.warning_lbl = ctk.CTkLabel(
            self.result_frame,
            text="",
            font=ctk.CTkFont(size=12),
            text_color=("#F57F17", "#FFD54F"),
            anchor="w",
            wraplength=590,
            justify="left",
        )
        self.warning_lbl.pack(fill="x", padx=12, pady=(4, 6))

        # Action Buttons (Open report / Open directory)
        self.action_btns_frame = ctk.CTkFrame(self.result_frame, fg_color="transparent")
        self.action_btns_frame.pack(fill="x", padx=12, pady=(4, 12))

        self.open_report_btn = ctk.CTkButton(
            self.action_btns_frame,
            text="Mở báo cáo chi tiết",
            state="disabled",
            height=32,
            command=self._open_report,
        )
        self.open_report_btn.pack(side="left", padx=(0, 10))

        self.open_folder_btn = ctk.CTkButton(
            self.action_btns_frame,
            text="Mở thư mục",
            state="disabled",
            height=32,
            command=self._open_report_folder,
        )
        self.open_folder_btn.pack(side="left")


    def _choose_word_file(self) -> None:
        """Opens file dialog to choose a Word document."""
        filepath = filedialog.askopenfilename(
            title="Chọn file Word đã duyệt",
            filetypes=[("Word Document", "*.docx *.doc"), ("All Files", "*.*")],
        )
        if filepath:
            self.word_path_var.set(filepath)
            self._check_ready_state()

    def _choose_pdf_file(self) -> None:
        """Opens file dialog to choose a signed PDF document."""
        filepath = filedialog.askopenfilename(
            title="Chọn file PDF WeSign",
            filetypes=[("PDF Document", "*.pdf"), ("All Files", "*.*")],
        )
        if filepath:
            self.pdf_path_var.set(filepath)
            self._check_ready_state()

    def _check_ready_state(self) -> None:
        """Enables compare button only when both files are selected."""
        word_ok = bool(self.word_path_var.get().strip())
        pdf_ok = bool(self.pdf_path_var.get().strip())
        if word_ok and pdf_ok and not self.is_comparing:
            self.compare_btn.configure(state="normal")
        else:
            self.compare_btn.configure(state="disabled")

    def _set_inputs_state(self, state: str) -> None:
        """Enables or disables interactive inputs."""
        self.word_btn.configure(state=state)
        self.pdf_btn.configure(state=state)
        self.case_chk.configure(state=state)
        self.compare_btn.configure(state=state)

    def _start_compare_thread(self) -> None:
        """Launches the comparison in a background daemon thread."""
        word_file = self.word_path_var.get().strip()
        pdf_file = self.pdf_path_var.get().strip()

        if not word_file or not pdf_file:
            messagebox.showwarning("Thiếu file", "Vui lòng chọn đầy đủ cả 2 file Word và PDF.")
            return

        self.is_comparing = True
        self._set_inputs_state("disabled")
        self.open_report_btn.configure(state="disabled")
        self.open_folder_btn.configure(state="disabled")
        self.warning_lbl.configure(text="")
        self.progress_bar.set(0.0)
        self.status_text_var.set("0% Đang khởi động tiến trình so sánh...")

        # Worker thread
        thread = threading.Thread(
            target=self._worker_run,
            args=(word_file, pdf_file, self.case_sensitive_var.get()),
            daemon=True,
        )
        thread.start()

    def _worker_run(self, word_file: str, pdf_file: str, case_sensitive: bool) -> None:
        """Runs the comparison engine in background."""
        try:
            options = CompareOptions(case_sensitive=case_sensitive)

            def progress_cb(percent: int, message: str) -> None:
                self.after(0, lambda p=percent, m=message: self._update_progress_ui(p, m))

            result = run_compare(word_file, pdf_file, options, progress_cb=progress_cb)

            # Auto-save HTML report in the same directory as the PDF
            pdf_path_obj = Path(pdf_file)
            report_out = pdf_path_obj.parent / f"{pdf_path_obj.stem}_report.html"
            build_html_report(result, str(report_out))

            self.after(0, lambda r=result, p=str(report_out): self._on_success_ui(r, p))
        except DocCompareError as err:
            self.after(0, lambda msg=err.message_vi: self._on_error_ui(msg))
        except Exception as exc:
            self.after(0, lambda msg=f"Lỗi không xác định: {exc}": self._on_error_ui(msg))

    def _update_progress_ui(self, percent: int, message: str) -> None:
        """Thread-safe UI update for progress bar and label."""
        self.progress_bar.set(percent / 100.0)
        self.status_text_var.set(f"{percent}% {message}")

    def _on_success_ui(self, result: CompareResult, report_path: str) -> None:
        """Handles successful comparison result on UI thread."""
        self.is_comparing = False
        self.generated_report_path = report_path
        self._set_inputs_state("normal")
        self.open_report_btn.configure(state="normal")
        self.open_folder_btn.configure(state="normal")
        self.progress_bar.set(1.0)
        self.status_text_var.set("100% So sánh hoàn tất! Báo cáo đã được tạo.")

        # Update summary badges
        real_diffs = [d for d in result.diffs if d.category == "diff"]
        maybe_noises = [d for d in result.diffs if d.category == "maybe_noise"]
        filtered_count = len(result.filtered)

        self.diff_badge.configure(text=f"🔴 {len(real_diffs)} điểm khác biệt")
        self.noise_badge.configure(text=f"🟡 {len(maybe_noises)} có thể là nhiễu")
        self.filtered_badge.configure(text=f"⚪ {filtered_count} đã lọc")

        # Warnings if any
        if result.warnings:
            self.warning_lbl.configure(text="⚠️ " + " | ".join(result.warnings))
        else:
            self.warning_lbl.configure(text="")

    def _on_error_ui(self, error_message: str) -> None:
        """Handles comparison failure on UI thread."""
        self.is_comparing = False
        self._set_inputs_state("normal")
        self.progress_bar.set(0.0)
        self.status_text_var.set("Đã dừng do xảy ra lỗi.")
        messagebox.showerror("Lỗi so sánh", error_message)

    def _open_report(self) -> None:
        """Opens generated report in the default browser."""
        if self.generated_report_path and Path(self.generated_report_path).exists():
            webbrowser.open(Path(self.generated_report_path).resolve().as_uri())
        else:
            messagebox.showwarning("Thông báo", "Chưa có báo cáo nào được tạo.")

    def _open_report_folder(self) -> None:
        """Opens parent folder of the generated report in system file manager."""
        if self.generated_report_path and Path(self.generated_report_path).exists():
            open_system_folder(Path(self.generated_report_path).parent)
        elif self.pdf_path_var.get():
            open_system_folder(Path(self.pdf_path_var.get()).parent)
        else:
            messagebox.showwarning("Thông báo", "Vui lòng chọn file hoặc thực hiện so sánh trước.")
