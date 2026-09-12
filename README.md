# Manuscript Auto-Formatter — Person B / Engineering

This is the **offline engineering pipeline** (Person B's part). It runs
entirely on a normal computer — no internet, no Colab, no cloud calls at any
point. Person A's Colab notebook lives in `model/train.ipynb` for reference;
you don't need Colab to run anything in this folder.

```
ManuscriptFormatter/
├── README.md                 <- you are here
├── engine/
│   ├── parser.py              DOCX -> feature vectors (paragraphs + tables, in order)
│   ├── classifier_stub.py     loads Person A's model if present, else rule-based stub
│   ├── formatting_engine.py   applies the publication spec via OOXML
│   ├── validation.py          integrity checks (valid file, no text loss, styles applied)
│   ├── main_pipeline.py       wires it all together — THIS is what you run
│   └── requirements.txt
├── model/
│   ├── train.ipynb            Person A's notebook (Colab only, reference)
│   ├── feature_spec.md        SHARED CONTRACT — read this if anything seems off
│   └── artifacts/             <- drop classifier.joblib + scaler.joblib here (empty for now)
├── samples/                   15 synthetic manuscripts, ready to test with
└── scripts/
    ├── run_all_samples.py         batch-runs the pipeline over every sample doc
    ├── build_scale_test_doc.py    stitches samples into a 400+ page doc for scale testing
    └── compare_before_after.py    generates the before/after comparison deliverable
```

## 1. Where to run this

Any regular machine — Windows, Mac, or Linux — with Python 3.9+. This is the
"offline app" itself, so run it wherever you'll demo from. No GPU, no
internet connection needed once packages are installed.

## 2. One-time setup

```bash
cd ManuscriptFormatter
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r engine/requirements.txt
```

That's it — `scikit-learn` is intentionally **not** in the base
`requirements.txt` yet (see step 5). Everything else runs today, using the
rule-based stub in place of the trained model.

## 3. Run it on one file

```bash
cd engine
python main_pipeline.py ../samples/manuscript_01.docx ../samples/manuscript_01_formatted.docx
```

Expected output:

```
[1/4] Parsed 165 elements from ../samples/manuscript_01.docx (161 paragraphs, 4 tables)
[classifier] No classifier.joblib found in model/artifacts/ -- using rule-based stub.
[2/4] Classified elements: {'Title': 1, 'Body Paragraph': 118, ...}
[3/4] Formatted and saved to ../samples/manuscript_01_formatted.docx
[4/4] Validation PASSED
Done in 0.36s (165 elements, 454.8 elements/sec)
```

Open the two files side by side in Word/LibreOffice to see the effect.

## 4. Run it on everything at once

```bash
cd ManuscriptFormatter          # repo root
python scripts/run_all_samples.py
```

Formats all 15 sample docs, writes them to `samples/formatted/`, and prints
a summary — already verified: **all 15 pass validation** in ~4.6s total.

## 5. Plugging in Person A's trained model (Phase 2)

No code changes needed on your side. Once Person A hands off:

- `classifier.joblib`
- `scaler.joblib`
- `feature_spec.md` (regenerated — diff it against `model/feature_spec.md`, they should match)
- `requirements.txt` (contains the exact `scikit-learn==X.Y.Z` pin)

Do this:

```bash
cp <handoff>/classifier.joblib <handoff>/scaler.joblib model/artifacts/
cat <handoff>/requirements.txt   # copy the scikit-learn==X.Y.Z line
echo "scikit-learn==X.Y.Z" >> engine/requirements.txt   # use the real version printed
pip install -r engine/requirements.txt
```

Re-run `main_pipeline.py` on any sample — the first console line changes
from `"using rule-based stub"` to `"Loaded trained model from ..."`. Nothing
else changes; `classify()` is the single call site every other file uses.

**Verify the switch actually happened** — this is the #1 thing to sanity
check before a demo:

```bash
python -c "
import sys; sys.path.insert(0, 'engine')
from classifier_stub import load_real_model
print('Model loaded:', load_real_model())
"
```

## 6. Scale test (400+ pages deliverable)

```bash
python scripts/build_scale_test_doc.py --target-pages 400
cd engine
python main_pipeline.py ../samples/scale_test_manuscript.docx ../samples/scale_test_formatted.docx
```

Already tested: a ~412-page stitched manuscript (4,675 elements) formats in
**~6.2 seconds** (~750 elements/sec) and passes validation. Use the printed
elapsed time / rate directly in your performance-evaluation deliverable.
Memory: for a rough number, wrap the run with `/usr/bin/time -v python ...`
(Linux/Mac) or Task Manager's peak working set (Windows) while it runs.

## 7. Before/after comparison deliverable

```bash
cd engine
python main_pipeline.py ../samples/manuscript_03.docx ../samples/manuscript_03_formatted.docx
cd ..
python scripts/compare_before_after.py samples/manuscript_03.docx samples/manuscript_03_formatted.docx samples/manuscript_03_comparison.md
```

Produces a markdown table: per element, its detected label plus font/size/
bold/alignment before vs. after. For a visual side-by-side, also render both
`.docx` files to PDF (LibreOffice: `soffice --headless --convert-to pdf
file.docx`) and screenshot page 1 of each next to each other.

## 8. What "Table"/"Figure" actually means here

Person A's updated notebook walks the document body in order and treats
each `<w:tbl>` as **one** feature row (not per-cell), and any paragraph
containing an image as `has_image=1`. `rule_based_override()` in
`classifier_stub.py` forces `is_table_element -> "Table"` and
`has_image -> "Figure"` deterministically — the ML model never actually
has to guess these two classes, it only disambiguates the text-based ones
(Title, Author, Heading, Subheading, Body, Caption, Reference, List).
`formatting_engine.py` has a separate code path for tables
(`apply_format_to_table`) since python-docx tables don't expose the same
paragraph-level formatting API.

## 9. Integration checklist

- [x] Pipeline runs end-to-end on all 15 sample docs with rule-based stub — verified
- [x] Scale test passes on a ~412-page stitched manuscript — verified
- [ ] `model/artifacts/classifier.joblib` + `scaler.joblib` dropped in
- [ ] `engine/requirements.txt` pinned to the exact sklearn version from Colab
- [ ] Console confirms `"Loaded trained model"` (not the rule-based stub) on a real run
- [ ] Re-run `scripts/run_all_samples.py`, confirm still 100% pass after swapping in the real model
- [ ] Person A reviews any misclassifications on actual pipeline output, retrains if needed
- [ ] Generate final before/after comparison + performance report for submission
