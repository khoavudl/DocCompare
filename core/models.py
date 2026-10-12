"""Data models for DocCompare."""

from dataclasses import dataclass, field
from typing import Literal

Source = Literal["word", "pdf"]


@dataclass
class Token:
    """Represents an atomic text token with location and normalization details."""
    raw: str  # Chữ gốc dùng để hiển thị
    norm: str = ""  # Chữ đã chuẩn hoá dùng để so sánh (tầng 2)
    page: int = 0  # Bắt đầu từ 1
    bbox: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    block_no: int = 0
    line_no: int = 0
    source: Source = "pdf"


@dataclass
class FilteredToken:
    """Represents a token removed by a noise filter."""
    token: Token
    filter_id: str  # "N2", "N3", ...
    reason: str  # Mô tả ngắn lý do lọc


@dataclass
class DiffItem:
    """Represents a single difference between Word and PDF documents."""
    id: int
    kind: Literal["replace", "insert", "delete"]
    word_text: str  # Nội dung bên Word (raw), rỗng nếu insert
    pdf_text: str  # Nội dung bên PDF (raw), rỗng nếu delete
    context_before: str
    context_after: str
    clause: str  # Ví dụ: "Điều 2.2", "Phần mở đầu"
    page_word: int | None
    page_pdf: int | None
    category: Literal["diff", "maybe_noise"] = "diff"
    note: str = ""  # Ghi chú, ví dụ: "N10: nội dung giống nhau, chỉ khác vị trí"


@dataclass
class PdfMetadata:
    """Metadata extracted from the PDF document."""
    format: str
    producer: str
    creator: str
    author: str
    creation_date: str
    mod_date: str
    page_count: int
    signature_fields: int
    encrypted: bool


@dataclass
class WordInfo:
    """Inspection information for Word document."""
    tracked_insertions: int
    tracked_deletions: int
    comments: int


@dataclass
class CompareOptions:
    """Options governing comparison and filtering."""
    case_sensitive: bool = False  # Mặc định tắt phân biệt hoa/thường
    config_path: str = "config/filters.yaml"


@dataclass
class CompareResult:
    """The aggregate output of document comparison."""
    word_path: str
    pdf_path: str
    word_sha256: str
    pdf_sha256: str
    options: CompareOptions
    tool_version: str
    run_at: str  # ISO 8601 kèm múi giờ
    word_info: WordInfo
    pdf_meta: PdfMetadata
    diffs: list[DiffItem] = field(default_factory=list)
    filtered: list[FilteredToken] = field(default_factory=list)
    filter_stats: dict[str, int] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
