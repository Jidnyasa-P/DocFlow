"""
Batch-run the pipeline over every .docx in samples/, writing formatted
output next to each one. Useful for a quick smoke test across your whole
sample set in one command.

Usage (from repo root):
    python scripts/run_all_samples.py
"""
import glob
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "engine"))
from main_pipeline import run_pipeline  # noqa: E402

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
SAMPLES_DIR = os.path.join(REPO_ROOT, "samples")
OUT_DIR = os.path.join(REPO_ROOT, "samples", "formatted")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    docx_files = sorted(glob.glob(os.path.join(SAMPLES_DIR, "*.docx")))
    if not docx_files:
        print(f"No .docx files found in {SAMPLES_DIR}")
        return

    print(f"Running pipeline on {len(docx_files)} sample document(s)...\n")
    total_elapsed = 0.0
    total_elements = 0
    failures = []

    for path in docx_files:
        name = os.path.basename(path)
        out_path = os.path.join(OUT_DIR, name.replace(".docx", "_formatted.docx"))
        print(f"--- {name} ---")
        try:
            report, elapsed, label_counts = run_pipeline(path, out_path, verbose=False)
            total_elapsed += elapsed
            total_elements += sum(label_counts.values())
            status = "OK" if report.ok else "FAILED VALIDATION"
            print(f"  {status} | {elapsed:.2f}s | {sum(label_counts.values())} elements "
                  f"| {label_counts}")
            if not report.ok:
                failures.append(name)
                for e in report.errors[:3]:
                    print(f"    - {e}")
        except Exception as e:
            failures.append(name)
            print(f"  ERROR: {e}")
        print()

    print("=" * 60)
    print(f"Processed {len(docx_files)} docs in {total_elapsed:.2f}s total "
          f"({total_elements} elements, {total_elements / max(total_elapsed, 0.001):.1f}/sec)")
    if failures:
        print(f"{len(failures)} doc(s) failed validation or errored: {failures}")
    else:
        print("All documents passed validation.")


if __name__ == "__main__":
    main()
