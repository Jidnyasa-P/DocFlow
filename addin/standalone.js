/* DocFlow standalone mode — same server, same engine, no Word/Office.js
   dependency. For LibreOffice users (or anyone testing without Word):
   export/save your document as .docx from LibreOffice Writer, choose it
   here, and it goes through the identical formatting pipeline as the Word
   add-in. */

let lastOriginalBase64 = null;
let lastFormattedBase64 = null;

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("fileInput").addEventListener("change", onFileChosen);
  setupSlider();
});

function setStatus(text, kind) {
  const el = document.getElementById("statusLine");
  el.textContent = text;
  el.className = "status-line" + (kind ? " " + kind : "");
}

async function onFileChosen(e) {
  const file = e.target.files[0];
  if (!file) return;

  setStatus("Reading " + file.name + "…");

  try {
    const docxBase64 = await fileToBase64(file);
    lastOriginalBase64 = docxBase64;

    setStatus("Classifying elements and typesetting…");
    const formatResult = await callApi("/api/format", { docx_base64: docxBase64 });

    if (formatResult.error) {
      setStatus("Error: " + formatResult.error, "error");
      return;
    }

    lastFormattedBase64 = formatResult.formatted_base64;
    showColophon(formatResult);
    setupDownload(formatResult.formatted_base64, file.name);

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
  }
}

function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const base64 = reader.result.split(",")[1]; // strip "data:...;base64,"
      resolve(base64);
    };
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

async function callApi(path, body) {
  const resp = await fetch(path, {
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

function setupDownload(formattedBase64, originalName) {
  const link = document.getElementById("downloadLink");
  const bytes = base64ToBytes(formattedBase64);
  const blob = new Blob([bytes], {
    type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  });
  const url = URL.createObjectURL(blob);
  link.href = url;
  const base = (originalName || "manuscript.docx").replace(/\.docx$/i, "");
  link.download = base + "_formatted.docx";
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
