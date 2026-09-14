"""
Performance profiling for the submission's performance-evaluation deliverable.

Measures wall-clock time and peak memory (RSS) for running the full
pipeline on a given document, and writes a markdown report.

Usage:
    python scripts/profile_performance.py samples/scale_test_manuscript.docx
    python scripts/profile_performance.py samples/scale_test_manuscript.docx --out perf_report.md
"""
import argparse
import os
import resource
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "engine"))
from main_pipeline import run_pipeline  # noqa: E402


def peak_rss_mb() -> float:
    """Peak resident set size in MB, since process start (Linux/Mac)."""
    kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    # Linux reports KB, macOS reports bytes -- normalize.
    return kb / 1024 if sys.platform != "darwin" else kb / (1024 * 1024)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input_docx")
    ap.add_argument("--out", default=None, help="write a markdown report here")
    ap.add_argument("--output-docx", default="/tmp/profiled_output.docx")
    args = ap.parse_args()

    mem_before = peak_rss_mb()
    t0 = time.time()
    report, elapsed, label_counts = run_pipeline(args.input_docx, args.output_docx, verbose=True)
    mem_after = peak_rss_mb()

    n_elements = sum(label_counts.values())
    rate = n_elements / elapsed if elapsed > 0 else float("inf")

    lines = [
        "# Performance Evaluation Report\n\n",
        f"- Input file: `{args.input_docx}`\n",
        f"- Elements processed: {n_elements}\n",
        f"- Wall-clock time: {elapsed:.2f}s\n",
        f"- Throughput: {rate:.1f} elements/sec\n",
        f"- Peak memory (RSS): {mem_after:.1f} MB (baseline before run: {mem_before:.1f} MB)\n",
        f"- Validation: {'PASSED' if report.ok else 'FAILED'}\n\n",
        "## Label distribution\n\n",
    ]
    for label, count in sorted(label_counts.items(), key=lambda x: -x[1]):
        lines.append(f"- {label}: {count}\n")

    if report.warnings:
        lines.append("\n## Warnings\n\n")
        for w in report.warnings:
            lines.append(f"- {w}\n")

    text = "".join(lines)
    print("\n" + text)

    if args.out:
        with open(args.out, "w") as f:
            f.write(text)
        print(f"Wrote report -> {args.out}")


if __name__ == "__main__":
    main()
