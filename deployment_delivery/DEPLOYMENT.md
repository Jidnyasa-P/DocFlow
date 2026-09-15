# DocFlow — Deployment Guide (Word + LibreOffice, free, offline)

This is the full path from what you have now to something you can hand to
someone else — teammate, judge, anyone — who has never seen VS Code or
Python, and have it work fully offline on their machine.

## The architecture decision (read this first)

I initially planned to host the task pane on GitHub Pages (free HTTPS) so
people could sideload a add-in that points at a stable public URL, with
the actual processing still happening locally. **I'm not doing that**,
because of something I confirmed while researching this:

**As of Chrome 142 (Nov 2025), a production add-in hosted on a real HTTPS
domain is blocked from calling back to `localhost` in Word Online** — this
is a new browser-level "Local Network Access" permission that Word Online
doesn't currently grant, and it's a live, unresolved issue in Microsoft's
own `office-js` repo. It would work in *your* sideloaded dev setup (that's
a different, unaffected code path) but would silently break for anyone
else using a "properly hosted" version on a recent Chrome/Edge.

There's a second reason to skip Microsoft AppSource specifically: its
"Functionality as Described" policy requires the add-in to work on *every*
platform Word supports, including iPad and mobile — which structurally
can't reach a localhost server at all, on any architecture. This isn't
fixable by us; it's a certification blocker built into how AppSource
works.

**So the right free architecture is the one you already validated**: the
local engine serves *both* the task pane and the API, on the user's own
machine, same-origin, exactly like your working sideload right now. The
actual deployment problem is just: make that local engine installable by
someone who isn't you, in one step, with no dev tools.

## What changed to make that possible

1. **No more Node.js/npx dependency.** `server/certs.py` generates its own
   self-signed certificate in pure Python on first run. `npx
   office-addin-dev-certs install` is no longer needed at all.
2. **No more Python install needed for end users.** `build_exe.py` uses
   PyInstaller to bundle Python, Flask, scikit-learn, your trained model,
   and the add-in's files into one folder with a single executable.
   Tested — it boots, serves the task pane, loads the real trained model,
   and formats a document correctly with nothing else installed.
3. **LibreOffice is already covered** by the standalone page (`/app`)
   built in the last delivery — it works from the packaged executable
   exactly the same way, no separate LibreOffice extension needed. Open
   `https://localhost:3000/app` in any browser, pick a `.docx` (from Word
   *or* LibreOffice Writer), done.

## Step-by-step: build the distributable (you do this once)

**1. In your existing venv, install the packaging tool:**

```powershell
pip install pyinstaller cryptography
```

**2. Build it:**

```powershell
python build_exe.py
```

This takes a minute or two. Output lands in `dist\DocFlow\` — a folder
containing `DocFlow.exe` plus everything it needs (~270 MB, mostly
scikit-learn/numpy's own binaries — normal, no cost either way).

**3. Test it yourself first**, from a totally clean terminal (not the
venv, to prove it doesn't secretly depend on your Python install):

```powershell
cd dist\DocFlow
.\DocFlow.exe
```

You should see the same `Serving DocFlow at https://localhost:3000` you
already know, then a first-run message about generating a certificate.

**4. Zip it for distribution:**

```powershell
cd dist
Compress-Archive -Path DocFlow -DestinationPath DocFlow-v1.zip
```

That zip is your deliverable. Anyone can download it, unzip it anywhere
(Desktop is fine), no installer, no admin rights, no Python.

## What the other person does (give them these instructions)

**1. Unzip `DocFlow-v1.zip` anywhere.**

**2. Run `DocFlow.exe` once.** A console window opens and stays open —
that's the local engine running. Leave it open while using the add-in.

**3. Trust the certificate (one-time):** right-click `trust_certificate.ps1`
→ **Run with PowerShell**. No admin rights required — it only installs
into their own Windows user account's trust store.

**4. Sideload the add-in into Word** — exact same steps as your working
setup:
   - *Word Online:* Insert → Add-ins → Upload My Add-in → select
     `addin\manifest.xml` (inside the unzipped folder)
   - *Word Desktop:* one-time Trust Center → Trusted Add-in Catalogs setup
     (full steps in `ADDIN_README.md`, already in your repo), then Insert →
     Add-ins → My Add-ins → SHARED FOLDER tab → DocFlow

**5. Or skip Word entirely:** with `DocFlow.exe` running, open
`https://localhost:3000/app` in any browser — this is the LibreOffice
path, and works for anyone regardless of which editor they used.

## Keeping it "free and up to date"

- **Free:** every tool used here — PyInstaller, `cryptography`, Flask,
  self-signed certs — is free and open source, zero licensing cost, no
  Microsoft account or developer registration needed anywhere in this
  path (that's specifically what skipping AppSource buys you).
- **Updated information:** if Person A retrains the model later, rebuild
  with `python build_exe.py` again and redistribute the new zip — the
  bundled `classifier.joblib`/`scaler.joblib` are just data files it
  picks up automatically from `model/artifacts/`.
- **No ongoing hosting cost:** because nothing is centrally hosted, there's
  no server bill, no domain renewal, nothing that can go down or expire.
  The tradeoff is every user runs their own local copy — which is also
  exactly what makes the "fully offline, your document never leaves your
  machine" claim actually true, for every user, not just you.

## Optional next steps (not needed for the above to work)

- **Smaller download:** `build_exe.py` currently bundles
  `model/artifacts/training_data.csv`, `unlabeled_paragraphs.csv`, and
  `train.ipynb` — none of these are needed at runtime. Exclude them from
  the `model/` folder before building if you want a leaner zip.
- **A real installer** (Start Menu shortcut, uninstaller) via Inno Setup
  (also free) instead of a plain zip — cosmetic, not required.
- **Native LibreOffice extension (.oxt)** with a toolbar button inside
  LibreOffice itself, instead of the browser-based `/app` fallback — a
  separate, non-trivial build using LibreOffice's UNO API. The standalone
  page already gets you free, offline, working LibreOffice support without
  this; only worth it if you specifically want a "runs inside LibreOffice"
  demo moment to match the Word one.

Let me know if you want either of the last two built out.
