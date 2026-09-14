# Phase 2 — Integration Report & Next Steps

I pulled `DocFlow` from GitHub and actually ran the full integration —
loaded your real `classifier.joblib`/`scaler.joblib`, ran it against all 15
samples plus a fresh set of test documents, and ran the 400+ page scale
test. Here's what's confirmed working, what I found, and exactly what to do
next.

## What's confirmed working

- `model/artifacts/classifier.joblib` + `scaler.joblib` load correctly —
  console prints `"Loaded trained model from ... (with scaler)"` instead of
  the rule-based stub fallback
- All 15 sample docs process end-to-end (parse → classify → format →
  validate) and **pass validation** with the real model
- Scale test: a ~412-page stitched manuscript (4,675 elements) completes in
  well under a minute and passes validation
- `engine/requirements.txt` already had `scikit-learn==1.6.1` pinned — good.
  I tested loading the model with `1.8.0` installed vs `1.6.1`: the mismatch
  throws `InconsistentVersionWarning` on every estimator; the exact pin
  loads with **zero warnings**. Keep that pin.

## What I found (the actual point of integration testing)

I generated 6 new test manuscripts your model had never seen and checked
its real-world accuracy — not the 100% the notebook reported, but what
happens on genuinely unseen documents:

**Result: 63% accuracy**, with two clear, fixable patterns:

1. **`List` is misclassified as `Table` 100% of the time; `Subheading` is
   misclassified 100% of the time (mostly as `List`).** Root cause: the
   model relies heavily on `style_name_hash` (which Word style a paragraph
   uses). Your training manuscripts apparently use real Word styles
   (Heading 1/2, List Paragraph, etc.) consistently, so the model leaned
   hard on that one feature. It works great as long as every input document
   also uses proper Word styles — but it's a single point of failure for
   any manuscript that doesn't (plain "Normal"-styled text is extremely
   common in real unformatted submissions).

2. **The notebook's reported 100% test accuracy is misleading.** The
   `train_test_split` splits individual *paragraphs* at random, not
   *documents*. Paragraphs from the same manuscript share fonts/styles/
   layout, so rows from one document end up on both sides of the split —
   the model is partly being "tested" on documents it already trained on.
   That's why the notebook says 100% but real unseen manuscripts only hit
   63%.

Neither of these is a bug in the engine (Person B's side is working exactly
as designed) — both are training-data/methodology issues on the model side,
which is exactly what Phase 2 is for catching before the final submission.

## What to do next (in order)

### 1. Fix the evaluation methodology (~15 min, Person A, in Colab)

Open `model/train.ipynb`, find the "Train classifier" cell, and replace it
with the code in **`group_aware_split_patch.py`** (included below) — it
splits by `source_doc` using `GroupShuffleSplit`/`GroupKFold` instead of by
row, so no document leaks between train and test. Re-run from that cell
onward. Expect the reported accuracy to drop from 100% — that's the honest
number, use it in your performance-evaluation deliverable instead of the
old one.

### 2. Add more training data, especially for the weak classes (Person A)

I generated **6 new manuscripts with real Word styles applied** (Title,
Heading 1, Heading 2, List Paragraph, Caption) plus ground-truth labels for
every paragraph — `style_aware_samples.zip`, included below. These are
exactly the `List`/`Subheading`/`Title` examples your model is currently
weakest on.

1. Upload `style_aware_samples.zip` to `MyDrive/HackNIMA/`, unzip it
2. Copy `samples_style_aware/*.docx` into your existing `samples/` folder
   (or point `SAMPLE_DIR` at both)
3. Copy `ground_truth_style_aware/*_labels.csv` into your `ground_truth/`
   folder so they auto-fill instead of needing hand-labeling
4. Re-run the notebook from Section 4 (feature extraction) onward with the
   larger, more diverse dataset

### 3. Retrain and re-export (Person A)

Run through to Section 6 as before. Drop the new `classifier.joblib` +
`scaler.joblib` into `model/artifacts/`, overwriting the old ones.

### 4. Re-verify on Person B's side (both, ~5 min)

```bash
cd DocFlow
python scripts/run_all_samples.py
python -c "import sys; sys.path.insert(0,'engine'); from classifier_stub import load_real_model; print(load_real_model())"
```

Confirm it still says `"Loaded trained model"` and check the label
breakdown per doc looks sane (no more suspiciously high `Figure` or `Table`
counts on documents that don't have many actual figures/tables).

### 5. Clean up repo hygiene (Person B, ~10 min)

Your repo currently has `engine/__pycache__/*.pyc` and several duplicate
generated files (`manuscript_01_formatted_formatted.docx` — looks like the
pipeline was accidentally run on its own output) committed to git. Use the
`.gitignore` below, then:

```bash
git rm -r --cached engine/__pycache__
git rm --cached samples/formatted -r 2>/dev/null
git rm --cached samples/*_formatted_formatted.docx samples/scale_test_manuscript.docx samples/scale_test_formatted.docx samples/*_comparison.md 2>/dev/null
git add .gitignore engine/requirements.txt
git commit -m "Phase 2: gitignore cleanup, pin scikit-learn exactly, add style-aware samples"
git push
```

### 6. Then continue the original Phase 2 checklist

- [ ] Person A retrains with group-aware split + expanded data (steps 1-3 above)
- [ ] Person B re-verifies (step 4)
- [ ] Re-run `scripts/compare_before_after.py` on a couple of docs for the
      submission deliverable, now that classifications are more trustworthy
- [ ] Re-run the scale test (`scripts/build_scale_test_doc.py`) and record
      the new timing for the performance report

## Files in this delivery

| File | What it's for |
|---|---|
| `.gitignore` | drop into repo root, replaces the current one-line version |
| `engine/requirements.txt` | updated: python-docx/joblib/numpy bumped to latest stable, scikit-learn kept pinned at 1.6.1 (verified clean load) |
| `group_aware_split_patch.py` | paste into `train.ipynb`'s training cell — fixes the leaky train/test split |
| `style_aware_samples.zip` | 6 new manuscripts + ground truth, real Word styles applied — add to training data |

## Where and how to run all of this

Same as before — this is all local/offline, not Colab (except the notebook
patch, which is Colab as always):

```bash
git clone https://github.com/Jidnyasa-P/DocFlow.git
cd DocFlow
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r engine/requirements.txt
python scripts/run_all_samples.py     # sanity check everything still works
```
