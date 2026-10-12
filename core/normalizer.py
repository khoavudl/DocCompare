"""Converts Word documents to temporary PDF files using headless LibreOffice."""

import os
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path

from core.errors import ConvertFailedError, ConvertTimeoutError, LibreOfficeNotFoundError
from core.soffice_locator import find_soffice


def docx_to_pdf(docx_path: str, out_dir: str, timeout: int = 60) -> str:
    """Converts a docx/doc file to PDF using LibreOffice headless.
    
    Args:
        docx_path: Path to the input Word document.
        out_dir: Directory where the output PDF should be saved.
        timeout: Maximum seconds to wait for conversion (default 60s).
        
    Returns:
        Path to the converted PDF file.
        
    Raises:
        LibreOfficeNotFoundError: if soffice is not installed.
        ConvertTimeoutError: if conversion exceeds timeout.
        ConvertFailedError: if conversion fails or produces no output.
    """
    soffice_bin = find_soffice()
    src_path = Path(docx_path).resolve()
    if not src_path.is_file():
        raise ConvertFailedError(f"File nguồn không tồn tại: {docx_path}")

    target_out_dir = Path(out_dir).resolve()
    target_out_dir.mkdir(parents=True, exist_ok=True)

    # Thư mục tạm dùng cho profile riêng biệt và file ASCII ngắn
    tmp_work_dir = Path(tempfile.mkdtemp(prefix="doc_compare_conv_"))
    tmp_profile_dir = tmp_work_dir / "profile"
    tmp_profile_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Copy sang tên ASCII ngắn để tránh lỗi font/dấu tiếng Việt/khoảng trắng
        safe_input_name = f"input_{uuid.uuid4().hex[:8]}{src_path.suffix.lower()}"
        safe_input_path = tmp_work_dir / safe_input_name
        shutil.copy2(src_path, safe_input_path)

        # Profile URI theo chuẩn file URI
        profile_uri = tmp_profile_dir.as_uri()

        cmd = [
            soffice_bin,
            "--headless",
            "--norestore",
            "--nolockcheck",
            f"-env:UserInstallation={profile_uri}",
            "--convert-to",
            "pdf",
            "--outdir",
            str(target_out_dir),
            str(safe_input_path),
        ]

        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as exc:
            raise ConvertTimeoutError() from exc

        if result.returncode != 0:
            raise ConvertFailedError(
                f"soffice thoát với mã lỗi {result.returncode}: {result.stderr or result.stdout}"
            )

        # File PDF được sinh ra có cùng tên gốc với safe_input_name nhưng đuôi .pdf
        expected_pdf_name = safe_input_path.stem + ".pdf"
        output_pdf_path = target_out_dir / expected_pdf_name

        if not output_pdf_path.is_file() or output_pdf_path.stat().st_size == 0:
            raise ConvertFailedError("LibreOffice không tạo ra file PDF kết quả.")

        return str(output_pdf_path)

    finally:
        # Dọn dẹp thư mục làm việc tạm và profile
        shutil.rmtree(tmp_work_dir, ignore_errors=True)
