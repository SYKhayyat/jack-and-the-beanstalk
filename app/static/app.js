/* Front-end controller: collect the form, POST it, render the result.
   Deliberately dependency-free — no build step, so Render serves static files
   straight from the repo. */
"use strict";

const form = document.getElementById("generate-form");
const submit = document.getElementById("submit");
const results = document.getElementById("results");
const statusEl = document.getElementById("status");
const photoInput = document.getElementById("photo");
const previewWrap = document.getElementById("preview-wrap");
const preview = document.getElementById("preview");
const intensity = document.getElementById("cartoon_intensity");
const intensityOutput = document.getElementById("intensity-output");

let lastScene = null;

/* Live-updating label for the cartoon-vs-real slider. */
intensity.addEventListener("input", () => {
  intensityOutput.textContent = intensity.value;
});

/* Local preview so the user can confirm they picked the right photo. */
photoInput.addEventListener("change", () => {
  const file = photoInput.files && photoInput.files[0];
  if (!file) {
    previewWrap.classList.add("hidden");
    return;
  }
  preview.src = URL.createObjectURL(file);
  previewWrap.classList.remove("hidden");
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!photoInput.files || !photoInput.files[0]) {
    showError("Please choose a photo first.");
    return;
  }

  const payload = new FormData(form);
  lastScene = payload.get("scene");

  setBusy("Cartoonifying you, then growing the beanstalk…");

  try {
    const response = await fetch("/api/generate", { method: "POST", body: payload });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(data.detail || `Request failed (${response.status}).`);
    }
    renderResult(data);
  } catch (error) {
    showError(error.message);
  } finally {
    setIdle();
  }
});

function renderResult(data) {
  document.getElementById("cartoon-image").src = data.images.cartoon_url;
  document.getElementById("scene-image").src = data.images.scene_url;
  document.getElementById("scene-caption").textContent = data.caption;
  document.getElementById("cartoon-prompt").textContent = data.prompts.cartoon;
  document.getElementById("scene-prompt").textContent = data.prompts.scene;

  const download = document.getElementById("download-scene");
  download.href = data.images.scene_url;
  download.download = `${data.scene_key}.png`;

  const swap = document.getElementById("same-person-second-scene");
  swap.href = "#";
  swap.addEventListener("click", (event) => {
    event.preventDefault();
    const other = form.querySelector(`input[name="scene"][value="${data.scene_key}"]`)
      ? form.querySelector('input[name="scene"]:not(:checked)')
      : null;
    if (other) {
      other.checked = true;
      form.requestSubmit();
    }
  });

  const warnings = data.warnings || [];
  statusEl.className = "status";
  statusEl.textContent =
    `Done via ${data.provider} (${data.model}). ` +
    `Generation ${data.generation_id.slice(0, 8)}.` +
    (warnings.length ? ` Note: ${warnings.join(" ")}` : "");

  results.classList.remove("hidden");
  results.scrollIntoView({ behavior: "smooth", block: "start" });
}

function setBusy(message) {
  submit.disabled = true;
  submit.textContent = "Working…";
  results.classList.remove("hidden");
  statusEl.className = "status busy";
  statusEl.textContent = message;
  results.scrollIntoView({ behavior: "smooth", block: "start" });
}

function setIdle() {
  submit.disabled = false;
  submit.textContent = "Grow the beanstalk…";
}

function showError(message) {
  results.classList.remove("hidden");
  statusEl.className = "status error";
  statusEl.textContent = message;
}