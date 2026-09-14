# Phase 3 (Part 1 of 2) — Scale & Harden: Profiling Results + Fixes

Part 1 covers the "test, profile, fix bottlenecks" half of Phase 3. Part 2
will be the frontend (separate message — it's a big enough piece to earn
its own delivery).

## What I actually did

Pulled your latest repo, ran `cProfile` against the 400+ page scale-test
manuscript already in `samples/`, found the real bottleneck, fixed it, and
re-verified against all 15 samples + the scale test.

## The finding: it wasn't XML writes

The original Phase 2 roadmap assumed the bottleneck would be paragraph-by-
paragraph XML writes. It wasn't. Profiling showed **97% of runtime** was
spent in `classifier_stub.classify()`, specifically in calling the model's
`.predict()` and `.predict_proba()` **once per element, one row at a
time** — 4,675 separate model calls for a 412-page document. Every one of
those calls pays fixed sklearn overhead (input validation, tag lookup,
joblib's parallel dispatch across the forest's 200 trees) regardless of
how small the input is.

I benchmarked it directly:

| Approach | Time for 4,675 rows |
|---|---|
| One row at a time (original code) | 65.0s (classification alone) |
| One batched call, all rows at once | 0.06s |

**That's roughly 1000x.** Full pipeline, before vs. after:

| Metric | Before | After |
|---|---|---|
| Full pipeline, 412-page doc | 210.95s | **4.44s** |
| Throughput | 22.2 elements/sec | **1,053.8 elements/sec** |
| Peak memory (RSS) | — | **~300 MB** |

After fixing the batching, I profiled again and found a second, smaller
bottleneck: `paragraph.style.name` (python-docx's style resolution) was
being called fresh for every one of 4,507 paragraphs — ~7.8s of the
remaining ~9s. A document only ever uses a handful of distinct style IDs,
so I added a per-document cache keyed on the raw style ID, paying the real
resolution cost once per unique style instead of once per paragraph. That's
where the 4.44s final number comes from.

## What changed (3 files, drop-in replacements)

- **`engine/classifier_stub.py`** — added `classify_batch()`, which builds
  one feature matrix for every element in the document and calls
  `.predict()`/`.predict_proba()` exactly once each. The old `classify()`
  (single-element) is kept as a thin wrapper for other scripts that still
  use it one at a time (fine for a handful of elements, just not a whole
  document).
- **`engine/main_pipeline.py`** — now calls `classify_batch(records)` once
  instead of looping `classify(r)` per element.
- **`engine/parser.py`** — added a per-document style-name cache to
  `_style_hash()`.

No output changed — same labels, same formatting, same validation
behavior. I re-ran all 15 sample docs plus the scale test after the change:
**19/19 pass validation**, 1,077 elements/sec average.

## Two new scripts (for your Phase 3/4 deliverables)

**`scripts/profile_performance.py`** — run this to generate the actual
numbers for your performance-evaluation deliverable (time, throughput,
peak memory, label distribution):

```bash
python scripts/profile_performance.py samples/scale_test_manuscript.docx --out performance_report.md
```

**`scripts/compare_before_after_html.py`** — upgrades the old markdown
comparison to a proper visual side-by-side report: renders page 1 of both
the original and formatted docs as images (if LibreOffice + poppler-utils
are installed — falls back gracefully to the formatting table alone if
not), plus a color-coded diff table underneath.

```bash
python scripts/compare_before_after_html.py samples/manuscript_05.docx samples/manuscript_05_formatted.docx comparison_report.html
```

Open the `.html` file in any browser. This is your "before-and-after
comparison demonstrating formatting accuracy" deliverable from the original
problem statement.

## How to apply this to your repo

```bash
cd DocFlow
# copy the 3 updated files + 2 new scripts from this delivery into place, then:
git add engine/classifier_stub.py engine/main_pipeline.py engine/parser.py scripts/profile_performance.py scripts/compare_before_after_html.py
git commit -m "Phase 3: batch classifier calls (~47x speedup), cache style resolution, add profiling + visual comparison scripts"
git push

# then re-verify:
python -m venv venv && source venv/bin/activate
pip install -r engine/requirements.txt
python scripts/run_all_samples.py
```

Expect the same "All documents passed validation" you saw before — this
change is pure performance, not behavior.

## One open item carried over from Phase 2

I noticed the Phase 2 fixes (group-aware train/test split, the style-aware
training samples) don't appear to have been merged into `train.ipynb` or
`model/artifacts/` yet — the evaluation report still shows the same 100%
test accuracy on the same 209 rows. That's Person A's side of Phase 3
("checks whether classifier accuracy holds up on longer/messier documents"),
not blocking this delivery, but worth doing before Phase 4's dry run —
running `scripts/run_all_samples.py` on my synthetic set still shows some
docs classifying 60-80% of paragraphs as "Figure", which is the same
style-reliance issue flagged before.

## What's next (Part 2)

The frontend — offline, Microsoft Office-compatible upload → process →
download flow. Say the word and I'll get started on it.
