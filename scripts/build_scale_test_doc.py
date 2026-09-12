"""
Stitches every .docx in samples/ together, repeating the list if necessary,
until the combined document reaches a target page count -- gives you a
realistic 400+ page manuscript for the scalability / performance deliverable
without needing an actual 400-page manuscript on hand.

Page count is estimated (~450 words/page for 12pt double-spaced-ish body
text) since python-docx has no native page counter; treat it as a rough
target, not an exact one. If your final estimate is off, re-run with a
higher TARGET_PAGES buffer or check the actual page count by opening the
output in Word/LibreOffice (bottom status bar).

Usage (from repo root):
    python scripts/build_scale_test_doc.py --target-pages 400
"""
import argparse
import glob
import os

from docx import Document

WORDS_PER_PAGE_ESTIMATE = 450


def count_words(doc: Document) -> int:
    total = 0
    for p in doc.paragraphs:
        total += len(p.text.split())
    for t in doc.tables:
        for row in t.rows:
            for cell in row.cells:
                total += len(cell.text.split())
    return total


def append_document(target: Document, source_path: str):
    """Append every block-level element of source_path onto target, in order."""
    source = Document(source_path)
    for element in source.element.body:
        target.element.body.append(element)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-pages", type=int, default=400)
    parser.add_argument("--samples-dir", default=os.path.join(os.path.dirname(__file__), "..", "samples"))
    parser.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "..", "samples", "scale_test_manuscript.docx"))
    args = parser.parse_args()

    docx_files = sorted(glob.glob(os.path.join(args.samples_dir, "*.docx")))
    docx_files = [f for f in docx_files if "formatted" not in f and "scale_test" not in f]
    if not docx_files:
        print(f"No source .docx files found in {args.samples_dir}")
        return

    target_words = args.target_pages * WORDS_PER_PAGE_ESTIMATE
    print(f"Stitching from {len(docx_files)} source docs, target ~{args.target_pages} "
          f"pages (~{target_words} words)...")

    combined = Document(docx_files[0])
    running_words = count_words(combined)
    i = 1
    while running_words < target_words:
        source_path = docx_files[i % len(docx_files)]
        append_document(combined, source_path)
        running_words = count_words(combined)
        i += 1
        if i > len(docx_files) * 200:  # safety valve
            print("Safety limit hit -- stopping early.")
            break

    combined.save(args.out)
    est_pages = running_words / WORDS_PER_PAGE_ESTIMATE
    print(f"Saved {args.out}")
    print(f"~{running_words} words, ~{est_pages:.0f} estimated pages "
          f"(open it in Word/LibreOffice to confirm the real page count)")


if __name__ == "__main__":
    main()
