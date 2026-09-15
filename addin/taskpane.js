/* global Office */

const API_BASE = ""; // same origin as the task pane -- no cross-origin calls at all

let lastOriginalBase64 = null;
let lastFormattedBase64 = null;

if (typeof Office === "undefined") {
  document.addEventListener("DOMContentLoaded", () => {
    const el = document.getElementById("statusLine");
    if (el) {
      el.textContent =
        "Office.js failed to load from Microsoft's CDN. Check your internet connection, then reload this task pane (right-click it -> Reload).";
      el.className = "status-line error";
    }
    const btn = document.getElementById("formatBtn");
    if (btn) btn.disabled = true;
  });
} else {
  Office.onReady(() => {
    document.getElementById("formatBtn").addEventListener("click", onFormatClick);
    setupSlider();
  });
}

function setStatus(text, kind) {
  const el = document.getElementById("statusLine");
  el.textContent = text;
  el.className = "status-line" + (kind ? " " + kind : "");
}

async function onFormatClick() {
  const btn = document.getElementById("formatBtn");
  btn.disabled = true;
  setStatus("Reading manuscript from Word…");

  try {
    const docxBase64 = await getActiveDocumentBase64();
    lastOriginalBase64 = docxBase64;

    setStatus("Classifying elements and typesetting…");
    const formatResult = await callApi("/api/format", { docx_base64: docxBase64 });

    if (formatResult.error) {
      setStatus("Error: " + formatResult.error, "error");
      btn.disabled = false;
      return;
    }

    lastFormattedBase64 = formatResult.formatted_base64;
    showColophon(formatResult);
    setupDownload(formatResult.formatted_base64);

    setStatus(
      `Done — ${formatResult.n_elements} elements typeset in ${formatResult.elapsed_seconds}s`,
      "done"
    );

    setStatus("Rendering proof…", null);
    const compare = await callApi("/api/render-comparison", {
      original_base64: lastOriginalBase64,
      formatted_base64: lastFormattedBase64,
    });
    showCompare(compare);

    setStatus(
      `Done — ${formatResult.n_elements} elements typeset in ${formatResult.elapsed_seconds}s`,
      "done"
    );
  } catch (err) {
    console.error(err);
    setStatus("Something went wrong: " + (err.message || err), "error");
  } finally {
    btn.disabled = false;
  }
}

/**
 * Word add-ins can't read the raw .docx bytes directly -- getFileAsync
 * with FileType.Compressed hands back the underlying OOXML package as a
 * sliced binary stream, which we reassemble and base64-encode here.
 */
function getActiveDocumentBase64() {
  return new Promise((resolve, reject) => {
    Office.context.document.getFileAsync(
      Office.FileType.Compressed,
      { sliceSize: 65536 },
      (result) => {
        if (result.status !== Office.AsyncResultStatus.Succeeded) {
          reject(result.error);
          return;
        }
        const file = result.value;
        const sliceCount = file.sliceCount;
        const slices = new Array(sliceCount);
        let received = 0;

        function getSlice(index) {
          file.getSliceAsync(index, (sliceResult) => {
            if (sliceResult.status !== Office.AsyncResultStatus.Succeeded) {
              file.closeAsync();
              reject(sliceResult.error);
              return;
            }
            slices[sliceResult.value.index] = sliceResult.value.data;
            received += 1;
            if (received === sliceCount) {
              file.closeAsync();
              resolve(bytesToBase64(concatSlices(slices)));
            } else {
              getSlice(received);
            }
          });
        }
        getSlice(0);
      }
    );
  });
}

function concatSlices(slices) {
  let total = 0;
  for (const s of slices) total += s.length;
  const merged = new Uint8Array(total);
  let offset = 0;
  for (const s of slices) {
    merged.set(s, offset);
    offset += s.length;
  }
  return merged;
}

/** btoa() chokes on very large arrays passed via String.fromCharCode(...arr)
 * (argument count limits) -- encode in chunks instead. */
function bytesToBase64(bytes) {
  const chunkSize = 0x8000;
  let binary = "";
  for (let i = 0; i < bytes.length; i += chunkSize) {
    binary += String.fromCharCode.apply(null, bytes.subarray(i, i + chunkSize));
  }
  return btoa(binary);
}

async function callApi(path, body) {
  const resp = await fetch(API_BASE + path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return resp.json();
}

function showColophon(result) {
  document.getElementById("colophon").classList.remove("hidden");
  document.getElementById("statElements").textContent = result.n_elements;
  document.getElementById("statTime").textContent = result.elapsed_seconds + "s";
  document.getElementById("statValidation").textContent = result.validation_ok
    ? "Passed"
    : `Issues (${result.validation_errors.length})`;
}

function setupDownload(formattedBase64) {
  const link = document.getElementById("downloadLink");
  const bytes = base64ToBytes(formattedBase64);
  const blob = new Blob([bytes], {
    type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  });
  const url = URL.createObjectURL(blob);
  link.href = url;
  link.classList.remove("hidden");
}

function base64ToBytes(b64) {
  const binary = atob(b64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  return bytes;
}

function showCompare(compareResult) {
  const section = document.getElementById("compareSection");
  section.classList.remove("hidden");
  const mockNote = document.getElementById("mockNote");

  if (compareResult && compareResult.available) {
    mockNote.classList.add("hidden");
    document.getElementById("beforeImg").src = "data:image/png;base64," + compareResult.before_png_base64;
    document.getElementById("afterImg").src = "data:image/png;base64," + compareResult.after_png_base64;
    document.getElementById("afterImgClip").src = "data:image/png;base64," + compareResult.after_png_base64;
  } else {
    // Fallback: stylized CSS mockup so the demo still has a visual even
    // without LibreOffice on this machine. Uses inline SVG "proof sheets"
    // instead of real page renders.
    mockNote.classList.remove("hidden");
    document.getElementById("beforeImg").src = mockProofSvg(false);
    document.getElementById("afterImg").src = mockProofSvg(true);
    document.getElementById("afterImgClip").src = mockProofSvg(true);
  }
}

function mockProofSvg(formatted) {
  const lines = [];
  const widths = formatted ? [92, 92, 92, 92, 60] : [88, 95, 71, 90, 55];
  const indent = formatted ? 14 : [0, 22, 4, 18, 0];
  let y = 30;
  widths.forEach((w, i) => {
    const x = 10 + (formatted ? (i === 0 ? indent : 0) : indent[i]);
    lines.push(`<rect x="${x}" y="${y}" width="${w}" height="4" rx="1" fill="${formatted ? '#1B1B1F' : '#585858'}"/>`);
    y += formatted ? 10 : 8.5;
  });
  const svg = `
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 130">
    <rect width="100" height="130" fill="#ffffff"/>
    <rect x="6" y="6" width="60" height="10" fill="${formatted ? '#17324D' : '#B3261E'}" opacity="0.85"/>
    ${lines.join("")}
  </svg>`;
  return "data:image/svg+xml;base64," + btoa(svg);
}

function setupSlider() {
  const input = document.getElementById("sliderInput");
  const handle = document.getElementById("handle");
  const clip = document.getElementById("afterClip");

  function update(value) {
    handle.style.left = value + "%";
    clip.style.clipPath = `inset(0 ${100 - value}% 0 0)`;
  }
  input.addEventListener("input", (e) => update(e.target.value));
  update(50);
}
