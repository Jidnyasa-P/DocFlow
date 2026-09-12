"""
DOCX Parser & Feature Extraction (Person B / Engineering)

Offline twin of the extractor in model/train.ipynb (Section 2). Walks the
document body IN ORDER — paragraphs and tables interleaved — exactly like
the notebook does, so table/figure detection is deterministic instead of
guessed by the classifier. See model/feature_spec.md for the full contract.
"""
import re
from dataclasses import dataclass, field
from typing import List, Optional, Union

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph

# --- Must match model/feature_spec.md and model/train.ipynb exactly ---
STYLE_VOCAB = ["Normal", "Heading 1", "Heading 2", "Heading 3", "Title",
               "Caption", "List Paragraph", "Quote", "Other"]

FEATURE_COLUMNS = [
    "font_size", "is_bold", "is_italic", "alignment", "indent_left",
    "indent_first_line", "space_before", "space_after", "line_spacing",
    "is_all_caps", "starts_with_number", "word_count",
    "position_ratio_in_doc", "style_name_hash", "has_image", "is_table_element",
]

ALIGN_MAP = {
    WD_ALIGN_PARAGRAPH.LEFT: 0, None: 0,
    WD_ALIGN_PARAGRAPH.CENTER: 1,
    WD_ALIGN_PARAGRAPH.RIGHT: 2,
    WD_ALIGN_PARAGRAPH.JUSTIFY: 3,
}

STARTS_WITH_NUMBER_RE = re.compile(r"^\s*(\d+[.)]|\[\d+\])")


@dataclass
class ElementRecord:
    """One document element: either a paragraph or a whole table.

    `paragraph` is set for kind == "paragraph"; `table` is set for
    kind == "table". Exactly one of the two is non-None.
    """
    order_index: int
    kind: str  # "paragraph" | "table"
    text: str
    features: List[float] = field(default_factory=list)
    paragraph: Optional[Paragraph] = None
    table: Optional[Table] = None
    label: Optional[str] = None
    label_confidence: float = 0.0

    @property
    def is_table(self) -> bool:
        return self.kind == "table"


def _pt(val) -> float:
    return round(val.pt, 2) if val is not None else 0.0


def _cm(val) -> float:
    return round(val.cm, 3) if val is not None else 0.0


def _paragraph_has_image(paragraph: Paragraph) -> bool:
    return len(paragraph._element.findall(".//" + qn("w:drawing"))) > 0


def _run_formatting(paragraph: Paragraph):
    runs = paragraph.runs
    sizes = [r.font.size for r in runs if r.font.size is not None]
    font_size = _pt(sizes[0]) if sizes else 11.0
    bold_flags = [bool(r.bold) for r in runs] or [False]
    italic_flags = [bool(r.italic) for r in runs] or [False]
    is_bold = int(sum(bold_flags) > len(bold_flags) / 2)
    is_italic = int(sum(italic_flags) > len(italic_flags) / 2)
    return font_size, is_bold, is_italic


def _style_hash(paragraph_or_none) -> int:
    style_name = "Normal"
    if paragraph_or_none is not None and paragraph_or_none.style:
        style_name = paragraph_or_none.style.name
    return STYLE_VOCAB.index(style_name) if style_name in STYLE_VOCAB else len(STYLE_VOCAB)


def _features_for_paragraph(p: Paragraph, order_index: int) -> Optional[dict]:
    text = p.text.strip()
    has_img = _paragraph_has_image(p)
    if not text and not has_img:
        return None  # genuinely empty spacer paragraph -- never a row

    font_size, is_bold, is_italic = _run_formatting(p)
    alignment = ALIGN_MAP.get(p.alignment, 0)
    pf = p.paragraph_format
    line_spacing = pf.line_spacing if pf.line_spacing else 1.0

    feat = {
        "font_size": font_size, "is_bold": is_bold, "is_italic": is_italic,
        "alignment": alignment,
        "indent_left": _cm(pf.left_indent),
        "indent_first_line": _cm(pf.first_line_indent),
        "space_before": _pt(pf.space_before), "space_after": _pt(pf.space_after),
        "line_spacing": line_spacing,
        "is_all_caps": int(bool(text) and text.upper() == text and any(c.isalpha() for c in text)),
        "starts_with_number": int(bool(text) and bool(STARTS_WITH_NUMBER_RE.match(text))),
        "word_count": len(text.split()),
        "style_name_hash": _style_hash(p),
        "has_image": int(has_img),
        "is_table_element": 0,
    }
    return feat, (text if text else "[IMAGE]")


def _features_for_table(t: Table) -> dict:
    all_cells_text = []
    first_size, first_bold = None, None
    for row in t.rows:
        for cell in row.cells:
            ctext = cell.text.strip()
            if ctext:
                all_cells_text.append(ctext)
            if first_size is None:
                for p2 in cell.paragraphs:
                    if p2.runs:
                        first_size, first_bold, _ = _run_formatting(p2)
                        break
    text_preview = " | ".join(all_cells_text[:6]) or "[TABLE]"

    feat = {
        "font_size": first_size or 11.0, "is_bold": first_bold or 0, "is_italic": 0,
        "alignment": 0, "indent_left": 0.0, "indent_first_line": 0.0,
        "space_before": 0.0, "space_after": 0.0, "line_spacing": 1.0,
        "is_all_caps": 0, "starts_with_number": 0,
        "word_count": sum(len(c.split()) for c in all_cells_text),
        "style_name_hash": len(STYLE_VOCAB),
        "has_image": 0, "is_table_element": 1,
    }
    return feat, text_preview


def parse_docx(path: str):
    """Load a DOCX and return (records, doc).

    records: one ElementRecord per non-empty paragraph or table, in
    document order, each with its 16-column feature vector already
    computed (feature order == FEATURE_COLUMNS).
    """
    doc = Document(path)
    body = doc.element.body

    raw_records = []  # (kind, obj, feat_dict, text)
    idx = 0
    for child in body.iterchildren():
        if child.tag == qn("w:p"):
            p = Paragraph(child, doc)
            result = _features_for_paragraph(p, idx)
            if result is None:
                continue
            feat, text = result
            raw_records.append(("paragraph", p, feat, text, idx))
            idx += 1
        elif child.tag == qn("w:tbl"):
            t = Table(child, doc)
            feat, text = _features_for_table(t)
            raw_records.append(("table", t, feat, text, idx))
            idx += 1
        else:
            continue  # sectPr, etc.

    total = max(idx, 1)
    records: List[ElementRecord] = []
    for kind, obj, feat, text, order_index in raw_records:
        feat["position_ratio_in_doc"] = round(order_index / total, 4)
        vector = [feat[c] for c in FEATURE_COLUMNS]
        records.append(ElementRecord(
            order_index=order_index,
            kind=kind,
            text=text,
            features=vector,
            paragraph=obj if kind == "paragraph" else None,
            table=obj if kind == "table" else None,
        ))

    return records, doc


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python parser.py <path_to_docx>")
        sys.exit(1)
    records, _ = parse_docx(sys.argv[1])
    print(f"Parsed {len(records)} elements (paragraphs + tables)")
    for r in records[:15]:
        print(r.order_index, r.kind, dict(zip(FEATURE_COLUMNS, r.features)), "|", r.text[:60])
