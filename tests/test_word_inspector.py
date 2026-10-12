"""Unit tests for word inspector."""

from pathlib import Path
from core.word_inspector import inspect_word


def test_inspect_sample01_word():
    docx_path = Path(__file__).parent / "fixtures" / "sample_01" / "approved.docx"
    info, warnings = inspect_word(str(docx_path))
    assert info.tracked_insertions == 0
    assert info.tracked_deletions == 0
    assert info.comments == 2
    assert any("2 comment" in w for w in warnings)
