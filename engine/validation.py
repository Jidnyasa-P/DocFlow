"""
Validation & Integrity Check (Person B / Engineering)

Confirms the output DOCX:
  1. Is valid OOXML (opens cleanly)
  2. Preserves all original paragraph text, in order, unchanged
  3. Preserves the same number of tables, with cell text unchanged
  4. Has every element labelled and formatting actually applied
"""
from docx import Document
from docx.oxml.ns import qn


class ValidationReport:
    def __init__(self):
        self.errors = []
        self.warnings = []

    @property
    def ok(self):
        return len(self.errors) == 0

    def add_error(self, msg):
        self.errors.append(msg)

    def add_warning(self, msg):
        self.warnings.append(msg)

    def summary(self):
        lines = [f"Validation {'PASSED' if self.ok else 'FAILED'}"]
        if self.errors:
            lines.append(f"  {len(self.errors)} error(s):")
            lines += [f"    - {e}" for e in self.errors]
        if self.warnings:
            lines.append(f"  {len(self.warnings)} warning(s):")
            lines += [f"    - {w}" for w in self.warnings]
        return "\n".join(lines)


def check_valid_ooxml(path: str, report: ValidationReport):
    try:
        Document(path)
    except Exception as e:
        report.add_error(f"Output file is not valid OOXML / failed to open: {e}")


def check_paragraph_text_integrity(original_paragraph_texts, output_path: str, report: ValidationReport):
    """Every non-empty paragraph's text from the original must still be
    present, in order, in the output. Table cell text is checked separately
    (check_table_integrity) since it isn't in doc.paragraphs."""
    try:
        out_doc = Document(output_path)
    except Exception:
        return  # already reported by check_valid_ooxml

    output_texts = [p.text.strip() for p in out_doc.paragraphs if p.text.strip()]

    if len(original_paragraph_texts) != len(output_texts):
        report.add_warning(
            f"Paragraph count changed: {len(original_paragraph_texts)} original vs "
            f"{len(output_texts)} output (formatting should never add/drop paragraphs)")

    mismatches = 0
    for i, (orig, out) in enumerate(zip(original_paragraph_texts, output_texts)):
        if orig != out:
            mismatches += 1
            if mismatches <= 5:
                report.add_error(
                    f"Paragraph {i} text changed:\n"
                    f"      orig: {orig[:80]!r}\n      out:  {out[:80]!r}")
    if mismatches > 5:
        report.add_error(f"...and {mismatches - 5} more paragraph text mismatches")


def check_table_integrity(original_path: str, output_path: str, report: ValidationReport):
    try:
        orig_doc = Document(original_path)
        out_doc = Document(output_path)
    except Exception:
        return

    if len(orig_doc.tables) != len(out_doc.tables):
        report.add_error(
            f"Table count changed: {len(orig_doc.tables)} original vs "
            f"{len(out_doc.tables)} output")
        return

    for ti, (ot, nt) in enumerate(zip(orig_doc.tables, out_doc.tables)):
        orig_cells = [c.text.strip() for row in ot.rows for c in row.cells]
        new_cells = [c.text.strip() for row in nt.rows for c in row.cells]
        if orig_cells != new_cells:
            report.add_error(f"Table {ti} cell text changed after formatting")


def check_style_consistency(records, report: ValidationReport):
    """Confirm every element has a label and formatting was actually applied."""
    unlabeled = [r for r in records if not r.label]
    if unlabeled:
        report.add_error(f"{len(unlabeled)} element(s) have no label assigned")

    for r in records:
        if r.is_table:
            continue
        if r.paragraph.runs:
            run = r.paragraph.runs[0]
            if run.font.name is None:
                report.add_warning(f"Element {r.order_index} ({r.label}) has no font name set")


def validate_output(original_paragraph_texts, original_path: str, output_path: str, records) -> ValidationReport:
    report = ValidationReport()
    check_valid_ooxml(output_path, report)
    check_paragraph_text_integrity(original_paragraph_texts, output_path, report)
    check_table_integrity(original_path, output_path, report)
    check_style_consistency(records, report)
    return report
