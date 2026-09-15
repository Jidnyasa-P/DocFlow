# DocFlow — Offline ML-Based DOCX-to-Publication Formatting System

DocFlow takes an unformatted Word manuscript and turns it into a
publication-ready book: it detects titles, headings, body text, tables,
figures, captions, references, and lists, then applies a fixed publication
spec (Times New Roman, justified body text, 1.5 line spacing, 1.27cm
first-line indent, defined margins, styled headings) — all offline, with no
generative AI, LLM, or cloud service involved anywhere in the pipeline.

It's usable two ways: as a **Word add-in** (task pane, with a drag-to-reveal
before/after slider), or as a **standalone local web page** that works with
`.docx` files from Word or LibreOffice Writer alike.

This document walks through the whole project from a clean checkout to a
working, distributable deliverable.

---

## 1. How it's built

The pipeline has five stages, matching the architecture diagram:

1. **DOCX Parser & Feature Extraction** (`engine/parser.py`) — walks the
   document body in order (paragraphs and tables interleaved), and for
   every element computes a 16-column feature vector: font size, bold/
   italic, alignment, indentation, spacing, line spacing, whether the text
   starts with a number, word count, position in the document, which Word
   style it uses, whether it contains an image, and whether it's a table.
2. **Hybrid ML + Rule-Based Structure Recognition** (`engine/classifier_stub.py`) —
   a scikit-learn classifier (trained in `model/train.ipynb`) predicts one
   of ten labels (Title, Author, Chapter Heading, Subheading, Body
   Paragraph, Table, Figure, Caption, Reference, List) for every element in
   one batched call. A rule-based layer then deterministically overrides
   the label for anything that's structurally a table or contains an
   image, and catches a few other high-confidence patterns (chapter
   headings, numbered references) by regex.
3. **Formatting Engine** (`engine/formatting_engine.py`) — applies the
   publication spec per label by writing OOXML properties directly, and
   sets page margins/layout for the whole document.
4. **Validation & Integrity Check** (`engine/validation.py`) — confirms the
   output is valid OOXML, that no paragraph text was added, dropped, or
   changed, that table content is unchanged, and that every element
   actually got a label and formatting applied.
5. **Output** — a new, publication-ready `.docx`, openable natively in
   Word or LibreOffice.

`engine/main_pipeline.py` wires all four stages together; everything else
in the repo (the Colab notebook, the scripts, the Word add-in, the
standalone page, the packaged executable) is a different way of driving
that same pipeline.

---

## 2. Repository layout

```
DocFlow/
├── engine/                 the offline pipeline itself
│   ├── parser.py             DOCX -> feature vectors
│   ├── classifier_stub.py    loads the trained model, batches predictions, applies rules
│   ├── formatting_engine.py  applies the publication spec
│   ├── validation.py         integrity checks
│   ├── main_pipeline.py      orchestrates the four stages
│   └── requirements.txt
├── model/
│   ├── train.ipynb           Colab notebook: feature extraction, labeling, training, export
│   ├── feature_spec.md       the exact feature schema -- the contract between the notebook and the engine
│   └── artifacts/            classifier.joblib, scaler.joblib, evaluation_report.md
├── samples/                  sample manuscripts for testing
├── scripts/
│   ├── run_all_samples.py            batch-runs the pipeline over every sample
│   ├── build_scale_test_doc.py       stitches samples into a 400+ page doc for scale testing
│   ├── profile_performance.py        timing + memory numbers for the performance report
│   ├── compare_before_after.py       before/after comparison, markdown output
│   └── compare_before_after_html.py  before/after comparison, visual HTML output
├── addin/                    Word add-in + standalone browser frontend
│   ├── manifest.xml            Word add-in manifest
│   ├── taskpane.html/js        task pane (runs inside Word)
│   ├── standalone.html/js      browser-only mode (Word or LibreOffice files, no sideloading)
│   ├── taskpane.css            shared styling for both
│   └── assets/                 icons
├── server/
│   ├── app.py                 local HTTPS server: serves both frontends + the formatting API
│   └── certs.py                generates a self-signed local certificate (no Node.js needed)
├── build_exe.py              packages everything into one standalone executable (PyInstaller)
├── trust_certificate.ps1     one-time, no-admin certificate trust step for end users
├── ADDIN_README.md           Word/LibreOffice setup and sideloading instructions
└── DEPLOYMENT.md             building and distributing the packaged executable
```

---

## 3. From a clean checkout to a working local pipeline

Clone the repo and set up a Python environment:

```bash
git clone https://github.com/Jidnyasa-P/DocFlow.git
cd DocFlow
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r engine/requirements.txt
```

`engine/requirements.txt` pins `scikit-learn` to the exact version the
model in `model/artifacts/` was trained with. Don't bump that pin without
retraining — a version mismatch loads with warnings and can silently
change predictions.

Run the pipeline on a single sample document:

```bash
cd engine
python main_pipeline.py ../samples/manuscript_01.docx ../samples/manuscript_01_formatted.docx
```

This prints each stage as it runs (parse, classify, format, validate) and
reports elements processed and throughput. Open the two files side by side
to see the effect.

Run it across every sample at once:

```bash
cd ..
python scripts/run_all_samples.py
```

---

## 4. Training or retraining the classifier

The classifier is trained in Google Colab, not locally — `model/train.ipynb`
expects your sample manuscripts and their ground-truth labels to live on
Google Drive.

Open the notebook in Colab, mount Drive when prompted, and it will look for
manuscripts under `MyDrive/HackNIMA/samples/` and any matching ground-truth
CSVs under `MyDrive/HackNIMA/ground_truth/`. Documents without a
ground-truth file get a heuristic first-pass label that you then correct by
hand in a spreadsheet before training.

The notebook extracts the same 16-column feature vector described in
`model/feature_spec.md`, trains a Random Forest classifier, evaluates it,
and exports three files to `MyDrive/HackNIMA/artifacts/`:
`classifier.joblib`, `scaler.joblib`, and `evaluation_report.md`. Copy
those three into `model/artifacts/` in the repo, and copy the exact
`scikit-learn==X.Y.Z` version the notebook printed into
`engine/requirements.txt`.

If you change anything about the feature columns, their order, or the
label set, update `model/feature_spec.md` first and change both the
notebook and `engine/parser.py` to match — they have to agree exactly or
the classifier's predictions become meaningless on real input.

---

## 5. Testing at scale

Build a large stitched manuscript from the sample set to simulate a
400+ page document:

```bash
python scripts/build_scale_test_doc.py --target-pages 400
```

Run the performance profiler against it:

```bash
python scripts/profile_performance.py samples/scale_test_manuscript.docx --out performance_report.md
```

This reports wall-clock time, throughput, peak memory, and the label
distribution — the numbers for the performance-evaluation deliverable.

Generate a visual before/after comparison for any processed document:

```bash
python engine/main_pipeline.py samples/manuscript_03.docx samples/manuscript_03_formatted.docx
python scripts/compare_before_after_html.py samples/manuscript_03.docx samples/manuscript_03_formatted.docx samples/manuscript_03_comparison.html
```

If LibreOffice and poppler-utils are installed, this renders real page-1
images of both documents side by side; otherwise it falls back to a
formatting-only diff table.

---

## 6. Running the Word add-in and the standalone page

The add-in and the standalone page are both served by the same local
server, and both drive the same `engine/` pipeline — nothing about the
underlying processing differs between them.

Install the one additional dependency and start the server:

```bash
pip install flask
python server/app.py
```

The first run generates its own self-signed HTTPS certificate (via
`server/certs.py`) and prints `Serving DocFlow at https://localhost:3000`.
Open that URL in a browser once to confirm it loads without a certificate
warning.

**For the Word add-in:** sideload `addin/manifest.xml` — through Word for
the web (Insert → Add-ins → Upload My Add-in) or through desktop Word
after registering a local trusted catalog. Full instructions, including
what to do if the "My Add-ins" upload option isn't visible in desktop
Word, are in `ADDIN_README.md`.

**For LibreOffice, or to skip sideloading entirely:** with the server
running, open `https://localhost:3000/app` in any browser. Choose a
`.docx` file saved from Word or LibreOffice Writer, and it goes through
the identical pipeline.

Either way, the flow is the same: click Format (or choose a file), watch
the status line move through reading, classifying, and typesetting, drag
the slider to compare raw vs. formatted, check the element/time/validation
summary, and download the formatted `.docx`.

---

## 7. Why the add-in talks to a local server instead of the cloud

Office Add-ins run as JavaScript inside a sandboxed webview inside Word —
they can't import Python or run a machine learning model directly. The
local server bridges that gap: it serves the task pane's HTML/CSS/JS *and*
exposes the formatting engine as an HTTP API, both from the same
`https://localhost` origin. The browser inside Word talks only to that one
local origin; nothing about the document or its content is ever sent
anywhere else.

This also shaped a deliberate decision not to centrally host the task pane
(e.g. on GitHub Pages) for other users. Recent Chrome versions (142+)
block a hosted, non-local add-in from reaching back to a `localhost` API
inside Word Online, since Word Online doesn't grant the browser permission
that would require. Keeping everything — task pane and API — on the same
local origin, exactly as it runs for you now, sidesteps that restriction
entirely and is also why AppSource (which requires the add-in to function
on platforms like iPad that can never reach a local server) isn't a fit
for this architecture.

---

## 8. Building a distributable for other people

Anyone you hand this to needs a working local server without installing
Python, pip, or Node.js. `build_exe.py` packages the whole thing —
Python itself, Flask, scikit-learn, the trained model, and both frontends
— into one folder with a single executable, using PyInstaller.

From your development environment, with the venv from section 3 active:

```bash
pip install pyinstaller cryptography
python build_exe.py
```

The output lands in `dist/DocFlow/`. Test it from a clean terminal (not
the venv) to confirm it's genuinely self-contained:

```bash
cd dist/DocFlow
./DocFlow          # Windows: DocFlow.exe
```

Zip the whole `dist/DocFlow/` folder — that's the deliverable.

---

## 9. What the other person does with that zip

They unzip it anywhere, run the executable once (a console window opens
and stays open — that's the local engine), and run
`trust_certificate.ps1` once (right-click → Run with PowerShell; no admin
rights required, since it only installs into their own Windows user
account's certificate store, not the machine-wide one).

From there, sideloading the Word add-in or opening
`https://localhost:3000/app` for the standalone/LibreOffice path works
exactly as described in section 6 — the packaged executable behaves
identically to running `python server/app.py` from source.

Full detail on this whole process, including what to do if the trained
model changes later and needs redistributing, is in `DEPLOYMENT.md`.
