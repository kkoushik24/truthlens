---
title: TruthLens Forensics
emoji: 🔍
colorFrom: blue
colorTo: cyan
sdk: streamlit
sdk_version: "1.38.0"
app_file: app.py
pinned: false
---

# TruthLens 🔍

**Multimodal Digital Forensics & Manipulation Detection Workstation**  
*Built for the 24-Hour Digital Trust & Forensics Hackathon*

---

## 📖 Overview

**TruthLens** is an explainable multimodal digital forensics workstation designed to inspect digital media across **images, video, audio, and textual claims**. Instead of acting as an opaque "black-box" classifier, TruthLens extracts atomic forensic signals, correlates indicators across modalities, preserves an immutable cryptographic chain of custody, and produces an exportable investigative dossier.

### ⚖️ Core Forensics Principle: Indicators, Never Verdicts
TruthLens adheres strictly to forensic standards:
- Detection scores are **probabilistic indicators of potential alteration**, never definitive verdicts.
- The system **never outputs binary labels like "REAL" or "FAKE"**.
- Findings are aggregated into standardized risk tiers: `low`, `moderate`, and `elevated`, paired with explicit confidence scores and mandatory forensic caveats.

---

## 🚀 Key Features

| Capability | Module | Description |
| :--- | :--- | :--- |
| **EXIF Metadata Audit** | `image_forensics` | Detects absent tags, camera hardware presence, anomalous future dates, and editing signatures (Photoshop, GIMP, Canva, Midjourney, etc.). |
| **Error Level Analysis (ELA)** | `image_forensics` | Recompresses imagery at fixed JPEG quality ($Q=90$), computes compression divergence, renders a color heatmap overlay, and flags the highest-error anomaly bounding box. |
| **AI Image Detection** | `image_forensics` | Evaluates generative diffusion and synthetic signatures using Hugging Face vision classifiers (`umm-maybe/AI-image-detector`). |
| **Linguistic & Context Claim Audit** | `text_analysis` | Scans captions for sensationalist certainty markers (*"100% real"*, *"undeniable proof"*) and flags chronological conflicts with media EXIF timestamps. |
| **Vision-Language Alignment** | `text_analysis` | Utilizes Google Gemini vision models to cross-reference visual facts against textual claims (setting, objects, climate, events). |
| **Uniform Keyframe Sampling** | `video_forensics` | Efficiently samples up to **12 evenly spaced keyframes** with OpenCV, preventing memory exhaustion on 8 GB RAM laptops. |
| **Temporal Consistency Check** | `video_forensics` | Compares consecutive sampled frames for abrupt shifts in luminance, Laplacian sharpness, and 2D Hue-Saturation color distribution. |
| **Acoustic Heuristics & Spectral Analysis** | `audio_forensics` | Dual-domain amplitude waveforms and log-power spectrograms; sample-rate aware bandwidth cutoff check, noise floor consistency, pitch variation/prosody, and breath/pause regularity heuristics. |
| **Speech-to-Text Caption Check** | `audio_forensics` | Transcribes spoken dialogue with Whisper and cross-checks against captions to detect topic replacement or misattribution. |
| **Cross-Modal Correlation** | `correlation` | Employs deterministic compounding rules and grounded LLM reasoning that strictly cite exact signal IDs without hallucinating evidence. |

---

### ⚠️ Audio Forensics Honesty Disclosures & Current Status

1. **Synthetic-Voice Classifier Disabled**: The pretrained neural audio classifier (`MelodyMachine/Deepfake-audio-detection-V2`) is **disabled** after failing an empirical sanity check (it produced identical static outputs of $fake \approx 0.000017$ across all human and synthetic speech test clips, while calling a pure 440 Hz sine tone 99.8% fake). Model configuration is preserved in `core/config.py` so a validated model can be plugged in later.
2. **Audio Heuristics are Unvalidated on Real Speech**: The acoustic heuristics (spectral cutoff, noise floor flatness, pitch variation, and silence regularity) are **UNVALIDATED ON REAL SPEECH**. Compression, noise reduction, studio recording, phone microphones, and text-to-speech readers can produce identical acoustic characteristics.
3. **8-Clip Evaluation Disclaimer**: The 8-clip evaluation in `samples/audio_eval/` is a preliminary sanity check and is **not a valid statistical accuracy claim** for the heuristics.
4. **Heuristics-Only Constraint**: Audio analysis is currently heuristics-only: its overall indicator is strictly hard-capped at `MODERATE` with a maximum confidence of 50%.
| **Automated Forensic Dossier** | `report` | Generates a structured JSON report and a multi-page PDF dossier featuring visual evidence embeds, indicator status badges, and SHA-256 hashes. |
| **Interactive Streamlit UI** | `app.py` | A clean multi-tab workspace with live progress spinners, `@st.cache_data` instant reruns, and a **Pre-Computed Demo Case Loader** for zero-latency presentations. |

---

## 💻 System Architecture & Constraints

- **Python**: 3.10 / 3.11 / 3.13 compatible.
- **Hardware Profile**: CPU-only execution (no GPU required); runs comfortably on standard 8 GB RAM laptops.
- **Cryptographic Chain of Custody**: Uploaded originals are never altered; they are stored immutably in isolated case folders and verified via SHA-256 hashes.
- **Fail-Safe Architecture**: Every single model inference and file parser is isolated in defensive `try/except` wrappers. If any module fails or network is offline, it emits a valid `Signal` with `score: null` and an explanatory caveat. **The application never crashes.**

---

## 📦 Installation & Setup

### 1. Prerequisites
- Python 3.10+ installed.
- Git installed.
- *(Note: Static FFmpeg is bundled automatically via `imageio-ffmpeg` — no manual system FFmpeg install is required!)*

### 2. Clone Repository & Setup Virtual Environment
```bash
git clone <repo-url> truthlens
cd truthlens

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows PowerShell:
.\venv\Scripts\Activate.ps1
# On macOS / Linux:
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy the template configuration file (or open the ready-made `.env` in the root folder):
```bash
cp .env.example .env
```
Open `.env` in an editor and insert your Groq API key:
```env
# LLM Provider: "groq" (ultra-fast) or "gemini"
LLM_PROVIDER=groq

# Groq API Key (free from https://console.groq.com/keys)
GROQ_API_KEY=gsk_your_groq_api_key_here
GROQ_VISION_MODEL=llama-3.2-11b-vision-preview
GROQ_TEXT_MODEL=llama-3.3-70b-versatile

# Alternative: Google Gemini API Key (optional)
GEMINI_API_KEY=
```
*(Note: If no API key is provided, TruthLens automatically activates its deterministic local heuristic engines, ensuring complete offline functionality without crashing.)*

---

## 🏃 Running TruthLens

Start the Streamlit application:
```bash
streamlit run app.py
```
Open your browser to `http://localhost:8501`.
Open your browser to `http://localhost:8501`.

---

## 🎯 Hackathon Presentation Guide

### 🚀 Using Instant Pre-Computed Demo Cases (Recommended for Judges)
For high-stakes judging where speed and reliability are paramount:
1. Open the left sidebar in the web app.
2. Under **Instant Demo Cases**, select:
   - **Case 1: Spliced Photo with Context Mismatch (Elevated Risk)**: Demonstrates Photoshop EXIF signatures, localized ELA compression divergence, and cross-modal claim contradiction.
   - **Case 2: Authentic Multi-Modal Wildlife Capture (Low/Moderate Risk)**: Demonstrates camera hardware tags, continuous acoustic frequency spectrum, and natural linguistic framing.
3. Click **Load Pre-Computed Demo**.
4. The complete investigation renders instantly with zero wait time, displaying interactive heatmaps, spectrograms, cross-modal findings, and download buttons for JSON and PDF reports.

### 🧪 Uploading Live Files
1. Drag and drop any image, video, audio file, or type a caption in the sidebar.
2. Click **Run Forensic Investigation**.
3. Watch the progress status bar as TruthLens executes the multimodal pipeline and caches results for instant subsequent interactions.

---

## 🔍 How Each Module Works (Plain-English Technical Guide)

### 1. Core (`core/`)
Manages evidence integrity. It assigns a unique case ID (`CASE-YYYYMMDD-XXXX`), calculates SHA-256 checksums by chunk-streaming bytes, and preserves original uploads untouched in `cases/<case_id>/originals/`. All steps are recorded in an audit log.

### 2. Image Forensics (`image_forensics/`)
- **EXIF Audit**: Inspects binary metadata tags. Scans for missing metadata, camera make/model, and editing tool signatures (`Photoshop`, `GIMP`, `Canva`, `Midjourney`).
- **Error Level Analysis (ELA)**: Saves a copy of the image at a known JPEG quality ($Q=90$), computes the per-pixel absolute difference against the original, normalizes the divergence, generates a JET colormap heatmap overlay, and calculates a bounding box around the highest-anomaly region.
- **AI Vision Classifier**: Loads a pretrained vision model with a fast-fail network probe that prevents hangs when offline.

### 3. Text Analysis (`text_analysis/`)
- **Linguistic Integrity**: Checks for manipulative certainty markers (*"undeniable proof"*, *"100% real"*) and detects impossible future calendar years.
- **Metadata Chronology Cross-Check**: Compares claimed years in captions against EXIF capture dates to detect temporal deception.
- **Vision-Language Alignment**: Sends image and caption to Gemini 1.5 Flash (or local heuristics) to evaluate whether visual scene elements (vehicles, foliage, weather) contradict the caption.

### 4. Video Forensics (`video_forensics/`)
- **Keyframe Sampling**: Samples up to 12 evenly spaced keyframes (strict hard cap 15) strictly including the first and last frame, filtering pitch-black/blank frames, and analyzing at most the first 60 seconds with clear UI notes.
- **Per-Frame AI Texture & Face Detection**: Runs configured vision models across sampled frames with face crop detection (Haar Cascade) and aggregates using the higher of top-3 mean vs max frame score, generating an AI timeline chart artifact (`frame_scores_{stem}.png`).
- **Container & Codec Audit**: Audits stream bitrates, container metadata, duration, and codecs (capped at max 0.35 with messaging app compression caveats).
- **Temporal Continuity**: Calculates inter-frame deltas across brightness, Laplacian sharpness, and color histograms to flag jump cuts, with the explicit caveat that modern generative AI produces smooth frames.
- **Physical Plausibility**: Selects candidate frames (first, last, middle, top detector scores) and audits physical realism, anatomy, and surreal lighting via Groq Vision.
- **Audio Extraction**: Demuxes audio tracks to 16 kHz mono WAV using bundled FFmpeg (`imageio-ffmpeg`) for acoustic analysis.

### 5. Audio Forensics (`audio_forensics/`)
- **Spectral Domain Inspection**: Computes log-power spectrograms and waveforms using `scipy.signal.spectrogram`, detecting unnatural brickwall frequency cutoffs ($< 7\text{ kHz}$) typical of legacy speech vocoders.
- **Speech Transcript Alignment**: Transcribes spoken words via `faster-whisper` and compares keywords against written captions to detect topic substitution.

### 6. Cross-Modal Correlation (`correlation/`)
- **Compounding Rules**: Aggregates indicators across modalities (e.g., visual ELA divergence $+$ caption date mismatch $=$ elevated suspicion).
- **Grounded LLM Reasoning**: Calls Gemini with strict prompting: explain using the provided signals only, cite exact supporting `signal_id` strings, state whether each finding strengthens or weakens suspicion, and never hallucinate external facts.
- **OSINT Human Checklist**: Compiles prioritized investigative next steps (Reverse Image Search, requesting camera RAW files, satellite verification).

### 7. Reporting Engine (`report/`)
- **JSON Exporter**: Validates and serializes the complete case data against the Pydantic `ForensicReport` schema.
- **PDF Dossier Exporter**: Uses `fpdf2` to assemble an investigative dossier with color-coded indicator badges, chain-of-custody tables, signals matrix, embedded visual artifacts, and audit history.

---

## ⚠️ Known Limitations & Forensic Caveats

1. **Indicator, Never a Verdict**: An elevated score indicates statistical divergence from baseline camera captures, not definitive proof of malicious intent.
2. **Platform Recompression & Metadata Stripping**: Social media platforms (X, WhatsApp, Instagram) automatically strip EXIF metadata and recompress media, which can produce benign ELA and metadata flags on authentic content.
3. **High-Frequency Texture Sensitivity in ELA**: High-frequency textures (hair, leaves, text, sharp architectural lines) naturally compress with higher error rates than flat skies, regardless of whether tampering occurred.
4. **Cinematic Cuts in Video**: Dramatic camera pans, strobe lighting, or intentional cinematic jump cuts will trigger temporal consistency spikes without indicating digital tampering.
5. **Microphone Bandwidth Limits**: Phone microphones and lossy VoIP codecs often truncate frequencies above 7 kHz, mimicking synthetic speech vocoders.
6. **Domain Shift in AI Classifiers**: Pretrained neural classifiers can exhibit false positives on heavily compressed or filtered photographic imagery. Human verification is always required.

---

## 🧪 Automated Test Suite

TruthLens includes a 39-test automated test suite spanning schema validation, cryptographic hashing, image processing, video sampling, acoustic analysis, correlation rules, report generation, and app integration.

Run all tests:
```bash
python -m pytest tests/ -v
```

---

## 📄 License
TruthLens is developed under the MIT License for educational, hackathon, and open-source investigative use.
