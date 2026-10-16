/* Front-end controller for the two-step review flow.
   Deliberately dependency-free — no build step, so Render serves static files
   straight from the repo.

   The flow: cartoonify → review (compare, pick, approve or reject with a reason)
   → compose. Keeping the two API calls apart is the point: a likeness you
   dislike costs one call, not two, and putting an approved portrait into the
   other scene costs one call. */
"use strict";

const form = document.getElementById("generate-form");
const submit = document.getElementById("submit");
const rejectButton = document.getElementById("reject-cartoon");
const approveButton = document.getElementById("approve-cartoon");
const otherSceneButton = document.getElementById("other-scene");
const startOverButton = document.getElementById("start-over");
const oneStep = document.getElementById("one_step");

const cartoonStage = document.getElementById("cartoon-stage");
const sceneStage = document.getElementById("scene-stage");
const cartoonStatus = document.getElementById("cartoon-status");
const sceneStatus = document.getElementById("scene-status");
const cartoonCost = document.getElementById("cartoon-cost");
const sceneCost = document.getElementById("scene-cost");
const candidatePicker = document.getElementById("candidate-picker");
const candidateStrip = document.getElementById("candidate-strip");
const filmstripBlock = document.getElementById("filmstrip-block");
const filmstrip = document.getElementById("filmstrip");
const lightbox = document.getElementById("lightbox");
const lightboxImage = document.getElementById("lightbox-image");
const lightboxCaption = document.getElementById("lightbox-caption");

const photoInput = document.getElementById("photo");
const previewWrap = document.getElementById("preview-wrap");
const preview = document.getElementById("preview");
const intensity = document.getElementById("cartoon_intensity");
const intensityOutput = document.getElementById("intensity-output");

const state = {
  generationId: null,
  calls: 0,
  candidateUrls: [],
  chosen: 0,
  attempts: [],
};

intensity.addEventListener("input", () => {
  intensityOutput.textContent = intensity.value;
});

oneStep.addEventListener("change", () => {
  submit.textContent = oneStep.checked ? "Make both images" : "Step 1 · Cartoonify me";
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
  document.getElementById("original-thumb").src = preview.src;
});

/* Submit: either the whole thing in one go, or step 1 only. */
form.addEventListener("submit", (event) => {
  event.preventDefault();
  if (!hasPhoto()) return;
  if (oneStep.checked) {
    runOneStep();
    return;
  }
  runCartoonify([]);
});

/* Retry with the ticked reasons. With nothing ticked this is just another
   attempt at the same settings, which is why there is no separate retry button. */
rejectButton.addEventListener("click", () => {
  if (!hasPhoto()) return;
  const reasons = selectedReasons();
  runCartoonify(reasons);
});

approveButton.addEventListener("click", () => {
  if (!state.generationId) {
    showCartoonError("Cartoonify first, then approve.");
    return;
  }
  runCompose(currentScene());
});

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

/* Click either image to enlarge it. */
document.querySelectorAll(".zoom").forEach((button) => {
  button.addEventListener("click", () => {
    const which = button.dataset.zoom;
    openLightbox(which === "original" ? document.getElementById("original-thumb").src
                                       : state.candidateUrls[state.chosen],
                 which === "original" ? "The photo you uploaded" : "Your cartoon");
  });
});

document.getElementById("lightbox-close").addEventListener("click", () => lightbox.close());
lightbox.addEventListener("click", (event) => {
  if (event.target === lightbox) lightbox.close();
});

function openLightbox(src, caption) {
  if (!src) return;
  lightboxImage.src = src;
  lightboxCaption.textContent = caption;
  lightbox.showModal();
}

function hasPhoto() {
  if (photoInput.files && photoInput.files.length) return true;
  showCartoonError("Please choose a photo first.");
  return false;
}

function currentScene() {
  return form.querySelector('input[name="scene"]:checked').value;
}

function selectedReasons() {
  return Array.from(
    document.querySelectorAll('#reject-chips input[name="reason"]:checked'),
  ).map((input) => input.value);
}

function reset() {
  state.generationId = null;
  state.calls = 0;
  state.candidateUrls = [];
  state.chosen = 0;
  state.attempts = [];
  cartoonStage.classList.add("hidden");
  sceneStage.classList.add("hidden");
  filmstripBlock.classList.add("hidden");
  clearChips();
}

/* The photo and every setting except the scene and the chips. */
function settingsPayload() {
  const payload = new FormData(form);
  payload.delete("photo");
  payload.delete("scene");
  payload.delete("one_step");
  payload.delete("reason");
  return payload;
}

async function runCartoonify(reasons) {
  const attemptNumber = state.attempts.length + 1;
  setBusy(cartoonStatus, cartoonStage, "Cartoonifying you…");
  submit.disabled = true;
  rejectButton.disabled = true;

  try {
    const body = settingsPayload();
    body.append("photo", photoInput.files[0]);
    reasons.forEach((reason) => body.append("reason", reason));

    const response = await fetch("/api/cartoonify", { method: "POST", body });
    const data = await readJson(response);
    renderCartoon(data, attemptNumber);
  } catch (error) {
    showCartoonError(error.message);
  } finally {
    submit.disabled = false;
    rejectButton.disabled = false;
  }
}

async function runCompose(scene) {
  setBusy(sceneStatus, sceneStage, `Placing you in the scene: ${scene}…`);

  try {
    const body = new FormData();
    body.append("generation_id", state.generationId);
    body.append("scene", scene);
    body.append("candidate", String(state.chosen));

    const response = await fetch("/api/compose", { method: "POST", body });
    const data = await readJson(response);
    renderScene(data);
  } catch (error) {
    showSceneError(error.message);
  }
}

async function runOneStep() {
  setBusy(cartoonStatus, cartoonStage, "Making both images, one step…");
  try {
    const body = settingsPayload();
    body.append("photo", photoInput.files[0]);
    body.append("scene", currentScene());

    const response = await fetch("/api/generate", { method: "POST", body });
    const data = await readJson(response);
    state.calls += data.images.candidate_count || 2;
    state.generationId = data.generation_id;
    renderScene(data, true);
  } catch (error) {
    showCartoonError(error.message);
  }
}

async function readJson(response) {
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.detail || `Request failed (${response.status}).`);
  }
  return data;
}

function renderCartoon(data, attemptNumber) {
  state.generationId = data.generation_id;
  state.calls += 1;
  state.candidateUrls = data.images.candidate_urls || [data.images.cartoon_url];
  state.chosen = 0;

  document.getElementById("cartoon-image").src = state.candidateUrls[0];
  document.getElementById("cartoon-prompt").textContent = data.prompts.cartoon;
  cartoonCost.textContent = `${state.calls} image call${state.calls > 1 ? "s" : ""} used`;

  renderCandidates(state.candidateUrls, data.settings.candidates);

  state.attempts.push({
    url: state.candidateUrls[0],
    style: data.settings.cartoon_style,
    intensity: data.settings.cartoon_intensity,
  });
  renderFilmstrip();

  cartoonStatus.className = "status";
  cartoonStatus.textContent =
    `Attempt ${attemptNumber} ready via ${data.provider}. ` +
    "Compare the two, then approve or tick what went wrong.";

  sceneStage.classList.add("hidden");
  cartoonStage.classList.remove("hidden");
  cartoonStage.scrollIntoView({ behavior: "smooth", block: "start" });
}

function renderCandidates(urls, requested) {
  if (urls.length < 2) {
    candidatePicker.classList.add("hidden");
    candidateStrip.innerHTML = "";
    return;
  }
  candidatePicker.classList.remove("hidden");
  candidateStrip.innerHTML = "";
  urls.forEach((url, index) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `candidate${index === 0 ? " chosen" : ""}`;
    button.innerHTML = `<img src="${url}" alt="Option ${index + 1}"><span>Option ${index + 1}</span>`;
    button.addEventListener("click", () => {
      state.chosen = index;
      document.getElementById("cartoon-image").src = url;
      candidateStrip.querySelectorAll(".candidate").forEach((node, i) => {
        node.classList.toggle("chosen", i === index);
      });
    });
    candidateStrip.appendChild(button);
  });
  if (requested > 1 && urls.length < requested) {
    const note = document.createElement("p");
    note.className = "field-help";
    note.textContent =
      `You asked for ${requested} options; the provider returned ${urls.length}.`;
    candidateStrip.appendChild(note);
  }
}

function renderFilmstrip() {
  if (state.attempts.length < 2) {
    filmstripBlock.classList.add("hidden");
    return;
  }
  filmstripBlock.classList.remove("hidden");
  filmstrip.innerHTML = "";
  state.attempts.forEach((attempt, index) => {
    const figure = document.createElement("figure");
    figure.innerHTML =
      `<img src="${attempt.url}" alt="Attempt ${index + 1}">` +
      `<figcaption>${index + 1} · ${attempt.style} · level ${attempt.intensity}</figcaption>`;
    figure.addEventListener("click", () =>
      openLightbox(attempt.url, `Attempt ${index + 1} · ${attempt.style}`));
    filmstrip.appendChild(figure);
  });
}

function clearChips() {
  document
    .querySelectorAll('#reject-chips input[name="reason"]')
    .forEach((input) => {
      input.checked = false;
    });
}

function renderScene(data, oneStepMode) {
  state.calls += oneStepMode ? 0 : 1;

  document.getElementById("scene-title").textContent = data.scene_title;
  document.getElementById("scene-image").src = data.images.scene_url;
  document.getElementById("scene-cartoon-image").src = data.images.cartoon_url;
  document.getElementById("scene-caption").textContent = data.caption;
  document.getElementById("scene-cartoon-prompt").textContent = data.prompts.cartoon;
  document.getElementById("scene-prompt").textContent = data.prompts.scene;
  sceneCost.textContent = `${state.calls} image call${state.calls > 1 ? "s" : ""} used`;

  const download = document.getElementById("download-scene");
  download.href = data.images.scene_url;
  download.download = `${data.scene_key}.png`;

  const warnings = data.warnings || [];
  sceneStatus.className = "status";
  sceneStatus.textContent =
    `Done via ${data.provider} (${data.model}). ` +
    `Generation ${data.generation_id.slice(0, 8)}.` +
    (warnings.length ? ` Note: ${warnings.join(" ")}` : "");

  cartoonStage.classList.add("hidden");
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