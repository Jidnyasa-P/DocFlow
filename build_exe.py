"""
Builds a standalone DocFlow executable with PyInstaller -- bundles Python
itself, Flask, scikit-learn, joblib, numpy, python-docx, our engine code,
the trained model, and the add-in's static files (task pane + standalone
page) into one .exe. End users need NOTHING installed to run it: no
Python, no pip, no Node.js.

Run this from the repo root, inside the venv used to build the app:
    pip install pyinstaller
    python build_exe.py

Output: dist/DocFlow/DocFlow.exe (folder build -- faster startup than
--onefile, and easier to inspect/debug if something's missing).
"""
import os
import shutil
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))

# scikit-learn/numpy pull in a lot of submodules PyInstaller's static
# analysis can miss (Cython-compiled bits, dynamically imported tree/
# ensemble modules). Listing them explicitly avoids a working build that
# then crashes at runtime with "No module named sklearn.XYZ" the first
# time a user clicks Format.
HIDDEN_IMPORTS = [
    "flask",
    "flask_cors",
    "sklearn.ensemble._forest",
    "sklearn.tree._tree",
    "sklearn.tree._splitter",
    "sklearn.tree._criterion",
    "sklearn.utils._cython_blas",
    "sklearn.utils._typedefs",
    "sklearn.utils._heap",
    "sklearn.utils._sorting",
    "sklearn.utils._vector_sentinel",
    "sklearn.neighbors._partition_nodes",
    "sklearn.utils._weight_vector",
    "scipy.special.cython_special",
    # python-docx isn't imported directly by app.py -- it's imported by
    # engine/*.py, which PyInstaller's static analyzer can't trace because
    # those modules are only reachable via a runtime sys.path.insert, not
    # a normal import statement it can follow at build time.
    "docx",
    "docx.enum.text",
    "docx.enum.table",
    "docx.oxml.ns",
    "docx.table",
    "docx.text.paragraph",
    "docx.shared",
]

DATA_DIRS = [
    ("addin", "addin"),
    ("model", "model"),
]


def main():
    entry = os.path.join(REPO_ROOT, "server", "app.py")
    venv_packages = os.path.join(REPO_ROOT, "venv", "Lib", "site-packages")

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", "DocFlow",
        "--noconfirm",
        "--clean",
        "--distpath", os.path.join(REPO_ROOT, "dist"),
        "--workpath", os.path.join(REPO_ROOT, "build"),
        # Provide explicit search paths for the dependency resolution engine
        "--paths", venv_packages,
        "-p", venv_packages,
        # keep console visible -- shows "Serving DocFlow at https://..."
        # and any errors, which matters a lot for a first-run diagnostic
        "--console",
    ]

    for hi in HIDDEN_IMPORTS:
        cmd += ["--hidden-import", hi]

    sep = ";" if os.name == "nt" else ":"
    for src, dest in DATA_DIRS:
        cmd += ["--add-data", f"{os.path.join(REPO_ROOT, src)}{sep}{dest}"]

    # engine/ is imported via sys.path manipulation in app.py, not a
    # normal package import, so PyInstaller's import scanner won't find
    # it on its own -- bundle it as data too and let app.py's sys.path
    # insert (already pointing at REPO_ROOT/engine, which becomes
    # sys._MEIPASS/engine when frozen) pick it up.
    cmd += ["--add-data", f"{os.path.join(REPO_ROOT, 'engine')}{sep}engine"]

    cmd.append(entry)

    print("Running:", " ".join(cmd))
    subprocess.run(cmd, check=True)

    print("\nDone. Output: dist/DocFlow/DocFlow.exe (or DocFlow on Mac/Linux)")
    print("Zip the whole dist/DocFlow/ folder to share it -- everything")
    print("needed is inside, nothing else to install.")


if __name__ == "__main__":
    main()