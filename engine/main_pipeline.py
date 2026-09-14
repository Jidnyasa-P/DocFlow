"""
End-to-end pipeline (Person B / Engineering)

DOCX in -> parse (paragraphs + tables, in order) -> classify each element ->
apply formatting -> save -> validate -> report.

Usage:
    python main_pipeline.py input.docx output.docx
"""
import sys
import time

from parser import parse_docx
from classifier_stub import classify_batch
from formatting_engine import format_document
from validation import validate_output


def run_pipeline(input_path: str, output_path: str, verbose: bool = True):
    t0 = time.time()

    # 1. Parse + extract features (paragraphs and tables, in document order)
    records, doc = parse_docx(input_path)
    original_paragraph_texts = [r.text for r in records if not r.is_table]
    n_tables = sum(1 for r in records if r.is_table)
    if verbose:
        print(f"[1/4] Parsed {len(records)} elements from {input_path} "
              f"({len(records) - n_tables} paragraphs, {n_tables} tables)")

    # 2. Classify all elements in ONE batched model call (real model if
    # available, else rule-based stub) -- see classifier_stub.classify_batch
    # for why this matters: one-at-a-time was ~1000x slower.
    label_counts = {}
    results = classify_batch(records)
    for r, (label, confidence) in zip(records, results):
        r.label = label
        r.label_confidence = confidence
        label_counts[label] = label_counts.get(label, 0) + 1
    if verbose:
        print(f"[2/4] Classified elements: {label_counts}")

    # 3. Apply formatting per label + save
    format_document(doc, records)
    doc.save(output_path)
    if verbose:
        print(f"[3/4] Formatted and saved to {output_path}")

    # 4. Validate
    report = validate_output(original_paragraph_texts, input_path, output_path, records)
    if verbose:
        print(f"[4/4] {report.summary()}")

    elapsed = time.time() - t0
    if verbose:
        rate = len(records) / elapsed if elapsed > 0 else float("inf")
        print(f"\nDone in {elapsed:.2f}s ({len(records)} elements, {rate:.1f} elements/sec)")

    return report, elapsed, label_counts


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python main_pipeline.py <input.docx> <output.docx>")
        sys.exit(1)
    report, _, _ = run_pipeline(sys.argv[1], sys.argv[2])
    sys.exit(0 if report.ok else 1)
