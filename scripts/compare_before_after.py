"""
Generates the "before-and-after comparison" deliverable: a markdown report
showing, per element, the detected label and a snapshot of key formatting
properties before vs. after. Pair this with rendered PDFs (see README) for
the visual side of the comparison.

Usage:
    python scripts/compare_before_after.py original.docx formatted.docx report.md
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "engine"))
from parser import parse_docx  # noqa: E402


def snapshot(records):
    rows = []
    for r in records:
        if r.is_table:
            rows.append({"kind": "table", "label": r.label, "text": r.text[:60]})
        else:
            p = r.paragraph
            run = p.runs[0] if p.runs else None
            rows.append({
                "kind": "paragraph",
                "label": r.label,
                "text": r.text[:60],
                "font": run.font.name if run else None,
                "size": run.font.size.pt if run and run.font.size else None,
                "bold": bool(run.font.bold) if run else None,
                "align": str(p.alignment),
            })
    return rows


def main():
    if len(sys.argv) != 4:
        print("Usage: python compare_before_after.py <original.docx> <formatted.docx> <report.md>")
        sys.exit(1)

    original_path, formatted_path, report_path = sys.argv[1:4]

    before_records, _ = parse_docx(original_path)
    after_records, _ = parse_docx(formatted_path)

    # classify the "before" set too, purely for the report (uses the same
    # classify() the pipeline used, re-imported here to avoid double logic)
    from classifier_stub import classify
    for r in before_records:
        label, _ = classify(r)
        r.label = label
    # Formatting never reorders/adds/drops elements, so positional labels
    # from the "before" pass apply directly to the "after" elements too.
    for b, a in zip(before_records, after_records):
        a.label = b.label

    before_snap = snapshot(before_records)
    after_snap = snapshot(after_records)

    lines = ["# Before / After Formatting Comparison\n"]
    lines.append(f"- Original: `{original_path}`\n")
    lines.append(f"- Formatted: `{formatted_path}`\n")
    lines.append(f"- Elements compared: {min(len(before_snap), len(after_snap))}\n\n")
    lines.append("| # | Label | Before (font / size / bold / align) | After (font / size / bold / align) | Text |\n")
    lines.append("|---|-------|----------------------------------------|---------------------------------------|------|\n")

    for i, (b, a) in enumerate(zip(before_snap, after_snap)):
        if b["kind"] == "table":
            before_str = "table"
            after_str = "table (reformatted)"
        else:
            before_str = f"{b['font']} / {b['size']} / {b['bold']} / {b['align']}"
            after_str = f"{a['font']} / {a['size']} / {a['bold']} / {a['align']}"
        lines.append(f"| {i} | {a['label']} | {before_str} | {after_str} | {a['text']} |\n")

    with open(report_path, "w") as f:
        f.writelines(lines)
    print(f"Wrote comparison report -> {report_path}")


if __name__ == "__main__":
    main()
