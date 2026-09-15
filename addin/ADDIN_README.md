# DocFlow Word Add-in — Setup & Run (Windows 11 + VS Code)

A task pane that runs inside Word: click **Format Manuscript**, and the
open document is parsed, classified, and formatted by the same offline
engine from Phases 1-3 — then a before/after slider (drag the red handle)
shows the raw manuscript morphing into the typeset result.

**Two ways to use DocFlow are included:**
1. **Word add-in** (preferred) — runs inside Word's task pane
2. **Standalone browser page** — same engine, same slider, works with any
   `.docx` regardless of what created it (Word *or* LibreOffice Writer),
   no sideloading required at all

Use #1 for the "runs inside Word" demo moment. Use #2 as your reliable
fallback and for anyone judging/testing with LibreOffice.

## What caused the error you saw

`taskpane.js:8 Uncaught ReferenceError: Office is not defined`, and the two
"Add-in Error" dialogs, both came from the same root cause: `office.js`
isn't a static library you can vendor locally — the real one (served from
`https://appsforoffice.microsoft.com/lib/1/hosted/office.js`) detects which
Office host is running it and performs a handshake with that host's frame.
My local copy couldn't do that handshake, so `Office` never got defined,
and Word's own error UI ("this add-in may not load properly") is exactly
what Word shows when an add-in never successfully calls `Office.onReady`.

**Fixed** — `taskpane.html` now loads `office.js` from Microsoft's CDN.
This needs internet only for that one script; parsing/classifying/
formatting still happens entirely on your machine via the local server.
(Word Online itself requires internet to run at all, so this changes
nothing about your actual test setup.)

## Why "My Add-ins" dropdown was missing in desktop Word

This is almost always one of:
- A Microsoft 365 desktop install with sideloading not yet enabled via a
  trusted catalog (most common)
- The "Upload My Add-in" option only shows once a trusted catalog exists —
  it's not visible by default

**Fix — register a local trusted catalog (one-time, ~2 minutes):**

1. Create a folder, e.g. `C:\DocFlowAddin`
2. Copy `addin\manifest.xml` into that folder
3. Open Word → **File** → **Options** → **Trust Center** → **Trust Center
   Settings...** → **Trusted Add-in Catalogs**
4. In **Catalog Url**, enter the folder path: `C:\DocFlowAddin`
5. Click **Add catalog**, check **Show in Menu**, click **OK**
6. **Close and restart Word completely**
7. Open a document → **Insert** tab → **Add-ins** → **My Add-ins** → you
   should now see a **SHARED FOLDER** tab listing "DocFlow" → select it →
   **Add**

This is Microsoft's documented method for sideloading without an Office
365 admin center — it works on any Windows 11 Word desktop install.

## One-time setup (do this once)

**1. Install Node.js LTS** (only used to generate a trusted local HTTPS
cert): https://nodejs.org

**2. Trust a local dev certificate** — open a terminal in VS Code
(`` Ctrl+` ``) and run:

```powershell
npx office-addin-dev-certs install
```

This installs a cert to `%USERPROFILE%\.office-addin-dev-certs\` and adds
it to Windows' trust store, so both Edge/Chrome and Word trust
`https://localhost:3000`.

**3. Python environment** (VS Code terminal, from the repo root):

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r engine\requirements.txt
pip install flask
```

**4. (Optional but recommended) Install LibreOffice** for the real
rendered-page slider (works either way — falls back to a stylized preview
without it): https://www.libreoffice.org

## Running it

**Start the server** (VS Code terminal, venv active):

```powershell
python server\app.py
```

You should see `Serving DocFlow add-in at https://localhost:3000`. Leave
this terminal running for the whole demo.

**Sanity check first** — open `https://localhost:3000` in Edge/Chrome. You
should see the DocFlow task pane render with no certificate warning. If you
get a cert warning, redo step 2 above and restart your browser.

### Option 1: Word Online (confirmed working in your testing)

1. Go to office.com, open/upload your manuscript, open it in **Word for
   the web**
2. **Insert** → **Add-ins** → **Upload My Add-in**
3. Browse to `addin\manifest.xml` → **Upload**
4. Click the **DocFlow** button that appears in the Home ribbon
5. Click **Format Manuscript** in the task pane

### Option 2: Word Desktop (after the trusted-catalog setup above)

1. Open your manuscript in desktop Word
2. **Insert** → **Add-ins** → **My Add-ins** → **SHARED FOLDER** tab →
   **DocFlow** → **Add**
3. Click the **DocFlow** button in the ribbon, then **Format Manuscript**

### Option 3: Standalone (LibreOffice, or no sideloading at all)

1. In LibreOffice Writer (or Word), save your manuscript as `.docx`
2. With the server running, open `https://localhost:3000/app` in any
   browser
3. Click **Choose a .docx manuscript**, select your file
4. Same slider, same colophon, same download — no sideloading needed

## Using it (either mode)

1. Click **Format Manuscript** (add-in) or choose a file (standalone)
2. Status line: reading → classifying → typesetting
3. Drag the red handle on the **Proof** slider to compare raw vs. typeset
4. Check the **Colophon** (elements formatted, time, validation)
5. **Download formatted .docx** and open it in Word or LibreOffice — that's
   your publication-ready output

## Troubleshooting

| Symptom | Fix |
|---|---|
| `Office is not defined` again | Confirm `taskpane.html` references the `appsforoffice.microsoft.com` URL, not a local file — check you copied the updated file from this delivery |
| "Add-in Error" dialogs in Word | Same root cause as above — should be resolved by the CDN fix; if not, open the task pane's dev tools (right-click → Inspect) and check the Console for the actual error |
| Word desktop still has no "My Add-ins" dropdown at all | Confirm you restarted Word *completely* (not just closed the document) after adding the trusted catalog |
| Cert warning in browser | Re-run `npx office-addin-dev-certs install`, then fully restart the browser |
| "No dev certs found" when starting the server | Run the `office-addin-dev-certs install` command above first |
| Slider shows the illustrative mockup, not real pages | Install LibreOffice; the server auto-detects `soffice`/`pdftoppm` on PATH, no config needed |
| `ModuleNotFoundError` on server start | Make sure `venv\Scripts\activate` ran and `pip install -r engine\requirements.txt` + `flask` succeeded |

## File map

```
addin/
├── manifest.xml       Word add-in manifest (classic XML, no Azure app registration needed)
├── taskpane.html        Word add-in task pane (uses Office.js CDN)
├── taskpane.js            Office.js file extraction, API calls, slider logic
├── standalone.html      browser-only mode, no Word/Office.js dependency
├── standalone.js          file-picker version of the same logic
├── taskpane.css             shared editorial/print-proof styling
└── assets/                    icons
server/
└── app.py              local HTTPS server: serves both frontends + the formatting API
```
