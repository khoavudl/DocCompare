"""Custom exceptions for DocCompare with user-friendly Vietnamese messages."""


class DocCompareError(Exception):
    """Base exception for all DocCompare errors."""
    def __init__(self, message_vi: str):
        super().__init__(message_vi)
        self.message_vi = message_vi


class InputFileError(DocCompareError):
    """Raised when an input file is invalid, missing, or exceeds maximum size."""
    def __init__(self, detail: str = ""):
        msg = f"File không hợp lệ: {detail}" if detail else "File không hợp lệ."
        super().__init__(msg)


class LibreOfficeNotFoundError(DocCompareError):
    """Raised when soffice executable cannot be located."""
    def __init__(self, message_vi: str = "Chưa cài LibreOffice. Vui lòng liên hệ IT hoặc cài tại libreoffice.org"):
        super().__init__(message_vi)


class ConvertTimeoutError(DocCompareError):
    """Raised when converting Word document to PDF times out."""
    def __init__(self, message_vi: str = "Chuyển đổi Word quá thời gian. Thử đóng các ứng dụng Office và chạy lại."):
        super().__init__(message_vi)


class ConvertFailedError(DocCompareError):
    """Raised when LibreOffice conversion fails or produces no output file."""
    def __init__(self, message_vi: str = "Không chuyển được file Word sang PDF."):
        super().__init__(message_vi)


class PdfEncryptedError(DocCompareError):
    """Raised when a PDF file is encrypted or password-protected."""
    def __init__(self, message_vi: str = "PDF đang được khoá bằng mật khẩu, không thể đọc."):
        super().__init__(message_vi)


class PdfNoTextError(DocCompareError):
    """Raised when a PDF file contains no selectable text layer (e.g. scanned)."""
    def __init__(self, message_vi: str = "PDF không có lớp chữ (có thể là bản scan). Tool không hỗ trợ."):
        super().__init__(message_vi)
