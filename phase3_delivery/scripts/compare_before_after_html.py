"""
Visual before/after comparison for the submission deliverable. Produces a
single self-contained HTML file:
  - side-by-side rendered page images (if LibreOffice/soffice is available
    on this machine -- optional, only needed to GENERATE this report, not
    part of the offline engine itself)
  - a formatting diff table (always generated, no dependencies)

Usage:
    python scripts/compare_before_after_html.py original.docx formatted.docx report.html
"""
import base64
import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "engine"))
from parser import parse_docx  # noqa: E402
from classifier_stub import classify_batch  # noqa: E402


def _soffice_available():
    return shutil.which("soffice") is not None


def _render_first_page_png(docx_path, workdir):
    """Convert page 1 of a docx to PNG via LibreOffice. Returns the PNG path
    or None if soffice/pdftoppm aren't available."""
    if not _soffice_available() or shutil.which("pdftoppm") is None:
        return None
    try:
        subprocess.run(
            ["soffice", "--headless", "--convert-to", "pdf", "--outdir", workdir, docx_path],
            check=True, capture_output=True, timeout=120,
        )
        base = os.path.splitext(os.path.basename(docx_path))[0]
        pdf_path = os.path.join(workdir, f"{base}.pdf")
        if not os.path.exists(pdf_path):
            return None
        out_prefix = os.path.join(workdir, f"{base}_page")
        subprocess.run(
            ["pdftoppm", "-png", "-r", "110", "-f", "1", "-l", "1", pdf_path, out_prefix],
            check=True, capture_output=True, timeout=60,
        )
        candidates = [f for f in os.listdir(workdir) if f.startswith(f"{base}_page")]
        return os.path.join(workdir, candidates[0]) if candidates else None
    except Exception as e:
        print(f"  (visual render skipped: {e})")
        return None


def _img_to_data_uri(path):
    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode("ascii")
    return f"data:image/png;base64,{data}"


def build_snapshot(records):
    rows = []
    for r in records:
        if r.is_table:
            rows.append({"kind": "table", "label": r.label, "text": r.text[:70],
                         "font": "-", "size": "-", "bold": "-", "align": "table"})
        else:
            p = r.paragraph
            run = p.runs[0] if p.runs else None
            rows.append({
                "kind": "paragraph", "label": r.label, "text": r.text[:70],
                "font": run.font.name if run else "-",
                "size": run.font.size.pt if run and run.font.size else "-",
                "bold": bool(run.font.bold) if run else False,
                "align": str(p.alignment).split(".")[-1] if p.alignment else "LEFT",
            })
    return rows


def main():
    if len(sys.argv) != 4:
        print("Usage: python compare_before_after_html.py <original.docx> <formatted.docx> <report.html>")
        sys.exit(1)

    original_path, formatted_path, report_path = sys.argv[1:4]

    before_records, _ = parse_docx(original_path)
    after_records, _ = parse_docx(formatted_path)

    labels = classify_batch(before_records)
    for r, (label, _) in zip(before_records, labels):
        r.label = label
    for b, a in zip(before_records, after_records):
        a.label = b.label

    before_rows = build_snapshot(before_records)
    after_rows = build_snapshot(after_records)

    # Optional visual page render
    images_html = ""
    with tempfile.TemporaryDirectory() as tmp:
        before_png = _render_first_page_png(original_path, tmp)
        after_png = _render_first_page_png(formatted_path, tmp)
        if before_png and after_png:
            before_uri = _img_to_data_uri(before_png)
            after_uri = _img_to_data_uri(after_png)
            images_html = f"""
            <div class="visual-row">
              <div class="visual-col">
                <h3>Before</h3>
                <img src="{before_uri}" alt="original page 1">
              </div>
              <div class="visual-col">
                <h3>After</h3>
                <img src="{after_uri}" alt="formatted page 1">
              </div>
            </div>
            """
        else:
            images_html = ("<p class='note'>Visual page render skipped "
                            "(install LibreOffice + poppler-utils for page-image comparison; "
                            "the formatting table below works regardless).</p>")

    table_rows_html = ""
    n_changed = 0
    for i, (b, a) in enumerate(zip(before_rows, after_rows)):
        changed = (b["font"], b["size"], b["bold"], b["align"]) != (a["font"], a["size"], a["bold"], a["align"])
        n_changed += int(changed)
        row_class = "changed" if changed else ""
        table_rows_html += f"""
        <tr class="{row_class}">
          <td>{i}</td>
          <td><span class="label-pill">{a['label']}</span></td>
          <td>{b['font']} / {b['size']}pt / {'B' if b['bold'] is True else ''} / {b['align']}</td>
          <td>{a['font']} / {a['size']}pt / {'B' if a['bold'] is True else ''} / {a['align']}</td>
          <td class="text-cell">{a['text']}</td>
        </tr>
        """

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Before / After Formatting Comparison</title>
<style>
  body {{ font-family: -apple-system, Segoe UI, Arial, sans-serif; margin: 32px; color: #1a1a2e; background: #fafafa; }}
  h1 {{ font-size: 22px; }}
  .meta {{ color: #555; font-size: 13px; margin-bottom: 24px; }}
  .visual-row {{ display: flex; gap: 24px; margin-bottom: 32px; }}
  .visual-col {{ flex: 1; text-align: center; }}
  .visual-col img {{ max-width: 100%; border: 1px solid #ddd; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }}
  .note {{ color: #888; font-style: italic; }}
  table {{ border-collapse: collapse; width: 100%; font-size: 13px; background: white; }}
  th, td {{ border: 1px solid #e0e0e0; padding: 6px 10px; text-align: left; }}
  th {{ background: #0B1F3A; color: white; }}
  tr.changed {{ background: #eef7ee; }}
  .label-pill {{ background: #4FC3F7; color: #0B1F3A; padding: 2px 8px; border-radius: 10px; font-weight: 600; font-size: 12px; }}
  .text-cell {{ color: #333; max-width: 420px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
  .summary {{ margin: 16px 0; font-size: 14px; }}
</style>
</head>
<body>
  <h1>Before / After Formatting Comparison</h1>
  <div class="meta">Original: {original_path} &nbsp;|&nbsp; Formatted: {formatted_path}</div>
  {images_html}
  <div class="summary"><strong>{n_changed}</strong> of {len(before_rows)} elements had formatting changed.</div>
  <table>
    <tr><th>#</th><th>Detected Label</th><th>Before</th><th>After</th><th>Text</th></tr>
    {table_rows_html}
  </table>
</body>
</html>"""

    with open(report_path, "w") as f:
        f.write(html)
    print(f"Wrote visual comparison -> {report_path}")


if __name__ == "__main__":
    main()
