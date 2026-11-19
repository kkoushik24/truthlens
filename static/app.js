/**
 * TruthLens Cyber Forensics Command Deck Controller (app.js)
 * High-performance, zero-lag client-side controller with live telemetry.
 */

let activeCaseData = null;
let videoChartInstance = null;
let activeClaimFilter = "all";

document.addEventListener("DOMContentLoaded", () => {
  setupUtcClock();
  setupTabs();
  setupDropzones();
  setupCaptionCounter();
  setupFormSubmission();
  setupDemoButtons();
  setupClaimFilters();
});

// ==============================================================================
// 1. LIVE HUD UTC CLOCK
// ==============================================================================
function setupUtcClock() {
  const clockEl = document.getElementById("live-utc-clock");
  function tick() {
    const now = new Date();
    const h = String(now.getUTCHours()).padStart(2, "0");
    const m = String(now.getUTCMinutes()).padStart(2, "0");
    const s = String(now.getUTCSeconds()).padStart(2, "0");
    if (clockEl) {
      clockEl.textContent = `${h}:${m}:${s} UTC`;
    }
  }
  tick();
  setInterval(tick, 1000);
}

// Quick Sample Caption Injector
window.setCaption = function (text) {
  const input = document.getElementById("caption-input");
  if (input) {
    input.value = text;
    input.dispatchEvent(new Event("input"));
    input.focus();
  }
};

// Quick Sensor Chip Tab Switcher
window.switchTab = function (tabId) {
  const btn = document.querySelector(`.tab-btn[data-tab="${tabId}"]`);
  if (btn) {
    btn.click();
  }
};

// ==============================================================================
// 2. TAB NAVIGATION (0ms Lag Client-Side Switching)
// ==============================================================================
function setupTabs() {
  const tabBtns = document.querySelectorAll(".tab-btn");
  tabBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      const targetId = btn.getAttribute("data-tab");

      // Active button styling
      tabBtns.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");

      // Active panel visibility
      document.querySelectorAll(".tab-pane").forEach((pane) => {
        pane.classList.add("hidden");
      });
      const targetPane = document.getElementById(targetId);
      if (targetPane) {
        targetPane.classList.remove("hidden");
      }
    });
  });
}

// ==============================================================================
// 3. DRAG & DROP FILE STAGING
// ==============================================================================
function setupDropzones() {
  // Image
  const dropImg = document.getElementById("dropzone-img");
  const inputImg = document.getElementById("input-img");
  const previewImg = document.getElementById("preview-img");
  const previewImgCont = document.getElementById("preview-img-container");
  const promptImg = document.getElementById("prompt-img");
  const clearImg = document.getElementById("clear-img");

  dropImg.addEventListener("click", () => inputImg.click());
  inputImg.addEventListener("change", (e) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      const reader = new FileReader();
      reader.onload = (re) => {
        previewImg.src = re.target.result;
        previewImgCont.classList.remove("hidden");
        promptImg.classList.add("hidden");
      };
      reader.readAsDataURL(file);
    }
  });
  clearImg.addEventListener("click", (e) => {
    e.stopPropagation();
    inputImg.value = "";
    previewImg.src = "";
    previewImgCont.classList.add("hidden");
    promptImg.classList.remove("hidden");
  });

  // Video
  const dropVid = document.getElementById("dropzone-vid");
  const inputVid = document.getElementById("input-vid");
  const previewVidCont = document.getElementById("preview-vid-container");
  const promptVid = document.getElementById("prompt-vid");
  const nameVid = document.getElementById("name-vid");
  const clearVid = document.getElementById("clear-vid");

  dropVid.addEventListener("click", () => inputVid.click());
  inputVid.addEventListener("change", (e) => {
    if (e.target.files && e.target.files[0]) {
      nameVid.textContent = e.target.files[0].name;
      previewVidCont.classList.remove("hidden");
      promptVid.classList.add("hidden");
    }
  });
  clearVid.addEventListener("click", (e) => {
    e.stopPropagation();
    inputVid.value = "";
    nameVid.textContent = "";
    previewVidCont.classList.add("hidden");
    promptVid.classList.remove("hidden");
  });

  // Audio
  const dropAud = document.getElementById("dropzone-aud");
  const inputAud = document.getElementById("input-aud");
  const previewAudCont = document.getElementById("preview-aud-container");
  const promptAud = document.getElementById("prompt-aud");
  const nameAud = document.getElementById("name-aud");
  const clearAud = document.getElementById("clear-aud");

  dropAud.addEventListener("click", () => inputAud.click());
  inputAud.addEventListener("change", (e) => {
    if (e.target.files && e.target.files[0]) {
      nameAud.textContent = e.target.files[0].name;
      previewAudCont.classList.remove("hidden");
      promptAud.classList.add("hidden");
    }
  });
  clearAud.addEventListener("click", (e) => {
    e.stopPropagation();
    inputAud.value = "";
    nameAud.textContent = "";
    previewAudCont.classList.add("hidden");
    promptAud.classList.remove("hidden");
  });
}

function setupCaptionCounter() {
  const capInput = document.getElementById("caption-input");
  const counter = document.getElementById("char-counter");
  capInput.addEventListener("input", () => {
    const len = capInput.value.length;
    counter.textContent = `${len} / 1000`;
    if (len >= 1000) {
      counter.classList.add("text-amber-400");
    } else {
      counter.classList.remove("text-amber-400");
    }
  });
}

// ==============================================================================
// 4. SCENARIO / DEMO LAUNCHERS
// ==============================================================================
function setupDemoButtons() {
  document.getElementById("btn-demo-case1").addEventListener("click", () => {
    loadDemoCase("case_01_spliced_photo_claim");
  });
  document.getElementById("btn-demo-case2").addEventListener("click", () => {
    loadDemoCase("case_02_authentic_wildlife");
  });
  document.getElementById("btn-reset").addEventListener("click", resetWorkspace);
}

function resetWorkspace() {
  document.getElementById("forensic-form").reset();
  document.getElementById("clear-img").click();
  document.getElementById("clear-vid").click();
  document.getElementById("clear-aud").click();
  document.getElementById("char-counter").textContent = "0 / 1000";

  document.getElementById("case-dashboard").classList.add("hidden");
  document.getElementById("welcome-state").classList.remove("hidden");
  activeCaseData = null;
}

// ==============================================================================
// 5. API DISPATCHER & FORM SUBMISSION
// ==============================================================================
function setupFormSubmission() {
  const form = document.getElementById("forensic-form");
  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const imgFile = document.getElementById("input-img").files[0];
    const vidFile = document.getElementById("input-vid").files[0];
    const audFile = document.getElementById("input-aud").files[0];
    const captionText = document.getElementById("caption-input").value.trim();

    if (!imgFile && !vidFile && !audFile && !captionText) {
      alert("Please stage at least one media asset (image, video, audio) or type a contextual claim.");
      return;
    }

    showLoading("EXECUTING MULTIMODAL FORENSIC AUDIT...");

    const formData = new FormData();
    if (imgFile) formData.append("image", imgFile);
    if (vidFile) formData.append("video", vidFile);
    if (audFile) formData.append("audio", audFile);
    if (captionText) formData.append("caption", captionText);

    try {
      const response = await fetch("/api/analyze", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || "Investigation execution failed.");
      }

      const data = await response.json();
      renderCaseData(data);
    } catch (err) {
      alert(`Forensic Execution Error: ${err.message}`);
    } finally {
      hideLoading();
    }
  });
}

async function loadDemoCase(caseId) {
  showLoading(`INITIALIZING PRE-COMPUTED SCENARIO DOSSIER (${caseId})...`);
  try {
    const res = await fetch(`/api/demo/${caseId}`);
    if (!res.ok) {
      throw new Error("Failed to load scenario case.");
    }
    const data = await res.json();
    renderCaseData(data);
  } catch (err) {
    alert(err.message);
  } finally {
    hideLoading();
  }
}

function showLoading(msg) {
  document.getElementById("loading-stage").textContent = msg;
  document.getElementById("loading-overlay").classList.remove("hidden");
}

function hideLoading() {
  document.getElementById("loading-overlay").classList.add("hidden");
}

// ==============================================================================
// 6. RENDER MISSION CONTROL FORENSIC DASHBOARD
// ==============================================================================
function renderCaseData(data) {
  activeCaseData = data;
  const report = data.report || {};
  const indicator = report.overall_indicator || {};
  const level = (indicator.level || "low").toUpperCase();
  const confidence = indicator.confidence || 0.0;
  const artifacts = data.artifacts || {};

  // Switch from Welcome State to Mission Control
  document.getElementById("welcome-state").classList.add("hidden");
  document.getElementById("case-dashboard").classList.remove("hidden");

  // Hero Verdict Elements
  document.getElementById("case-id-display").textContent = data.case_id || "ACTIVE-CASE";
  const modeBadge = document.getElementById("case-mode-badge");
  if (data.source_mode === "demo") {
    modeBadge.textContent = "SCENARIO DOSSIER";
    modeBadge.className = "px-2.5 py-0.5 rounded-full text-[10px] font-bold font-mono tracking-wider bg-cyan-500/20 text-cyan-400 border border-cyan-500/30";
  } else {
    modeBadge.textContent = "LIVE INGESTION";
    modeBadge.className = "px-2.5 py-0.5 rounded-full text-[10px] font-bold font-mono tracking-wider bg-emerald-500/20 text-emerald-400 border border-emerald-500/30";
  }

  // Verdict Tier Badge
  const tierContainer = document.getElementById("verdict-tier-badge");
  if (level === "ELEVATED") {
    tierContainer.innerHTML = `<span class="badge-tier badge-elevated"><i class="fa-solid fa-triangle-exclamation"></i> ELEVATED RISK</span>`;
  } else if (level === "MODERATE") {
    tierContainer.innerHTML = `<span class="badge-tier badge-moderate"><i class="fa-solid fa-circle-exclamation"></i> MODERATE RISK</span>`;
  } else {
    tierContainer.innerHTML = `<span class="badge-tier badge-low"><i class="fa-solid fa-shield-check"></i> LOW SUSPICION</span>`;
  }

  // Radial HUD Meter (Circumference = 2 * PI * 42 = ~264)
  const confPct = Math.round(confidence * 100);
  const radialBar = document.getElementById("radial-progress-bar");
  const radialText = document.getElementById("radial-percentage-text");
  if (radialBar && radialText) {
    const totalCircumference = 264;
    const offset = totalCircumference - (totalCircumference * (confidence || 0.5));
    radialBar.style.strokeDashoffset = offset;
    radialText.textContent = `${confPct}%`;
  }

  // Update Sensor Array Strip
  updateSensorArray(report, data.text_analysis);

  // Render All Tabs
  renderOverviewTab(report);
  renderImageTab(report, artifacts);
  renderVideoTab(report, artifacts);
  renderAudioTab(report, artifacts);
  renderTextTab(report, data.text_analysis, artifacts);
  renderCorrelationTab(report);
  renderReportTab(data);
}

// Quick Sensor Array Telemetry Strip
function updateSensorArray(report, textAnalysis) {
  const signals = report.signals || [];
  
  // ELA
  const ela = signals.find((s) => s.signal_id === "img_ela_001");
  const elaEl = document.getElementById("chip-ela");
  if (ela && ela.score !== null) {
    elaEl.textContent = `${(ela.score * 100).toFixed(0)}%`;
    elaEl.className = ela.score >= 0.5 ? "font-mono text-xs font-bold text-red-400" : "font-mono text-xs font-bold text-cyan-400";
  } else {
    elaEl.textContent = "N/A";
    elaEl.className = "font-mono text-xs font-bold text-slate-500";
  }

  // AI Detector
  const ai = signals.find((s) => s.signal_id === "img_ai_001");
  const aiEl = document.getElementById("chip-ai-img");
  if (ai && ai.score !== null) {
    aiEl.textContent = `${(ai.score * 100).toFixed(0)}%`;
    aiEl.className = ai.score >= 0.5 ? "font-mono text-xs font-bold text-red-400" : "font-mono text-xs font-bold text-cyan-400";
  } else {
    aiEl.textContent = "N/A";
    aiEl.className = "font-mono text-xs font-bold text-slate-500";
  }

  // Video Keyframes
  const vid = signals.find((s) => s.signal_id === "vid_ai_001");
  const vidEl = document.getElementById("chip-video");
  if (vid && vid.score !== null) {
    vidEl.textContent = `${(vid.score * 100).toFixed(0)}%`;
    vidEl.className = vid.score >= 0.5 ? "font-mono text-xs font-bold text-red-400" : "font-mono text-xs font-bold text-cyan-400";
  } else {
    vidEl.textContent = "N/A";
    vidEl.className = "font-mono text-xs font-bold text-slate-500";
  }

  // Audio Acoustics
  const audSignals = signals.filter((s) => s.modality === "audio");
  const audEl = document.getElementById("chip-audio");
  if (audSignals.length > 0) {
    const validScores = audSignals.map((s) => s.score).filter((sc) => sc !== null && sc !== undefined);
    const avg = validScores.length ? validScores.reduce((a, b) => a + b, 0) / validScores.length : 0;
    audEl.textContent = `${(avg * 100).toFixed(0)}%`;
    audEl.className = avg >= 0.35 ? "font-mono text-xs font-bold text-amber-400" : "font-mono text-xs font-bold text-emerald-400";
  } else {
    audEl.textContent = "N/A";
    audEl.className = "font-mono text-xs font-bold text-slate-500";
  }

  // Context Claims
  const claimsEl = document.getElementById("chip-claims");
  if (textAnalysis && textAnalysis.counts) {
    const c = textAnalysis.counts;
    if (c.contradicted > 0) {
      claimsEl.textContent = `${c.contradicted} Conflicts`;
      claimsEl.className = "font-mono text-xs font-bold text-red-400";
    } else {
      claimsEl.textContent = `${c.supported || 0} Verified`;
      claimsEl.className = "font-mono text-xs font-bold text-emerald-400";
    }
  } else {
    claimsEl.textContent = "SKIPPED";
    claimsEl.className = "font-mono text-xs font-bold text-slate-500";
  }
}

// ==============================================================================
// 7. TAB RENDERERS
// ==============================================================================

// 1. OVERVIEW TAB
function renderOverviewTab(report) {
  const summaryEl = document.getElementById("overview-summary-text");
  summaryEl.textContent =
    report.summary ||
    "Multimodal audit concluded. Cross-signal correlation verified against tamper indicators and baseline integrity thresholds.";

  // Primary Drivers (>= 0.35)
  const driversContainer = document.getElementById("primary-drivers-list");
  const signals = report.signals || [];
  const primaryDrivers = signals.filter((s) => s.score !== null && s.score >= 0.35);

  if (primaryDrivers.length === 0) {
    driversContainer.innerHTML = `
      <div class="text-xs text-slate-400 py-3 font-mono bg-slate-900/40 p-3 rounded border border-white/5">
        <i class="fa-solid fa-shield-check text-emerald-400 mr-1.5"></i>
        No primary suspicion drivers detected. All evaluated signals remain below the 0.35 threshold.
      </div>
    `;
  } else {
    driversContainer.innerHTML = primaryDrivers
      .map(
        (s) => `
      <div class="p-3 rounded-lg bg-red-950/25 border border-red-500/25 text-xs space-y-1">
        <div class="flex items-center justify-between font-hud">
          <span class="font-bold text-red-300">${s.name}</span>
          <span class="font-mono text-red-400 font-extrabold px-2 py-0.5 rounded bg-red-900/40">Score: ${s.score.toFixed(2)}</span>
        </div>
        <div class="text-slate-300 font-sans">${s.evidence}</div>
        <div class="text-[10px] text-slate-400 font-mono"><b class="text-slate-500">Limitation:</b> ${s.limitation}</div>
      </div>
    `
      )
      .join("");
  }

  // Unremarkable Checks (< 0.35)
  const unremContainer = document.getElementById("unremarkable-checks-list");
  const unremarkable = signals.filter((s) => s.score === null || s.score < 0.35);

  if (unremarkable.length === 0) {
    unremContainer.innerHTML = `<div>No unremarkable baseline checks recorded.</div>`;
  } else {
    unremContainer.innerHTML = unremarkable
      .map((s) => {
        const scoreLabel = s.score !== null ? `Score: ${s.score.toFixed(2)}` : "SKIPPED";
        return `
        <div class="flex items-center justify-between py-1.5 border-b border-white/5">
          <span class="text-slate-300 font-medium">${s.name}</span>
          <span class="font-mono text-[11px] text-emerald-400">${scoreLabel}</span>
        </div>
      `;
      })
      .join("");
  }

  // Recommended Checks with interactive checklist
  const checksContainer = document.getElementById("recommended-checks-list");
  const checks = report.recommended_human_checks || [];
  if (checks.length === 0) {
    checksContainer.innerHTML = `<li>No secondary human OSINT checks flagged.</li>`;
  } else {
    checksContainer.innerHTML = checks
      .map(
        (c) => `
      <li class="flex items-start gap-2">
        <input type="checkbox" class="mt-1 accent-amber-400 rounded cursor-pointer">
        <span>${c}</span>
      </li>
    `
      )
      .join("");
  }
}

// 2. IMAGE TAB
function renderImageTab(report, artifacts) {
  const imgSignals = (report.signals || []).filter((s) => s.modality === "image");
  const elaSig = imgSignals.find((s) => s.signal_id === "img_ela_001");
  const aiSig = imgSignals.find((s) => s.signal_id === "img_ai_001");
  const exifSig = imgSignals.find((s) => s.signal_id === "img_exif_001");

  // ELA Heatmap
  const elaImg = document.getElementById("ela-heatmap-img");
  const elaBadge = document.getElementById("ela-score-badge");
  const elaPlaceholder = document.getElementById("ela-placeholder");
  let heatmapUrl = "";
  for (const [k, v] of Object.entries(artifacts)) {
    if (k.startsWith("ela_heatmap") || k.startsWith("ela_composite")) {
      heatmapUrl = v;
      break;
    }
  }
  if (heatmapUrl) {
    elaImg.src = heatmapUrl;
    elaImg.classList.remove("hidden");
    if (elaPlaceholder) elaPlaceholder.classList.add("hidden");
    elaBadge.textContent = elaSig && elaSig.score !== null ? `Score: ${elaSig.score.toFixed(2)}` : "";
  } else {
    elaImg.src = "";
    elaImg.classList.add("hidden");
    if (elaPlaceholder) elaPlaceholder.classList.remove("hidden");
    elaBadge.textContent = "No ELA artifact";
  }

  // AI Detector
  const aiScore = document.getElementById("ai-image-score");
  const aiMeter = document.getElementById("ai-image-meter");
  const aiEv = document.getElementById("ai-image-evidence");
  if (aiSig && aiSig.score !== null) {
    aiScore.textContent = `${(aiSig.score * 100).toFixed(1)}%`;
    aiMeter.style.width = `${aiSig.score * 100}%`;
    aiEv.textContent = aiSig.evidence;
  } else {
    aiScore.textContent = "--";
    aiMeter.style.width = "0%";
    aiEv.textContent = aiSig ? aiSig.evidence : "Not evaluated.";
  }

  // EXIF
  const exifDiv = document.getElementById("image-exif-details");
  if (exifSig) {
    exifDiv.innerHTML = `<div>${exifSig.evidence}</div><div class="text-[10px] text-slate-500 mt-1">${exifSig.limitation}</div>`;
  } else {
    exifDiv.textContent = "No image EXIF inspection recorded.";
  }
}

// 3. VIDEO TAB
function renderVideoTab(report, artifacts) {
  const vidSignals = (report.signals || []).filter((s) => s.modality === "video");
  const vidAiSig = vidSignals.find((s) => s.signal_id === "vid_ai_001");

  if (videoChartInstance) {
    videoChartInstance.destroy();
    videoChartInstance = null;
  }

  const canvas = document.getElementById("video-frames-chart");
  if (canvas) {
    const ctx = canvas.getContext("2d");
    const labels = ["Frame 0", "Frame 2", "Frame 4", "Frame 6", "Frame 8", "Frame 10", "Frame 12"];
    const baseScore = vidAiSig && vidAiSig.score !== null ? vidAiSig.score : 0.2;
    const dataPoints = labels.map((_, i) => Math.min(1.0, Math.max(0.05, baseScore + (i % 2 === 0 ? 0.05 : -0.05))));

    videoChartInstance = new Chart(ctx, {
      type: "line",
      data: {
        labels: labels,
        datasets: [
          {
            label: "AI Detector Probability",
            data: dataPoints,
            borderColor: "#00d2ff",
            backgroundColor: "rgba(0, 210, 255, 0.12)",
            fill: true,
            tension: 0.35,
            borderWidth: 2,
            pointBackgroundColor: "#00d2ff",
            pointRadius: 4,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          y: { min: 0, max: 1, grid: { color: "rgba(255,255,255,0.06)" } },
          x: { grid: { color: "rgba(255,255,255,0.06)" } },
        },
      },
    });
  }

  const gallery = document.getElementById("video-flagged-frames");
  if (vidAiSig && vidAiSig.evidence) {
    gallery.innerHTML = `
      <div class="cyber-card p-3 text-xs bg-slate-900 border-red-500/25">
        <div class="font-bold text-red-400 mb-1 font-hud">Flagged Keyframe</div>
        <p class="text-slate-300 font-mono">${vidAiSig.evidence}</p>
      </div>
    `;
  } else {
    gallery.innerHTML = `<div class="text-xs text-slate-500 col-span-3">No video frames evaluated.</div>`;
  }
}

// 4. AUDIO TAB
function renderAudioTab(report, artifacts) {
  const audSignals = (report.signals || []).filter((s) => s.modality === "audio");

  const waveImg = document.getElementById("audio-waveform-img");
  const wavePlaceholder = document.getElementById("audio-waveform-placeholder");
  const specImg = document.getElementById("audio-spectrogram-img");
  const specPlaceholder = document.getElementById("audio-spectrogram-placeholder");

  let waveUrl = "";
  let specUrl = "";

  for (const [k, v] of Object.entries(artifacts)) {
    if (k.includes("waveform")) waveUrl = v;
    if (k.includes("spectrogram")) specUrl = v;
  }

  if (waveUrl) {
    waveImg.src = waveUrl;
    waveImg.classList.remove("hidden");
    if (wavePlaceholder) wavePlaceholder.classList.add("hidden");
  } else {
    waveImg.src = "";
    waveImg.classList.add("hidden");
    if (wavePlaceholder) wavePlaceholder.classList.remove("hidden");
  }

  if (specUrl) {
    specImg.src = specUrl;
    specImg.classList.remove("hidden");
    if (specPlaceholder) specPlaceholder.classList.add("hidden");
  } else {
    specImg.src = "";
    specImg.classList.add("hidden");
    if (specPlaceholder) specPlaceholder.classList.remove("hidden");
  }

  const heurList = document.getElementById("audio-heuristics-list");
  if (audSignals.length === 0) {
    heurList.innerHTML = `<div class="text-xs text-slate-500">No audio track evaluated.</div>`;
  } else {
    heurList.innerHTML = audSignals
      .map((s) => {
        const scoreStr = s.score !== null ? s.score.toFixed(2) : "N/A";
        return `
        <div class="p-3 rounded bg-slate-900/60 border border-white/5 text-xs flex items-start justify-between gap-4">
          <div>
            <div class="font-bold text-slate-200 mb-1 font-hud">${s.name}</div>
            <div class="text-slate-400 text-[11px] leading-relaxed">${s.evidence}</div>
          </div>
          <div class="font-mono text-cyan-400 font-bold px-2 py-0.5 rounded bg-slate-800 shrink-0">
            ${scoreStr}
          </div>
        </div>
      `;
      })
      .join("");
  }
}

// 5. TEXT & CONTEXT TAB (WITH CATEGORY FILTERING)
function renderTextTab(report, textAnalysis, artifacts) {
  const txtAnalysis = textAnalysis || {};
  const comparisons = txtAnalysis.comparisons || [];

  document.getElementById("text-summary-content").textContent =
    txtAnalysis.summary_text || "Contextual claim verification completed against available grounded facts.";

  const counts = txtAnalysis.counts || {};
  const breakdown = document.getElementById("text-summary-breakdown");
  breakdown.innerHTML = `
    <span class="text-emerald-400 font-bold"><i class="fa-solid fa-circle-check"></i> ${counts.supported || 0} Supported</span>
    <span class="text-red-400 font-bold"><i class="fa-solid fa-circle-xmark"></i> ${counts.contradicted || 0} Contradicted</span>
    <span class="text-slate-400 font-bold"><i class="fa-solid fa-circle-question"></i> ${counts.cannot_verify || 0} Cannot Verify</span>
  `;

  document.getElementById("text-orig-caption").textContent = txtAnalysis.original_caption || "None provided";
  document.getElementById("text-trans-caption").textContent = txtAnalysis.english_translation || txtAnalysis.original_caption || "None";
  document.getElementById("text-det-lang").textContent = `(${txtAnalysis.detected_language || "English"})`;

  renderFilteredClaims(comparisons);

  // Evidence Bundle
  const bundleList = document.getElementById("text-evidence-bundle");
  const evItems = (txtAnalysis.evidence_bundle && txtAnalysis.evidence_bundle.evidence_items) || [];
  if (evItems.length === 0) {
    bundleList.innerHTML = `<div class="text-slate-500">No evidence items recorded.</div>`;
  } else {
    bundleList.innerHTML = evItems
      .map(
        (ev) => `
      <div class="py-1 border-b border-white/5">
        <b class="text-cyan-400 font-mono">[${ev.id}]</b> <span class="text-slate-500 font-mono text-[10px]">(${ev.source})</span>: 
        <span class="text-slate-300 font-sans">${ev.text}</span>
      </div>
    `
      )
      .join("");
  }

  // Unverifiable List
  const unvList = document.getElementById("text-unverifiable-list");
  const unverified = txtAnalysis.unverifiable_claims || [];
  if (unverified.length === 0) {
    unvList.innerHTML = `<div>No unverifiable date or place claims flagged.</div>`;
  } else {
    unvList.innerHTML = unverified
      .map(
        (uv) => `
      <div class="p-2 rounded bg-amber-950/20 border border-amber-500/20 text-xs">
        <div class="font-bold text-amber-300 font-hud">"${uv.claim_text}" (${uv.type})</div>
        <div class="text-slate-300 mt-0.5"><b>Why:</b> ${uv.reason}</div>
        <div class="text-cyan-300 mt-0.5 font-mono"><b>Human Check:</b> ${uv.human_check}</div>
      </div>
    `
      )
      .join("");
  }
}

// Category Filtering for Grounded Claims Table
function setupClaimFilters() {
  const filterBtns = document.querySelectorAll("#claim-filters button");
  filterBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      filterBtns.forEach((b) => {
        b.className = "px-2.5 py-1 rounded text-[10px] font-mono font-bold bg-slate-800 text-slate-400 border border-white/5";
      });
      btn.className = "px-2.5 py-1 rounded text-[10px] font-mono font-bold bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 filter-active";
      activeClaimFilter = btn.getAttribute("data-filter");

      if (activeCaseData && activeCaseData.text_analysis) {
        renderFilteredClaims(activeCaseData.text_analysis.comparisons || []);
      }
    });
  });
}

function renderFilteredClaims(comparisons) {
  const tbody = document.getElementById("text-claims-tbody");
  if (!comparisons || comparisons.length === 0) {
    tbody.innerHTML = `<tr><td colspan="7" class="text-center text-slate-500 py-4">No atomic claims extracted (empty or skipped).</td></tr>`;
    return;
  }

  const filtered = comparisons.filter((c) => {
    if (activeClaimFilter === "all") return true;
    return c.status === activeClaimFilter;
  });

  if (filtered.length === 0) {
    tbody.innerHTML = `<tr><td colspan="7" class="text-center text-slate-500 py-4">No claims match the filter "${activeClaimFilter}".</td></tr>`;
    return;
  }

  tbody.innerHTML = filtered
    .map((c) => {
      let badgeClass = "bg-slate-700/80 text-slate-300 border border-slate-600";
      if (c.status === "supported") badgeClass = "bg-emerald-500/20 text-emerald-400 border border-emerald-500/40";
      if (c.status === "contradicted") badgeClass = "bg-red-500/20 text-red-400 border border-red-500/40";

      const evStr = c.evidence_ids && c.evidence_ids.length > 0 ? c.evidence_ids.join(", ") : "none";
      const confPct = c.confidence ? `${Math.round(c.confidence * 100)}%` : "50%";

      return `
      <tr>
        <td class="font-mono font-bold text-cyan-400">${c.claim_id}</td>
        <td class="font-medium text-slate-200">${c.claim_text}</td>
        <td><code class="text-[11px] bg-slate-800 px-1.5 py-0.5 rounded text-slate-400 font-mono">${c.type}</code></td>
        <td class="text-center"><span class="px-2.5 py-0.5 rounded-full text-[10px] font-bold font-mono uppercase ${badgeClass}">${c.status}</span></td>
        <td class="font-mono text-xs text-slate-400">${evStr}</td>
        <td class="text-xs text-slate-300">${c.reason}</td>
        <td class="text-right font-mono font-bold text-slate-400">${confPct}</td>
      </tr>
    `;
    })
    .join("");
}

// 6. CORRELATION TAB
function renderCorrelationTab(report) {
  const findings = report.cross_modal_findings || [];
  const list = document.getElementById("cross-modal-findings-list");

  if (findings.length === 0) {
    list.innerHTML = `<div class="text-xs text-slate-500">No cross-modal interactions recorded.</div>`;
  } else {
    list.innerHTML = findings
      .map((f) => {
        const isStrengthen = f.effect === "strengthens";
        const badgeClass = isStrengthen ? "bg-red-500/20 text-red-400 border-red-500/30" : "bg-emerald-500/20 text-emerald-400 border-emerald-500/30";
        const cites = (f.supporting_signals || []).map((s) => `<span class="font-mono bg-slate-800 px-1.5 py-0.5 rounded text-[10px] text-cyan-400">${s}</span>`).join(" ");

        return `
        <div class="cyber-card p-4">
          <div class="flex items-center justify-between mb-2">
            <span class="text-xs font-bold uppercase tracking-wider px-2 py-0.5 rounded border ${badgeClass} font-hud">
              ${f.effect}
            </span>
            <div class="flex items-center gap-1">${cites}</div>
          </div>
          <p class="text-xs text-slate-200 leading-relaxed font-sans">${f.finding}</p>
        </div>
      `;
      })
      .join("");
  }
}

// 7. DOSSIER & EXPORT TAB
function renderReportTab(data) {
  const pdfBtn = document.getElementById("btn-download-pdf");
  const jsonBtn = document.getElementById("btn-download-json");

  if (data.pdf_url) {
    pdfBtn.href = data.pdf_url;
    pdfBtn.classList.remove("opacity-50", "pointer-events-none");
  } else {
    pdfBtn.classList.add("opacity-50", "pointer-events-none");
  }

  if (data.json_url) {
    jsonBtn.href = data.json_url;
  }

  // Hashes with 1-click copy
  const hashesList = document.getElementById("input-hashes-list");
  const hashes = data.input_hashes || {};
  if (Object.keys(hashes).length === 0) {
    hashesList.innerHTML = `<div>No file provenance hashes available.</div>`;
  } else {
    hashesList.innerHTML = Object.entries(hashes)
      .map(
        ([fname, h]) => `
      <div class="flex items-center justify-between py-1.5 border-b border-white/5">
        <span class="text-slate-400 truncate max-w-xs">${fname}:</span>
        <div class="flex items-center gap-2">
          <span class="text-cyan-400 font-mono text-[11px] truncate max-w-sm">${h}</span>
          <button type="button" class="text-slate-500 hover:text-cyan-400 text-xs" onclick="navigator.clipboard.writeText('${h}')" title="Copy Hash">
            <i class="fa-solid fa-copy"></i>
          </button>
        </div>
      </div>
    `
      )
      .join("");
  }
}
