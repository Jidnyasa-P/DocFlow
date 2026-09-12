"""
Formatting Engine (Person B / Engineering)

Applies the publication spec from the problem statement to every classified
element. Paragraphs and tables are handled separately since python-docx
exposes very different APIs for each.

Publication spec:
    Font: Times New Roman, Black, 12pt body, justified, 1.5 line spacing,
    1.27cm first-line indent. Margins: top/bottom 1.52cm, left 1.97cm,
    right 1.96cm, gutter left. Heading 1: 16pt Bold. Subheading: 12pt Bold.
"""
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT

BODY_FONT = "Times New Roman"
BODY_COLOR = RGBColor(0, 0, 0)

MARGIN_TOP = Cm(1.52)
MARGIN_BOTTOM = Cm(1.52)
MARGIN_LEFT = Cm(1.97)
MARGIN_RIGHT = Cm(1.96)

# label -> paragraph-level spec
PARAGRAPH_SPEC = {
    "Title": dict(size=20, bold=True, alignment=WD_ALIGN_PARAGRAPH.CENTER,
                  line_spacing=1.5, space_before=24, space_after=24, first_line_indent=0),
    "Author": dict(size=13, bold=False, italic=True, alignment=WD_ALIGN_PARAGRAPH.CENTER,
                   line_spacing=1.5, space_before=0, space_after=12, first_line_indent=0),
    "Chapter Heading": dict(size=16, bold=True, alignment=WD_ALIGN_PARAGRAPH.LEFT,
                             line_spacing=1.5, space_before=24, space_after=12, first_line_indent=0),
    "Subheading": dict(size=12, bold=True, alignment=WD_ALIGN_PARAGRAPH.LEFT,
                        line_spacing=1.5, space_before=12, space_after=6, first_line_indent=0),
    "Body Paragraph": dict(size=12, bold=False, alignment=WD_ALIGN_PARAGRAPH.JUSTIFY,
                            line_spacing=1.5, space_before=0, space_after=0, first_line_indent=1.27),
    "Figure": dict(size=11, bold=False, alignment=WD_ALIGN_PARAGRAPH.CENTER,
                   line_spacing=1.0, space_before=12, space_after=0, first_line_indent=0),
    "Caption": dict(size=10, bold=False, italic=True, alignment=WD_ALIGN_PARAGRAPH.CENTER,
                    line_spacing=1.0, space_before=0, space_after=12, first_line_indent=0),
    "Reference": dict(size=10, bold=False, alignment=WD_ALIGN_PARAGRAPH.JUSTIFY,
                       line_spacing=1.0, space_before=0, space_after=6, first_line_indent=0,
                       left_indent=0.63),
    "List": dict(size=12, bold=False, alignment=WD_ALIGN_PARAGRAPH.LEFT,
                 line_spacing=1.5, space_before=0, space_after=0, first_line_indent=0,
                 left_indent=1.0),
}


def apply_page_layout(doc):
    for section in doc.sections:
        section.top_margin = MARGIN_TOP
        section.bottom_margin = MARGIN_BOTTOM
        section.left_margin = MARGIN_LEFT
        section.right_margin = MARGIN_RIGHT
        try:
            section.mirror_margins = False  # gutter stays fixed-left, not mirrored
        except AttributeError:
            pass


def apply_format_to_paragraph(paragraph, label: str):
    spec = PARAGRAPH_SPEC.get(label, PARAGRAPH_SPEC["Body Paragraph"])

    paragraph.alignment = spec["alignment"]
    pf = paragraph.paragraph_format
    pf.line_spacing = spec["line_spacing"]
    pf.space_before = Pt(spec["space_before"])
    pf.space_after = Pt(spec["space_after"])
    pf.first_line_indent = Cm(spec.get("first_line_indent", 0))
    if "left_indent" in spec:
        pf.left_indent = Cm(spec["left_indent"])

    runs = paragraph.runs
    if not runs and paragraph.text:
        runs = [paragraph.add_run(paragraph.text)]
    for run in runs:
        run.font.name = BODY_FONT
        run.font.size = Pt(spec["size"])
        run.font.bold = spec["bold"]
        run.font.italic = spec.get("italic", False)
        run.font.color.rgb = BODY_COLOR


def apply_format_to_table(table):
    """Tables get a consistent readable style rather than the body-text
    spec (which doesn't apply to table cells): centered, gridded, Times
    New Roman 11pt in every cell."""
    try:
        table.style = "Table Grid"
    except KeyError:
        pass  # style not present in this template -- leave existing style
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    for row in table.rows:
        for cell in row.cells:
            for p in cell.paragraphs:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                for run in p.runs:
                    run.font.name = BODY_FONT
                    run.font.size = Pt(11)
                    run.font.color.rgb = BODY_COLOR


def format_document(doc, records):
    """Apply formatting to every classified element and set page layout."""
    apply_page_layout(doc)
    for record in records:
        if record.is_table:
            apply_format_to_table(record.table)
        else:
            apply_format_to_paragraph(record.paragraph, record.label)
    return doc
