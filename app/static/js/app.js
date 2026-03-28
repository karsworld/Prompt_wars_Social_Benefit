/**
 * BridgeLink — SPA JavaScript
 * Modules: Geo, Tabs, Capture (text/image/voice), Gemini API, Map, Card, Confirm
 */
"use strict";

// ─── State ───────────────────────────────────────────────────────────────────
const state = {
  inputType: "text",
  lat: null,
  lng: null,
  imageFile: null,
  audioBlob: null,
  card: null,
  mediaRecorder: null,
  recordingChunks: [],
  recordingTimer: null,
  recordingSecs: 0,
  mapInstance: null,
  mapMarker: null,
};

// ─── DOM refs ─────────────────────────────────────────────────────────────────
const $ = (id) => document.getElementById(id);

const tabBtns       = document.querySelectorAll(".tab-btn");
const panels        = { text: $("panel-text"), image: $("panel-image"), voice: $("panel-voice") };

const textInput     = $("text-input");
const textCounter   = $("text-counter");

const dropZone      = $("drop-zone");
const imageFileInput= $("image-file");
const imagePreviewW = $("image-preview-wrap");
const imagePreview  = $("image-preview");
const imageClear    = $("image-clear");

const btnRecord     = $("btn-record");
const recordLabel   = $("record-label");
const voiceViz      = $("voice-viz");
const voiceStatus   = $("voice-status");
const voiceTimer    = $("voice-timer");

const locationText  = $("location-text");
const btnRetryGeo   = $("btn-retry-geo");

const btnAnalyze    = $("btn-analyze");
const analyzeLabel  = $("analyze-label");
const analyzeSpinner= $("analyze-spinner");

const errorBanner   = $("error-banner");
const errorMsg      = $("error-msg");

const verificationSection = $("verification-section");
const cardEl        = $("card");
const cardPriority  = $("card-priority");
const cardCategory  = $("card-category");
const cardConfidence= $("card-confidence");
const cardSummary   = $("card-summary");
const cardLocationDesc = $("card-location-desc");
const mapContainer  = $("map");
const payloadType   = $("payload-type");
const payloadUnits  = $("payload-units");
const payloadUrgency= $("payload-urgency");
const payloadNotes  = $("payload-notes");
const btnConfirm    = $("btn-confirm");
const confirmLabel  = $("confirm-label");
const confirmSpinner= $("confirm-spinner");

const ackSection    = $("ack-section");
const ackMessage    = $("ack-message");
const ackId         = $("ack-id");
const btnReset      = $("btn-reset");
const historyList   = $("history-list");

// ─── Geo Module ──────────────────────────────────────────────────────────────
function detectLocation() {
  if (!navigator.geolocation) {
    locationText.textContent = "Geolocation not supported by this browser.";
    btnRetryGeo.hidden = true;
    return;
  }
  locationText.textContent = "Detecting location…";
  btnRetryGeo.hidden = true;

  navigator.geolocation.getCurrentPosition(
    ({ coords }) => {
      state.lat = coords.latitude;
      state.lng = coords.longitude;
      locationText.textContent = `${coords.latitude.toFixed(5)}, ${coords.longitude.toFixed(5)}`;
      btnRetryGeo.hidden = true;
    },
    () => {
      locationText.textContent = "Could not detect location.";
      btnRetryGeo.hidden = false;
    },
    { timeout: 8000 }
  );
}
btnRetryGeo.addEventListener("click", detectLocation);

// ─── Tab Module ───────────────────────────────────────────────────────────────
tabBtns.forEach((btn) => {
  btn.addEventListener("click", () => {
    const type = btn.dataset.type;
    state.inputType = type;

    tabBtns.forEach((b) => {
      b.classList.toggle("active", b === btn);
      b.setAttribute("aria-selected", b === btn ? "true" : "false");
    });

    Object.entries(panels).forEach(([key, panel]) => {
      if (key === type) {
        panel.classList.add("active");
        panel.hidden = false;
      } else {
        panel.classList.remove("active");
        panel.hidden = true;
      }
    });

    hideError();
  });
});

// ─── Text Module ─────────────────────────────────────────────────────────────
textInput.addEventListener("input", () => {
  textCounter.textContent = `${textInput.value.length} / 2000`;
});

// ─── Image Module ─────────────────────────────────────────────────────────────
function setImageFile(file) {
  if (!file) return;
  const allowed = ["image/jpeg", "image/png", "image/webp"];
  if (!allowed.includes(file.type)) {
    showError("Please upload a JPEG, PNG, or WebP image.");
    return;
  }
  if (file.size > 5 * 1024 * 1024) {
    showError("Image must be smaller than 5 MB.");
    return;
  }
  state.imageFile = file;
  const url = URL.createObjectURL(file);
  imagePreview.src = url;
  imagePreview.alt = `Selected image: ${file.name}`;
  imagePreviewW.hidden = false;
  dropZone.hidden = true;
  hideError();
}

dropZone.addEventListener("click", () => imageFileInput.click());
dropZone.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") imageFileInput.click(); });

dropZone.addEventListener("dragover", (e) => { e.preventDefault(); dropZone.classList.add("drag-over"); });
dropZone.addEventListener("dragleave", () => dropZone.classList.remove("drag-over"));
dropZone.addEventListener("drop", (e) => {
  e.preventDefault();
  dropZone.classList.remove("drag-over");
  const file = e.dataTransfer?.files?.[0];
  if (file) setImageFile(file);
});

imageFileInput.addEventListener("change", () => {
  const file = imageFileInput.files?.[0];
  if (file) setImageFile(file);
});

imageClear.addEventListener("click", () => {
  state.imageFile = null;
  imagePreview.src = "";
  imagePreviewW.hidden = true;
  dropZone.hidden = false;
  imageFileInput.value = "";
});

// ─── Voice Module ─────────────────────────────────────────────────────────────
async function startRecording() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    state.recordingChunks = [];

    const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
      ? "audio/webm;codecs=opus"
      : "audio/webm";

    state.mediaRecorder = new MediaRecorder(stream, { mimeType });
    state.mediaRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) state.recordingChunks.push(e.data);
    };
    state.mediaRecorder.onstop = () => {
      state.audioBlob = new Blob(state.recordingChunks, { type: mimeType });
      stream.getTracks().forEach((t) => t.stop());
      voiceStatus.textContent = `Recording saved (${state.recordingSecs}s). Ready to analyze.`;
    };

    state.mediaRecorder.start(100);
    btnRecord.classList.add("recording");
    btnRecord.setAttribute("aria-pressed", "true");
    btnRecord.setAttribute("aria-label", "Stop voice recording");
    recordLabel.textContent = "Recording…";
    voiceViz.classList.add("active");
    voiceStatus.textContent = "Recording in progress…";

    // Timer
    state.recordingSecs = 0;
    voiceTimer.hidden = false;
    voiceTimer.textContent = "0s";
    state.recordingTimer = setInterval(() => {
      state.recordingSecs += 1;
      voiceTimer.textContent = `${state.recordingSecs}s`;
      // Auto-stop at 60s
      if (state.recordingSecs >= 60) stopRecording();
    }, 1000);
  } catch (err) {
    voiceStatus.textContent = "Microphone access denied. Please allow mic permissions.";
  }
}

function stopRecording() {
  if (state.mediaRecorder?.state === "recording") {
    state.mediaRecorder.stop();
  }
  clearInterval(state.recordingTimer);
  btnRecord.classList.remove("recording");
  btnRecord.setAttribute("aria-pressed", "false");
  btnRecord.setAttribute("aria-label", "Start voice recording");
  recordLabel.textContent = "Hold to Record";
  voiceViz.classList.remove("active");
  voiceTimer.hidden = true;
}

let isRecording = false;
btnRecord.addEventListener("mousedown", () => { if (!isRecording) { isRecording = true; startRecording(); } });
btnRecord.addEventListener("mouseup",  () => { if (isRecording)  { isRecording = false; stopRecording(); } });
btnRecord.addEventListener("mouseleave",() => { if (isRecording)  { isRecording = false; stopRecording(); } });
btnRecord.addEventListener("touchstart",(e) => { e.preventDefault(); if (!isRecording) { isRecording = true; startRecording(); } });
btnRecord.addEventListener("touchend", (e) => { e.preventDefault(); if (isRecording)  { isRecording = false; stopRecording(); } });
btnRecord.addEventListener("keydown", (e) => {
  if ((e.key === "Enter" || e.key === " ") && !isRecording) { e.preventDefault(); isRecording = true; startRecording(); }
});
btnRecord.addEventListener("keyup", (e) => {
  if ((e.key === "Enter" || e.key === " ") && isRecording) { e.preventDefault(); isRecording = false; stopRecording(); }
});

// ─── Error helpers ────────────────────────────────────────────────────────────
function showError(msg) {
  errorMsg.textContent = msg;
  errorBanner.hidden = false;
  errorBanner.scrollIntoView({ behavior: "smooth", block: "nearest" });
}
function hideError() { errorBanner.hidden = true; }

// ─── Analyze ─────────────────────────────────────────────────────────────────
btnAnalyze.addEventListener("click", async () => {
  hideError();

  const fd = new FormData();
  fd.append("input_type", state.inputType);
  if (state.lat !== null) fd.append("lat", state.lat);
  if (state.lng !== null) fd.append("lng", state.lng);

  if (state.inputType === "text") {
    const t = textInput.value.trim();
    if (!t) { showError("Please describe the incident before analyzing."); return; }
    fd.append("text", t);
  } else if (state.inputType === "image") {
    if (!state.imageFile) { showError("Please select an image before analyzing."); return; }
    fd.append("file", state.imageFile, state.imageFile.name);
  } else if (state.inputType === "voice") {
    if (!state.audioBlob) { showError("Please record a voice message before analyzing."); return; }
    fd.append("file", state.audioBlob, "recording.webm");
  }

  setAnalyzeLoading(true);

  try {
    const res = await fetch("/api/capture", { method: "POST", body: fd });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Server error." }));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }
    state.card = await res.json();
    renderCard(state.card);
    await fetchHistory(); // Update history immediately
  } catch (err) {
    showError(`Analysis failed: ${err.message}`);
  } finally {
    setAnalyzeLoading(false);
  }
});

function setAnalyzeLoading(loading) {
  btnAnalyze.disabled = loading;
  btnAnalyze.setAttribute("aria-busy", loading ? "true" : "false");
  analyzeLabel.hidden = loading;
  analyzeSpinner.hidden = !loading;
}

// ─── Card Renderer ────────────────────────────────────────────────────────────
function renderCard(card) {
  // Priority
  cardPriority.textContent = card.priority;
  cardPriority.dataset.priority = card.priority;
  cardPriority.setAttribute("aria-label", `Priority ${card.priority}`);

  // Category
  cardCategory.textContent = card.category;

  // Confidence
  const pct = Math.round((card.confidence || 0) * 100);
  cardConfidence.textContent = `${pct}% confidence`;

  // Summary
  cardSummary.textContent = card.summary;

  // Location
  cardLocationDesc.textContent = card.location?.description || "Unknown";

  // Payload
  const ap = card.action_payload || {};
  payloadType.textContent    = ap.dispatch_type   || "—";
  payloadUnits.textContent   = `${ap.units_needed ?? "—"} unit${ap.units_needed !== 1 ? "s" : ""}`;
  payloadUrgency.textContent = ap.urgency_minutes != null
    ? ap.urgency_minutes < 60
      ? `${ap.urgency_minutes} min`
      : `${Math.round(ap.urgency_minutes / 60)} hr`
    : "—";
  payloadNotes.textContent = ap.notes || "";

  // Map
  initMap(card.location?.lat, card.location?.lng, card.location?.description);

  // Show section
  verificationSection.hidden = false;
  ackSection.hidden = true;
  verificationSection.scrollIntoView({ behavior: "smooth", block: "start" });
}

// ─── Google Maps ──────────────────────────────────────────────────────────────
let mapsLoaded = false;
let mapsLoadCallbacks = [];

function loadGoogleMaps(apiKey) {
  if (mapsLoaded) return;
  mapsLoaded = true;
  const script = document.createElement("script");
  script.src = `https://maps.googleapis.com/maps/api/js?key=${apiKey}&callback=_mapsReady`;
  script.async = true;
  script.defer = true;
  document.getElementById("maps-script-container").appendChild(script);
}

window._mapsReady = function () {
  mapsLoadCallbacks.forEach((cb) => cb());
  mapsLoadCallbacks = [];
};

function initMap(lat, lng, label) {
  const hasCoords = lat != null && lng != null;
  const center = hasCoords ? { lat: Number(lat), lng: Number(lng) } : { lat: 0, lng: 0 };

  const key = window.__MAPS_KEY__;
  if (!key) {
    mapContainer.innerHTML = `<div style="display:flex;align-items:center;justify-content:center;height:100%;color:var(--text-muted);font-size:.85rem;">📍 ${label || "Location not pinned — GOOGLE_MAPS_API_KEY not set"}</div>`;
    return;
  }

  const renderMap = () => {
    if (state.mapInstance) {
      state.mapInstance.setCenter(center);
      state.mapInstance.setZoom(hasCoords ? 15 : 2);
      if (state.mapMarker) {
        state.mapMarker.setPosition(center);
        state.mapMarker.setTitle(label || "Incident");
      }
      return;
    }
    state.mapInstance = new google.maps.Map(mapContainer, {
      center,
      zoom: hasCoords ? 15 : 2,
      mapTypeId: "roadmap",
      styles: darkMapStyles(),
      disableDefaultUI: true,
      zoomControl: true,
    });
    if (hasCoords) {
      state.mapMarker = new google.maps.Marker({
        position: center,
        map: state.mapInstance,
        title: label || "Incident",
        animation: google.maps.Animation.DROP,
      });
    }
  };

  if (window.google?.maps) {
    renderMap();
  } else {
    mapsLoadCallbacks.push(renderMap);
    loadGoogleMaps(key);
  }
}

function darkMapStyles() {
  return [
    { elementType: "geometry",           stylers: [{ color: "#0e1018" }] },
    { elementType: "labels.text.stroke", stylers: [{ color: "#07080f" }] },
    { elementType: "labels.text.fill",   stylers: [{ color: "#8b90b4" }] },
    { featureType: "road",                elementType: "geometry",  stylers: [{ color: "#181b27" }] },
    { featureType: "road",                elementType: "labels.text.fill", stylers: [{ color: "#545878" }] },
    { featureType: "water",               elementType: "geometry",  stylers: [{ color: "#07080f" }] },
    { featureType: "poi",                 elementType: "geometry",  stylers: [{ color: "#12141e" }] },
    { featureType: "transit",             elementType: "geometry",  stylers: [{ color: "#12141e" }] },
    { featureType: "administrative",      elementType: "geometry.stroke", stylers: [{ color: "#181b27" }] },
  ];
}

// ─── Confirm & Dispatch ───────────────────────────────────────────────────────
btnConfirm.addEventListener("click", async () => {
  if (!state.card) return;
  setConfirmLoading(true);
  try {
    const res = await fetch("/api/confirm", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ card: state.card, confirmed_by: "field_operator" }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Dispatch failed." }));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }
    const ack = await res.json();
    renderAck(ack);
  } catch (err) {
    showError(`Dispatch failed: ${err.message}`);
  } finally {
    setConfirmLoading(false);
  }
});

function setConfirmLoading(loading) {
  btnConfirm.disabled = loading;
  btnConfirm.setAttribute("aria-busy", loading ? "true" : "false");
  confirmLabel.hidden = loading;
  confirmSpinner.hidden = !loading;
}

function renderAck(ack) {
  ackMessage.textContent = ack.message;
  ackId.textContent = ack.dispatch_id;
  ackSection.hidden = false;
  verificationSection.hidden = true;
  ackSection.scrollIntoView({ behavior: "smooth", block: "start" });
}

// ─── Reset ────────────────────────────────────────────────────────────────────
btnReset.addEventListener("click", () => {
  state.card = null;
  state.imageFile = null;
  state.audioBlob = null;
  state.mapInstance = null;
  state.mapMarker = null;

  textInput.value = "";
  textCounter.textContent = "0 / 2000";
  imagePreview.src = "";
  imagePreviewW.hidden = true;
  dropZone.hidden = false;
  imageFileInput.value = "";
  voiceStatus.textContent = "Press and hold the button to start recording";
  voiceTimer.hidden = true;

  verificationSection.hidden = true;
  ackSection.hidden = true;
  hideError();

  window.scrollTo({ top: 0, behavior: "smooth" });
});

// ─── History Module ──────────────────────────────────────────────────────────
async function fetchHistory() {
  try {
    const res = await fetch("/api/incidents");
    if (!res.ok) return;
    const items = await res.json();
    renderHistory(items);
  } catch (err) {
    console.error("Failed to fetch history:", err);
  }
}

function renderHistory(items) {
  if (!items || items.length === 0) {
    historyList.innerHTML = '<div class="empty-history">No activity yet. Reports will appear here once analyzed.</div>';
    return;
  }

  historyList.innerHTML = items.map(item => `
    <div class="history-card" data-priority="${item.priority}">
      <div class="hc-header">
        <span class="hc-priority">${item.priority}</span>
        <span class="hc-category">${item.category}</span>
        <span class="hc-time">${new Date(item.created_at || Date.now()).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
      </div>
      <p class="hc-summary">${item.summary}</p>
      <div class="hc-footer">
        <span>📍 ${item.location?.description || "Unknown"}</span>
        <span>${Math.round(item.confidence * 100)}%</span>
      </div>
    </div>
  `).join('');
}

// ─── Boot: inject Maps key from server config endpoint ───────────────────────
(async () => {
  try {
    const res = await fetch("/api/config");
    if (res.ok) {
      const cfg = await res.json();
      if (cfg.maps_key) window.__MAPS_KEY__ = cfg.maps_key;
    }
  } catch (_) {
    // Maps key unavailable — map will show placeholder text
  }
  await fetchHistory();
  detectLocation();
})();
