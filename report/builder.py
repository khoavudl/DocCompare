"""HTML Report Builder rendering comprehensive standalone comparison reports."""

import difflib
import html
import re
from datetime import datetime
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

from core.models import CompareResult

TEMPLATE_DIR = Path(__file__).parent
TEMPLATE_NAME = "template.html.j2"


def highlight_character_diffs(word_text: str, pdf_text: str) -> tuple[str, str]:
    """Generates character-level highlighted HTML for replaced diff items."""
    matcher = difflib.SequenceMatcher(None, word_text, pdf_text)
    w_out: list[str] = []
    p_out: list[str] = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            w_out.append(html.escape(word_text[i1:i2]))
            p_out.append(html.escape(pdf_text[j1:j2]))
        elif tag == "replace":
            w_out.append(f'<span class="char-del">{html.escape(word_text[i1:i2])}</span>')
            p_out.append(f'<span class="char-ins">{html.escape(pdf_text[j1:j2])}</span>')
        elif tag == "delete":
            w_out.append(f'<span class="char-del">{html.escape(word_text[i1:i2])}</span>')
        elif tag == "insert":
            p_out.append(f'<span class="char-ins">{html.escape(pdf_text[j1:j2])}</span>')

    return "".join(w_out), "".join(p_out)


def get_default_report_path(pdf_path: str) -> Path:
    """Generates default output path: ~/Documents/DocCompare/DocCompare_{yyyyMMdd_HHmmss}_{stem}.html"""
    try:
        report_dir = Path.home() / "Documents" / "DocCompare"
        report_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        report_dir = Path(pdf_path).parent

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    clean_stem = re.sub(r"[^\w\-]", "_", Path(pdf_path).stem)[:30]
    filename = f"DocCompare_{timestamp}_{clean_stem}.html"
    return report_dir / filename


def build_html_report(result: CompareResult, output_path: str | None = None) -> str:
    """Renders the HTML report template and saves it to disk.
    
    Args:
        result: CompareResult instance from pipeline execution.
        output_path: Optional explicit output file path.
        
    Returns:
        Absolute path to the created HTML report file.
    """
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=False,
    )
    template = env.get_template(TEMPLATE_NAME)

    # Chuẩn bị view items cho diff với character highlighting
    prepared_diffs = []
    for d in result.diffs:
        if d.kind == "replace":
            w_html, p_html = highlight_character_diffs(d.word_text, d.pdf_text)
        elif d.kind == "delete":
            w_html = html.escape(d.word_text)
            p_html = ""
        else:  # insert
            w_html = ""
            p_html = html.escape(d.pdf_text)

        diff_view = {
            "id": d.id,
            "kind": d.kind,
            "word_text": d.word_text,
            "pdf_text": d.pdf_text,
            "word_html": w_html,
            "pdf_html": p_html,
            "context_before": html.escape(d.context_before),
            "context_after": html.escape(d.context_after),
            "clause": d.clause,
            "page_word": d.page_word,
            "page_pdf": d.page_pdf,
            "category": d.category,
            "note": d.note,
        }
        prepared_diffs.append(diff_view)

    # Render template
    rendered_html = template.render(
        result=result,
        word_filename=Path(result.word_path).name,
        pdf_filename=Path(result.pdf_path).name,
        prepared_diffs=prepared_diffs,
    )

    if output_path:
        out_file = Path(output_path).resolve()
        out_file.parent.mkdir(parents=True, exist_ok=True)
    else:
        out_file = get_default_report_path(result.pdf_path)

    with open(out_file, "w", encoding="utf-8") as f:
        f.write(rendered_html)

    return str(out_file)
