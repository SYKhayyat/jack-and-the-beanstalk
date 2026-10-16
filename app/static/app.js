/* Front-end controller for the two-step flow.
   Deliberately dependency-free — no build step, so Render serves static files
   straight from the repo.

   The flow is: cartoonify → review → compose. Keeping the two API calls apart
   is the point: a likeness you dislike costs one call, not two, and putting an
   approved portrait into the other scene costs one call. */
"use strict";

const form = document.getElementById("generate-form");
const submit = document.getElementById("submit");
const retryButton = document.getElementById("retry-cartoon");
const approveButton = document.getElementById("approve-cartoon");
const otherSceneButton = document.getElementById("other-scene");
const startOverButton = document.getElementById("start-over");

const cartoonStage = document.getElementById("cartoon-stage");
const sceneStage = document.getElementById("scene-stage");
const cartoonStatus = document.getElementById("cartoon-status");
const sceneStatus = document.getElementById("scene-status");
const cartoonCost = document.getElementById("cartoon-cost");
const sceneCost = document.getElementById("scene-cost");

const photoInput = document.getElementById("photo");
const previewWrap = document.getElementById("preview-wrap");
const preview = document.getElementById("preview");
const intensity = document.getElementById("cartoon_intensity");
const intensityOutput = document.getElementById("intensity-output");

const state = {
  generationId: null,
  calls: 0,
  sceneKey: null,
};

intensity.addEventListener("input", () => {
  intensityOutput.textContent = intensity.value;
});

photoInput.addEventListener("change", () => {
  const file = photoInput.files && photoInput.files[0];
  if (!file) {
    previewWrap.classList.add("hidden");
    reset();
    return;
  }
  preview.src = URL.createObjectURL(file);
  previewWrap.classList.remove("hidden");
});

/* Step 1 — cartoonify only. */
form.addEventListener("submit", (event) => {
  event.preventDefault();
  if (!hasPhoto()) return;
  runCartoonify();
});

retryButton.addEventListener("click", () => {
  if (!hasPhoto()) return;
  runCartoonify();
});

/* Step 2 — the user approved the portrait. */
approveButton.addEventListener("click", () => {
  if (!state.generationId) {
    showCartoonError("Cartoonify first, then approve.");
    return;
  }
  runCompose(currentScene());
});

/* Same approved portrait, other scene: one call, not two. */
otherSceneButton.addEventListener("click", () => {
  const other = form.querySelector('input[name="scene"]:not(:checked)');
  if (!other) return;
  other.checked = true;
  runCompose(currentScene());
});

startOverButton.addEventListener("click", () => {
  reset();
  form.scrollIntoView({ behavior: "smooth", block: "start" });
});

function hasPhoto() {
  if (photoInput.files && photoInput.files.length) return true;
  showCartoonError("Please choose a photo first.");
  return false;
}

function currentScene() {
  return form.querySelector('input[name="scene"]:checked').value;
}

function reset() {
  state.generationId = null;
  state.calls = 0;
  state.sceneKey = null;
  cartoonStage.classList.add("hidden");
  sceneStage.classList.add("hidden");
}

function settingsPayload() {
  const payload = new FormData(form);
  payload.delete("photo");
  payload.delete("scene");
  return payload;
}

async function runCartoonify() {
  setBusy(cartoonStatus, cartoonStage, "Cartoonifying you…");
  submit.disabled = true;
  retryButton.disabled = true;

  try {
    const body = settingsPayload();
    body.append("photo", photoInput.files[0]);

    const response = await fetch("/api/cartoonify", { method: "POST", body });
    const data = await readJson(response);
    renderCartoon(data);
  } catch (error) {
    showCartoonError(error.message);
  } finally {
    submit.disabled = false;
    retryButton.disabled = false;
  }
}

async function runCompose(scene) {
  setBusy(sceneStatus, sceneStage, `Placing you in the scene: ${scene}…`);

  try {
    const body = new FormData();
    body.append("generation_id", state.generationId);
    body.append("scene", scene);

    const response = await fetch("/api/compose", { method: "POST", body });
    const data = await readJson(response);
    renderScene(data);
  } catch (error) {
    showSceneError(error.message);
  }
}

async function readJson(response) {
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.detail || `Request failed (${response.status}).`);
  }
  return data;
}

function renderCartoon(data) {
  state.generationId = data.generation_id;
  state.calls += 1;

  document.getElementById("cartoon-image").src = data.images.cartoon_url;
  document.getElementById("cartoon-prompt").textContent = data.prompts.cartoon;
  cartoonCost.textContent = `${state.calls} image call${state.calls > 1 ? "s" : ""} used`;

  cartoonStatus.className = "status";
  cartoonStatus.textContent =
    `Cartoon ready via ${data.provider}. Judge the likeness before continuing.`;

  sceneStage.classList.add("hidden");
  cartoonStage.classList.remove("hidden");
  cartoonStage.scrollIntoView({ behavior: "smooth", block: "start" });
}

function renderScene(data) {
  state.sceneKey = data.scene_key;
  state.calls += 1;

  document.getElementById("scene-title").textContent = data.scene_title;
  document.getElementById("scene-image").src = data.images.scene_url;
  document.getElementById("scene-cartoon-image").src = data.images.cartoon_url;
  document.getElementById("scene-caption").textContent = data.caption;
  document.getElementById("scene-cartoon-prompt").textContent = data.prompts.cartoon;
  document.getElementById("scene-prompt").textContent = data.prompts.scene;
  sceneCost.textContent = `${state.calls} image calls used for this picture`;

  const download = document.getElementById("download-scene");
  download.href = data.images.scene_url;
  download.download = `${data.scene_key}.png`;

  const warnings = data.warnings || [];
  sceneStatus.className = "status";
  sceneStatus.textContent =
    `Done via ${data.provider} (${data.model}). ` +
    `Generation ${data.generation_id.slice(0, 8)}.` +
    (warnings.length ? ` Note: ${warnings.join(" ")}` : "");

  sceneStage.classList.remove("hidden");
  sceneStage.scrollIntoView({ behavior: "smooth", block: "start" });
}

function setBusy(statusEl, stageEl, message) {
  statusEl.className = "status busy";
  statusEl.textContent = message;
  stageEl.classList.remove("hidden");
  stageEl.scrollIntoView({ behavior: "smooth", block: "start" });
}

function showCartoonError(message) {
  cartoonStatus.className = "status error";
  cartoonStatus.textContent = message;
  cartoonStage.classList.remove("hidden");
}

function showSceneError(message) {
  sceneStatus.className = "status error";
  sceneStatus.textContent = message;
  sceneStage.classList.remove("hidden");
}