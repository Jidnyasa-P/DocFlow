"""
DocFlow Word Add-in — local bridge server.

Office Add-ins run as JavaScript inside a sandboxed webview in Word. They
cannot import Python, spawn processes, or touch the filesystem directly.
This server is the bridge: it serves the task pane's static files (HTML/
CSS/JS) AND exposes the formatting engine as a local HTTP API, all from
ONE https://localhost origin so the browser never blocks it as mixed
content or cross-origin.

Everything here runs on localhost only. No data leaves the machine, no
internet connection is used at request time — this satisfies the "fully
offline" requirement while still letting a browser-sandboxed add-in reach
a real Python ML pipeline.

Run:
    python server/app.py
Then sideload addin/manifest.xml into Word (see ADDIN_README.md).
"""
import base64
import os
import shutil
import subprocess
import sys
import tempfile
import time

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if getattr(sys, "frozen", False):
    # Running as a PyInstaller-built executable: bundled data files live
    # under sys._MEIPASS (a temp extraction dir), not next to this script.
    REPO_ROOT = sys._MEIPASS

ADDIN_DIR = os.path.join(REPO_ROOT, "addin")
ENGINE_DIR = os.path.join(REPO_ROOT, "engine")

# 1. Add the REPO_ROOT (DocFlow) to the path instead of ENGINE_DIR
sys.path.insert(0, REPO_ROOT)

# 2. Update the docx_parser import to use the 'engine.' prefix
from engine.docx_parser import parse_docx             # noqa: E402
from engine.classifier_stub import classify_batch     # noqa: E402
from engine.formatting_engine import format_document # noqa: E402
from engine.validation import validate_output         # noqa: E402

app = Flask(__name__, static_folder=None)
CORS(app)


# ---------------------------------------------------------------------
# Static file serving — task pane HTML/CSS/JS/icons/vendored office.js
# ---------------------------------------------------------------------
@app.route("/")
@app.route("/taskpane.html")
def taskpane():
    return send_from_directory(ADDIN_DIR, "taskpane.html")


@app.route("/taskpane.css")
def taskpane_css():
    return send_from_directory(ADDIN_DIR, "taskpane.css")


@app.route("/taskpane.js")
def taskpane_js():
    return send_from_directory(ADDIN_DIR, "taskpane.js")


@app.route("/standalone.html")
@app.route("/app")
def standalone():
    return send_from_directory(ADDIN_DIR, "standalone.html")


@app.route("/standalone.js")
def standalone_js():
    return send_from_directory(ADDIN_DIR, "standalone.js")


@app.route("/manifest.xml")
def manifest():
    return send_from_directory(ADDIN_DIR, "manifest.xml", mimetype="application/xml")


@app.route("/assets/<path:filename>")
def asset_files(filename):
    return send_from_directory(os.path.join(ADDIN_DIR, "assets"), filename)


# ---------------------------------------------------------------------
# API: run the actual formatting pipeline
# ---------------------------------------------------------------------
@app.route("/api/format", methods=["POST"])
def api_format():
    payload = request.get_json(force=True)
    docx_b64 = payload.get("docx_base64")
    if not docx_b64:
        return jsonify({"error": "docx_base64 is required"}), 400

    with tempfile.TemporaryDirectory() as tmp:
        in_path = os.path.join(tmp, "input.docx")
        out_path = os.path.join(tmp, "output.docx")
        with open(in_path, "wb") as f:
            f.write(base64.b64decode(docx_b64))

        t0 = time.time()
        records, doc = parse_docx(in_path)
        original_paragraph_texts = [r.text for r in records if not r.is_table]

        results = classify_batch(records)
        label_counts = {}
        for r, (label, confidence) in zip(records, results):
            r.label = label
            r.label_confidence = confidence
            label_counts[label] = label_counts.get(label, 0) + 1

        format_document(doc, records)
        doc.save(out_path)

        report = validate_output(original_paragraph_texts, in_path, out_path, records)
        elapsed = time.time() - t0

        with open(out_path, "rb") as f:
            formatted_b64 = base64.b64encode(f.read()).decode("ascii")

    return jsonify({
        "formatted_base64": formatted_b64,
        "n_elements": len(records),
        "label_counts": label_counts,
        "elapsed_seconds": round(elapsed, 2),
        "validation_ok": report.ok,
        "validation_errors": report.errors[:5],
        "validation_warnings": report.warnings[:5],
    })


# ---------------------------------------------------------------------
# API: optional visual page render for the before/after slider.
# Requires LibreOffice (soffice) + poppler-utils (pdftoppm) on this
# machine. Purely a nice-to-have for the demo -- the formatting API above
# works with or without this.
# ---------------------------------------------------------------------
def _render_first_page_png(docx_bytes, workdir, name):
    if shutil.which("soffice") is None or shutil.which("pdftoppm") is None:
        return None
    docx_path = os.path.join(workdir, f"{name}.docx")
    with open(docx_path, "wb") as f:
        f.write(docx_bytes)
    try:
        subprocess.run(
            ["soffice", "--headless", "--convert-to", "pdf", "--outdir", workdir, docx_path],
            check=True, capture_output=True, timeout=120,
        )
        pdf_path = os.path.join(workdir, f"{name}.pdf")
        if not os.path.exists(pdf_path):
            return None
        prefix = os.path.join(workdir, f"{name}_page")
        subprocess.run(
            ["pdftoppm", "-png", "-r", "110", "-f", "1", "-l", "1", pdf_path, prefix],
            check=True, capture_output=True, timeout=60,
        )
        for fn in os.listdir(workdir):
            if fn.startswith(f"{name}_page"):
                with open(os.path.join(workdir, fn), "rb") as img_f:
                    return base64.b64encode(img_f.read()).decode("ascii")
    except Exception as e:
        print(f"[render-comparison] skipped: {e}")
    return None


@app.route("/api/render-comparison", methods=["POST"])
def api_render_comparison():
    payload = request.get_json(force=True)
    original_b64 = payload.get("original_base64")
    formatted_b64 = payload.get("formatted_base64")
    if not original_b64 or not formatted_b64:
        return jsonify({"error": "original_base64 and formatted_base64 are required"}), 400

    with tempfile.TemporaryDirectory() as tmp:
        before_png = _render_first_page_png(base64.b64decode(original_b64), tmp, "before")
        after_png = _render_first_page_png(base64.b64decode(formatted_b64), tmp, "after")

    if before_png and after_png:
        return jsonify({"available": True, "before_png_base64": before_png, "after_png_base64": after_png})
    return jsonify({"available": False, "reason": "LibreOffice/poppler-utils not found on this machine"})


@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "engine_dir": ENGINE_DIR})


def _find_dev_certs():
    """Generate (or reuse) a self-signed certificate in pure Python -- no
    Node.js/npx required. See certs.py for details."""
    from certs import ensure_cert
    return ensure_cert()


if __name__ == "__main__":
    cert, key = _find_dev_certs()
    print(f"Serving DocFlow at https://localhost:3000  (cert: {cert})")
    print("First time running this? See README: you need to trust this")
    print("certificate once (run trust_certificate.ps1) before Word/your")
    print("browser will accept it without a warning.")
    app.run(host="localhost", port=3000, ssl_context=(cert, key), debug=False)
