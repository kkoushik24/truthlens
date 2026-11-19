"""TruthLens: Multimodal Digital Forensics Investigation Workstation.

A Streamlit application for analyzing images, video, audio, and claims,
correlating indicators across media types, and producing explainable forensic reports.
"""

import sys
import os
import json
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import streamlit as st
from PIL import Image

# Add workspace root to Python path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from core.case_manager import CaseManager
from core.schemas import ForensicReport, Signal, CrossModalFinding, OverallIndicator
from core.config import settings
from image_forensics.pipeline import analyze_image_pipeline
from video_forensics.pipeline import analyze_video_pipeline
from audio_forensics.pipeline import analyze_audio_pipeline
from text_analysis.pipeline import analyze_text_pipeline
from correlation.engine import correlate_forensic_signals
from report.generator import generate_forensic_report_bundle

# Page configuration
st.set_page_config(
    page_title="TruthLens | Multimodal Digital Forensics",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Cyber Forensics Dark Theme Styling
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    code, pre, .mono {
        font-family: 'JetBrains Mono', monospace !important;
    }

    /* Glassmorphic Cyber Panels */
    .cyber-card {
        background: rgba(17, 24, 39, 0.75);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 16px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
    }
    .cyber-card:hover {
        border-color: rgba(0, 210, 255, 0.3);
        box-shadow: 0 6px 24px rgba(0, 210, 255, 0.12);
    }

    /* Hero Verdict Container */
    .verdict-hero {
        background: linear-gradient(135deg, rgba(17, 24, 39, 0.95) 0%, rgba(15, 23, 42, 0.95) 100%);
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 16px;
        padding: 24px 28px;
        margin-bottom: 24px;
        box-shadow: 0 12px 36px rgba(0, 0, 0, 0.45);
    }

    /* Verdict Badges with Glowing Effects */
    .badge-elevated {
        background: linear-gradient(135deg, #ef4444 0%, #b91c1c 100%);
        color: #ffffff !important;
        padding: 6px 16px;
        border-radius: 30px;
        font-weight: 700;
        font-size: 1.05rem;
        letter-spacing: 0.5px;
        box-shadow: 0 0 20px rgba(239, 68, 68, 0.45);
        display: inline-block;
    }
    .badge-moderate {
        background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
        color: #ffffff !important;
        padding: 6px 16px;
        border-radius: 30px;
        font-weight: 700;
        font-size: 1.05rem;
        letter-spacing: 0.5px;
        box-shadow: 0 0 20px rgba(245, 158, 11, 0.45);
        display: inline-block;
    }
    .badge-low {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        color: #ffffff !important;
        padding: 6px 16px;
        border-radius: 30px;
        font-weight: 700;
        font-size: 1.05rem;
        letter-spacing: 0.5px;
        box-shadow: 0 0 20px rgba(16, 185, 129, 0.45);
        display: inline-block;
    }

    /* Forensic Disclaimer Box */
    .disclaimer-box {
        background: rgba(31, 41, 55, 0.6);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-left: 4px solid #00d2ff;
        border-radius: 8px;
        padding: 12px 16px;
        font-size: 0.88rem;
        color: #9ca3af;
        margin-top: 10px;
    }

    /* Sleek Custom Scrollbar */
    ::-webkit-scrollbar {
        width: 7px;
        height: 7px;
    }
    ::-webkit-scrollbar-track {
        background: #0b0f19;
    }
    ::-webkit-scrollbar-thumb {
        background: #1f2937;
        border-radius: 4px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: #00d2ff;
    }

    /* Buttons Styling */
    button[kind="primary"] {
        background: linear-gradient(135deg, #00d2ff 0%, #0072ff 100%) !important;
        border: none !important;
        color: white !important;
        font-weight: 700 !important;
        letter-spacing: 0.3px;
        border-radius: 8px !important;
        box-shadow: 0 4px 18px rgba(0, 210, 255, 0.35) !important;
        transition: all 0.2s ease !important;
    }
    button[kind="primary"]:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 24px rgba(0, 210, 255, 0.55) !important;
    }

    /* Metric Cards */
    .metric-card {
        background: rgba(17, 24, 39, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-left: 4px solid #00d2ff;
        border-radius: 8px;
        padding: 14px 16px;
        margin-bottom: 12px;
    }

    /* Brand Header */
    .brand-title {
        font-size: 1.5rem;
        font-weight: 800;
        background: linear-gradient(135deg, #00d2ff 0%, #3a7bd5 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: -0.5px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def parse_signal_status(s: dict) -> dict:
    """Parse signal status (ran / failed / skipped), score, and error message for Task 3."""
    evidence = str(s.get("evidence", "")).strip()
    score = s.get("score")

    if evidence.startswith("FAILED:") or ("failed" in evidence.lower() and score is None):
        status = "FAILED"
        err_msg = evidence.replace("FAILED:", "").strip() if evidence.startswith("FAILED:") else evidence
    elif evidence.startswith("SKIPPED:") or ("skipped" in evidence.lower() and score is None):
        status = "SKIPPED"
        err_msg = evidence.replace("SKIPPED:", "").strip() if evidence.startswith("SKIPPED:") else evidence
    elif score is not None:
        status = "RAN"
        err_msg = ""
    else:
        status = "FAILED"
        err_msg = evidence or "No score computed"

    score_str = f"{score:.2f}" if score is not None else "--"
    return {
        "Signal ID": s.get("signal_id"),
        "Signal Name": s.get("name"),
        "Modality": s.get("modality", "").title(),
        "Status": status,
        "Score": score_str,
        "Error / Reason": err_msg,
    }


@st.cache_data(show_spinner=False)
def run_cached_forensic_pipeline(
    input_hashes_key: str,
    image_bytes: Optional[bytes],
    image_name: Optional[str],
    video_bytes: Optional[bytes],
    video_name: Optional[str],
    audio_bytes: Optional[bytes],
    audio_name: Optional[str],
    caption_text: Optional[str],
) -> Dict[str, Any]:
    """Execute complete forensic pipeline across all inputs with deterministic caching."""
    case_mgr = CaseManager()
    all_signals: List[Signal] = []

    # Preserved original paths
    orig_img_path = None
    orig_vid_path = None
    orig_aud_path = None

    if image_bytes and image_name:
        orig_img_path = case_mgr.save_original(image_name, image_bytes)
        img_signals = analyze_image_pipeline(orig_img_path, case_manager=case_mgr)
        all_signals.extend(img_signals)

    if video_bytes and video_name:
        orig_vid_path = case_mgr.save_original(video_name, video_bytes)
        vid_signals, extracted_audio = analyze_video_pipeline(
            orig_vid_path,
            caption=caption_text,
            case_manager=case_mgr,
        )
        all_signals.extend(vid_signals)
        # If no standalone audio was uploaded but video has an audio track, process it
        if extracted_audio and not audio_bytes:
            extracted_aud_signals = analyze_audio_pipeline(
                extracted_audio,
                caption=caption_text,
                case_manager=case_mgr,
            )
            all_signals.extend(extracted_aud_signals)

    if audio_bytes and audio_name:
        orig_aud_path = case_mgr.save_original(audio_name, audio_bytes)
        aud_signals = analyze_audio_pipeline(
            orig_aud_path,
            caption=caption_text,
            case_manager=case_mgr,
        )
        all_signals.extend(aud_signals)

    # 4. Text & Context Analysis (runs if caption provided OR if media uploaded)
    if (caption_text and caption_text.strip()) or orig_img_path or orig_vid_path or orig_aud_path:
        clean_cap = (caption_text or "").strip()
        if clean_cap:
            case_mgr.save_original("caption.txt", clean_cap.encode("utf-8"))
        target_media = orig_img_path or orig_vid_path or orig_aud_path
        target_type = "video" if orig_vid_path else ("audio" if orig_aud_path else "image")
        txt_signals = analyze_text_pipeline(
            caption=clean_cap,
            image_path=orig_img_path,
            media_path=target_media,
            media_type=target_type,
            case_manager=case_mgr,
        )
        all_signals.extend(txt_signals)

    # Cross-Modal Correlation
    input_names = [p.name for p in case_mgr.list_originals()]
    correlation_data = correlate_forensic_signals(
        signals=all_signals,
        inputs=input_names,
        case_manager=case_mgr,
    )

    # Generate Report Bundle (JSON + PDF)
    report_obj, json_path, pdf_path = generate_forensic_report_bundle(
        case_manager=case_mgr,
        signals=all_signals,
        correlation_data=correlation_data,
    )

    # Gather artifact file paths for rendering
    artifacts_map: Dict[str, str] = {}
    if case_mgr.artifacts_dir.exists():
        for art in case_mgr.artifacts_dir.glob("*.*"):
            artifacts_map[art.name] = str(art)

    return {
        "report": report_obj.model_dump(),
        "json_bytes": json_path.read_bytes(),
        "pdf_bytes": pdf_path.read_bytes(),
        "artifacts": artifacts_map,
        "case_id": case_mgr.case_id,
        "input_hashes": case_mgr.input_hashes,
    }


def load_demo_case(case_folder_name: str) -> Dict[str, Any]:
    """Load a pre-computed case from /demo_cases without live processing."""
    case_dir = settings.DEMO_CASES_DIR / case_folder_name
    report_json_path = case_dir / "report.json"
    report_pdf_path = case_dir / "report.pdf"

    if not report_json_path.is_file():
        st.error(f"Demo case not found at: {report_json_path}")
        st.stop()

    with open(report_json_path, "r", encoding="utf-8") as f:
        report_data = json.load(f)

    pdf_bytes = report_pdf_path.read_bytes() if report_pdf_path.is_file() else b""
    json_bytes = report_json_path.read_bytes()

    artifacts_map = {}
    art_dir = case_dir / "artifacts"
    if art_dir.exists():
        for art in art_dir.glob("*.*"):
            artifacts_map[art.name] = str(art)

    return {
        "report": report_data,
        "json_bytes": json_bytes,
        "pdf_bytes": pdf_bytes,
        "artifacts": artifacts_map,
        "case_id": report_data.get("case_id", "DEMO-CASE"),
        "input_hashes": report_data.get("input_hashes", {}),
    }


# ==============================================================================
# SIDEBAR CONTROLS & DEMO LOADER
# ==============================================================================
with st.sidebar:
    st.markdown('<div class="brand-title">TRUTHLENS 🔍</div>', unsafe_allow_html=True)
    st.caption("Multimodal Digital Forensics • Deepfake & Claim Verification")
    st.markdown("---")

    st.subheader("⚡ Quick Demos")
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        if st.button("🚨 Spliced Photo", use_container_width=True):
            st.session_state["active_case"] = load_demo_case("case_01_spliced_photo_claim")
            st.session_state["source_mode"] = "demo"
            st.session_state["demo_name"] = "Case 1: Spliced Photo with Context Mismatch"
            st.rerun()
    with col_d2:
        if st.button("🛡️ Wildlife", use_container_width=True):
            st.session_state["active_case"] = load_demo_case("case_02_authentic_wildlife")
            st.session_state["source_mode"] = "demo"
            st.session_state["demo_name"] = "Case 2: Authentic Multi-Modal Wildlife Capture"
            st.rerun()

    demo_choice = st.selectbox(
        "Or choose demo from list:",
        options=[
            "None (Upload Live Media)",
            "Case 1: Spliced Photo with Context Mismatch (Elevated)",
            "Case 2: Authentic Multi-Modal Wildlife Capture (Low)",
        ],
        index=0,
    )
    if st.button("Load Selected Demo", use_container_width=True):
        if "Case 1" in demo_choice:
            st.session_state["active_case"] = load_demo_case("case_01_spliced_photo_claim")
            st.session_state["source_mode"] = "demo"
            st.session_state["demo_name"] = "Case 1: Spliced Photo with Context Mismatch"
            st.rerun()
        elif "Case 2" in demo_choice:
            st.session_state["active_case"] = load_demo_case("case_02_authentic_wildlife")
            st.session_state["source_mode"] = "demo"
            st.session_state["demo_name"] = "Case 2: Authentic Multi-Modal Wildlife Capture"
            st.rerun()

    st.markdown("---")
    st.subheader("📁 Upload Live Media")

    uploaded_image = st.file_uploader(
        "Upload Image", type=["jpg", "jpeg", "png"], key="uploader_img"
    )
    uploaded_video = st.file_uploader(
        "Upload Video", type=["mp4", "mov", "avi", "mkv"], key="uploader_vid"
    )
    uploaded_audio = st.file_uploader(
        "Upload Audio", type=["wav", "mp3", "m4a", "flac"], key="uploader_aud"
    )
    caption_input = st.text_area(
        "Caption / Contextual Claim:",
        placeholder="e.g. A banana walking on a beach in 2019...",
        height=90,
    )

    # Task 10: Clear previous results whenever input file or caption changes
    current_input_signature = (
        uploaded_image.name if uploaded_image else "",
        uploaded_image.size if uploaded_image else 0,
        uploaded_video.name if uploaded_video else "",
        uploaded_video.size if uploaded_video else 0,
        uploaded_audio.name if uploaded_audio else "",
        uploaded_audio.size if uploaded_audio else 0,
        caption_input.strip(),
    )
    if "last_input_signature" in st.session_state:
        if st.session_state["last_input_signature"] != current_input_signature:
            st.session_state.pop("active_case", None)
            st.session_state.pop("source_mode", None)
    st.session_state["last_input_signature"] = current_input_signature

    run_analysis_clicked = st.button("🔍 Run Forensic Investigation", type="primary", use_container_width=True)

    if st.button("Reset Workspace", use_container_width=True):
        st.cache_data.clear()
        try:
            from text_analysis.caption_checker import clear_caption_cache
            clear_caption_cache()
        except Exception:
            pass
        st.session_state.clear()
        st.rerun()

    st.markdown("---")
    st.markdown(
        "<small style='color: #6b7280;'>TruthLens Core • Python 3.11 Target • CPU Inference • Groq Vision & Text</small>",
        unsafe_allow_html=True,
    )


# ==============================================================================
# LIVE ANALYSIS DISPATCHER
# ==============================================================================
if run_analysis_clicked:
    has_inputs = any([uploaded_image, uploaded_video, uploaded_audio, caption_input.strip()])
    if not has_inputs:
        st.warning("Please upload at least one media asset or provide a contextual caption.")
    else:
        # Create deterministic hash key from media and caption hashes (Task 6)
        hash_seed = ""
        img_b = uploaded_image.getvalue() if uploaded_image else None
        vid_b = uploaded_video.getvalue() if uploaded_video else None
        aud_b = uploaded_audio.getvalue() if uploaded_audio else None

        if img_b:
            hash_seed += f"img_{hashlib.sha256(img_b).hexdigest()[:16]}_"
        if vid_b:
            hash_seed += f"vid_{hashlib.sha256(vid_b).hexdigest()[:16]}_"
        if aud_b:
            hash_seed += f"aud_{hashlib.sha256(aud_b).hexdigest()[:16]}_"
        hash_seed += f"cap_{hashlib.sha256(caption_input.strip().encode('utf-8')).hexdigest()[:16]}"

        with st.status("Executing Multimodal Forensics...", expanded=True) as status:
            if uploaded_image:
                st.write("🔬 Inspecting Image EXIF, running ELA heatmap, and evaluating AI artifacts...")
            if uploaded_video:
                st.write("🎥 Sampling keyframes, auditing container metadata, and analyzing temporal jumps...")
            if uploaded_audio or uploaded_video:
                st.write("🔊 Computing acoustic spectrogram, detecting synthetic vocoders, and transcribing dialogue...")
            st.write("📝 Evaluating visual plausibility and cross-checking visual-textual claims...")
            st.write("🧩 Compounding cross-modal indicators and compiling cryptographic report...")

            result_case = run_cached_forensic_pipeline(
                input_hashes_key=hash_seed,
                image_bytes=img_b,
                image_name=uploaded_image.name if uploaded_image else None,
                video_bytes=vid_b,
                video_name=uploaded_video.name if uploaded_video else None,
                audio_bytes=aud_b,
                audio_name=uploaded_audio.name if uploaded_audio else None,
                caption_text=caption_input,
            )
            status.update(label="Forensic Investigation Complete!", state="complete", expanded=False)

        st.session_state["active_case"] = result_case
        st.session_state["source_mode"] = "live"


# ==============================================================================
# MAIN DASHBOARD DISPLAY
# ==============================================================================
active_case = st.session_state.get("active_case")
source_mode = st.session_state.get("source_mode", "live")
has_live_uploads = any([uploaded_image, uploaded_video, uploaded_audio, caption_input.strip()])

# Task 10: Disambiguate if demo case is loaded while files are uploaded
if active_case and source_mode == "demo" and has_live_uploads:
    st.warning("⚠️ **Notice**: A pre-computed Demo Case is currently displayed, but you also have live files uploaded in the sidebar.")
    col_sel1, col_sel2 = st.columns([1, 3])
    with col_sel1:
        chosen_view = st.radio("Select which investigation to display:", ["Demo Case", "Live Uploads"], horizontal=True)
        if chosen_view == "Live Uploads":
            st.session_state.pop("active_case", None)
            st.session_state["source_mode"] = "live"
            st.rerun()

if not active_case:
    # Cyber Forensics Hero Welcome Dashboard
    st.markdown(
        """
        <div class="verdict-hero" style="text-align: center; padding: 45px 24px; margin-top: 10px;">
            <div style="font-size: 3.2rem; margin-bottom: 8px;">🔍</div>
            <h1 style="font-size: 2.3rem; font-weight: 800; margin-bottom: 12px; background: linear-gradient(135deg, #00d2ff 0%, #3a7bd5 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; letter-spacing: -0.5px;">
                TruthLens Forensic Investigation Workstation
            </h1>
            <p style="color: #9ca3af; font-size: 1.05rem; max-width: 780px; margin: 0 auto 24px auto; line-height: 1.6;">
                Autonomous multimodal digital forensics platform for detecting media manipulation, synthetic audio/video, and contextual claim mismatches using deterministic physics and acoustic signal processing.
            </p>
            <div style="display: flex; gap: 10px; justify-content: center; flex-wrap: wrap; margin-bottom: 10px;">
                <span style="background: rgba(0, 210, 255, 0.1); color: #00d2ff; border: 1px solid rgba(0, 210, 255, 0.3); padding: 6px 14px; border-radius: 20px; font-size: 0.82rem; font-weight: 600;">🖼️ Image ELA & EXIF</span>
                <span style="background: rgba(0, 210, 255, 0.1); color: #00d2ff; border: 1px solid rgba(0, 210, 255, 0.3); padding: 6px 14px; border-radius: 20px; font-size: 0.82rem; font-weight: 600;">🎥 Video Keyframe Forensics</span>
                <span style="background: rgba(0, 210, 255, 0.1); color: #00d2ff; border: 1px solid rgba(0, 210, 255, 0.3); padding: 6px 14px; border-radius: 20px; font-size: 0.82rem; font-weight: 600;">🔊 Dual-Domain Acoustic Spectrograms</span>
                <span style="background: rgba(0, 210, 255, 0.1); color: #00d2ff; border: 1px solid rgba(0, 210, 255, 0.3); padding: 6px 14px; border-radius: 20px; font-size: 0.82rem; font-weight: 600;">📝 Grounded Claim Verification</span>
                <span style="background: rgba(0, 210, 255, 0.1); color: #00d2ff; border: 1px solid rgba(0, 210, 255, 0.3); padding: 6px 14px; border-radius: 20px; font-size: 0.82rem; font-weight: 600;">🧩 Cross-Modal Correlation</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("### ⚡ Quick-Launch Pre-Computed Investigations")
    col_w1, col_w2 = st.columns(2)
    with col_w1:
        st.markdown(
            """
            <div class="cyber-card">
                <div style="font-size: 1.15rem; font-weight: 700; color: #ef4444; margin-bottom: 6px;">
                    🚨 Case 1: Spliced Photo with Context Contradiction
                </div>
                <p style="color: #9ca3af; font-size: 0.9rem; line-height: 1.5; margin-bottom: 14px;">
                    Evaluates JPEG compression divergence via ELA heatmap, Photoshop metadata tags, and out-of-context caption contradiction.
                </p>
                <div style="font-size: 0.85rem; color: #6b7280; margin-bottom: 12px;">
                    <b>Modality:</b> Image + Text Claim • <b>Risk Tier:</b> <span style="color: #ef4444; font-weight: bold;">ELEVATED</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("🚀 Launch Spliced Photo Demo", key="btn_w_case1", use_container_width=True):
            st.session_state["active_case"] = load_demo_case("case_01_spliced_photo_claim")
            st.session_state["source_mode"] = "demo"
            st.session_state["demo_name"] = "Case 1: Spliced Photo with Context Mismatch"
            st.rerun()

    with col_w2:
        st.markdown(
            """
            <div class="cyber-card">
                <div style="font-size: 1.15rem; font-weight: 700; color: #10b981; margin-bottom: 6px;">
                    🛡️ Case 2: Authentic Multi-Modal Wildlife Capture
                </div>
                <p style="color: #9ca3af; font-size: 0.9rem; line-height: 1.5; margin-bottom: 14px;">
                    Evaluates genuine Canon DSLR hardware signatures, uniform compression baseline, and verified descriptive caption alignment.
                </p>
                <div style="font-size: 0.85rem; color: #6b7280; margin-bottom: 12px;">
                    <b>Modality:</b> Image + Text Claim • <b>Risk Tier:</b> <span style="color: #10b981; font-weight: bold;">LOW</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("🚀 Launch Authentic Wildlife Demo", key="btn_w_case2", use_container_width=True):
            st.session_state["active_case"] = load_demo_case("case_02_authentic_wildlife")
            st.session_state["source_mode"] = "demo"
            st.session_state["demo_name"] = "Case 2: Authentic Multi-Modal Wildlife Capture"
            st.rerun()

    st.markdown("---")
    st.markdown(
        """
        <div style="text-align: center; color: #6b7280; font-size: 0.85rem; padding: 10px 0;">
            TruthLens Forensic Workstation • Built for Defense, Forensics & OSINT Verification • Strictly Avoids Binary 'Real' or 'Fake' Verdicts
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    report = active_case["report"]
    artifacts = active_case.get("artifacts", {})
    indicator = report.get("overall_indicator", {})
    indicator_level = indicator.get("level", "low").upper()
    confidence = indicator.get("confidence", 0.0)

    # Task 10: Clear Mode Label at top
    mode_badge = "DEMO CASE" if source_mode == "demo" else "LIVE UPLOAD"
    mode_color = "#00d2ff" if source_mode == "demo" else "#10b981"

    col_h1, col_h2 = st.columns([3, 1])
    with col_h1:
        st.markdown(
            f"""
            <div class="cyber-card" style="margin-bottom: 0px; padding: 18px 22px;">
                <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 6px;">
                    <span style="font-size: 1.3rem; font-weight: 800; color: #f3f4f6;">Case File:</span>
                    <span style="font-family: 'JetBrains Mono', monospace; font-size: 1.25rem; color: #00d2ff; font-weight: 700;">{report.get('case_id')}</span>
                    <span style="background-color: {mode_color}; color: #0b0f19; padding: 3px 10px; border-radius: 12px; font-size: 0.75rem; font-weight: 800; letter-spacing: 0.5px;">{mode_badge}</span>
                </div>
                <div class="disclaimer-box" style="margin-top: 6px;">
                    ⚖️ <b>FORENSIC NOTICE:</b> Detection scores represent risk probability tiers, <b>NEVER</b> binary verdicts. TruthLens strictly avoids binary labels like "REAL" or "FAKE".
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col_h2:
        badge_class = f"badge-{indicator_level.lower()}"
        bar_color = "#ef4444" if indicator_level == "ELEVATED" else ("#f59e0b" if indicator_level == "MODERATE" else "#10b981")
        st.markdown(
            f"""
            <div class="cyber-card" style="text-align: center; margin-bottom: 0px; padding: 18px 20px;">
                <div style="font-size: 0.78rem; font-weight: 700; color: #9ca3af; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;">Overall Forensic Indicator</div>
                <span class="{badge_class}">{indicator_level}</span>
                <div style="margin-top: 10px; font-size: 0.85rem; color: #9ca3af;">
                    Confidence Assessment: <b style="color: #f3f4f6;">{confidence:.0%}</b>
                </div>
                <div style="background: rgba(255,255,255,0.1); border-radius: 4px; height: 6px; width: 100%; margin-top: 6px; overflow: hidden;">
                    <div style="background: {bar_color}; width: {confidence * 100:.0f}%; height: 100%; border-radius: 4px;"></div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Multimodal Tabs
    tab_overview, tab_image, tab_video, tab_audio, tab_text, tab_corr, tab_report = st.tabs([
        "📋 Overview",
        "🖼️ Image Forensics",
        "🎥 Video Forensics",
        "🔊 Audio Forensics",
        "📝 Text & Context",
        "🧩 Cross-Modal Correlation",
        "📥 Report & Export",
    ])

    # --------------------------------------------------------------------------
    # TAB 1: OVERVIEW
    # --------------------------------------------------------------------------
    with tab_overview:
        # Task 2: Red warning banner if any model is not downloaded
        all_signals_raw = report.get("signals", [])
        model_missing_sigs = [s for s in all_signals_raw if "Model not downloaded" in str(s.get("evidence", ""))]
        if model_missing_sigs:
            st.error("🚨 **Model not downloaded.** Run: `python setup_models.py` in your terminal to cache required weights.")

        # Task 7: Show limited signals warnings if major signals did not run
        for lim in report.get("limitations", []):
            if "Result based on limited signals" in lim:
                st.warning(f"⚠️ {lim}")

        # Task 6: Compression warning banner if messaging-app compression detected
        compression_warn = any("Compression may hide AI artifacts" in str(w) for w in report.get("overall_indicator", {}).get("warnings", []))
        if not compression_warn:
            vid_sigs = [s for s in all_signals_raw if s.get("modality") == "video"]
            vid_meta = next((s for s in vid_sigs if s.get("signal_id") == "vid_meta_001"), None)
            if vid_meta and ("stripped" in str(vid_meta.get("evidence", "")).lower() or "whatsapp" in str(vid_meta.get("source_file", "")).lower()):
                compression_warn = True
        if compression_warn:
            st.warning("⚠️ **Compression may hide AI artifacts. A low result here is not reliable.**")

        # Task 9 & Task E: OVERVIEW SUMMARY BOX (10-second comprehension for judges)
        st.markdown("#### 🔍 Executive Forensic Summary")
        badge_color = "#dc3545" if indicator_level == "ELEVATED" else ("#fd7e14" if indicator_level == "MODERATE" else "#28a745")

        # Extract top reasons ranked by score, strictly ONLY signals >= 0.35 (Task E & Task 5)
        scored_signals = [s for s in all_signals_raw if s.get("score") is not None and s.get("score") >= 0.35]
        scored_signals.sort(key=lambda s: s.get("score", 0.0), reverse=True)

        top_reasons_list = []
        for s in scored_signals[:3]:
            first_sentence = s.get("evidence", "").split(". ")[0] + "."
            top_reasons_list.append(f"<b>{s.get('name')}:</b> {first_sentence} (Score: <code>{s.get('score'):.2f}</code>)")

        if not top_reasons_list:
            reasons_html = "<li style='margin-bottom: 4px; color: #6c757d;'>No forensic tests found significant tampering indicators (all test scores below 0.35 threshold).</li>"
        else:
            reasons_html = "".join([f"<li style='margin-bottom: 4px;'>{r}</li>" for r in top_reasons_list])

        if any(s.get("modality") == "video" for s in all_signals_raw):
            default_checks = [
                "Perform reverse video search on Google Lens / Yandex.",
                "Request original uncompressed recording directly from the source.",
                "Check posting account metadata and origin context.",
            ]
        else:
            default_checks = [
                "Perform a reverse image search on Google Images and TinEye.",
                "Inspect raw camera original metadata or request uncompressed source file.",
                "Cross-verify claimed location and date against trusted news reporting.",
            ]
        human_checks = report.get("recommended_human_checks", default_checks)
        checks_html = "".join([f"<li style='margin-bottom: 2px;'>{c}</li>" for c in human_checks[:4]])

        st.markdown(
            f"""
            <div style="border: 2px solid {badge_color}; background-color: #ffffff; border-radius: 8px; padding: 18px; margin-bottom: 22px;">
                <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #e9ecef; padding-bottom: 10px; margin-bottom: 12px;">
                    <div>
                        <span style="font-size: 1.05rem; color: #495057; font-weight: 600;">Overall Tampering Indicator:</span>
                        <span style="background-color: {badge_color}; color: white; padding: 4px 12px; border-radius: 5px; font-size: 1.15rem; font-weight: bold; margin-left: 8px;">
                            {indicator_level}
                        </span>
                    </div>
                    <div style="font-size: 1rem; color: #495057;">
                        Assessed Confidence: <b style="color: #212529;">{confidence:.0%}</b>
                    </div>
                </div>
                <div style="margin-bottom: 12px;">
                    <div style="font-weight: 600; color: #212529; margin-bottom: 6px;">Top Reasons (Plain English):</div>
                    <ul style="margin: 0; padding-left: 20px; color: #343a40; font-size: 0.95rem;">
                        {reasons_html}
                    </ul>
                </div>
                <div style="background-color: #f8f9fa; border-radius: 6px; padding: 10px 14px; border: 1px solid #e9ecef;">
                    <div style="font-weight: 600; color: #495057; font-size: 0.88rem; margin-bottom: 4px;">Recommended Next Steps (Human OSINT):</div>
                    <ul style="margin: 0; padding-left: 20px; color: #495057; font-size: 0.88rem;">
                        {checks_html}
                    </ul>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Task E: Collapsed section for "Checks that found nothing unusual" (including skipped with reasons)
        with st.expander("✅ Checks that found nothing unusual (and skipped tests)", expanded=False):
            unremarkable_signals = [s for s in all_signals_raw if s.get("score") is None or s.get("score") < 0.35]
            if unremarkable_signals:
                for s in unremarkable_signals:
                    status_lbl = "SKIPPED" if "SKIPPED" in str(s.get("evidence", "")) else ("FAILED" if "FAILED" in str(s.get("evidence", "")) else "NORMAL")
                    score_str = f"Score: {s.get('score'):.2f}" if s.get("score") is not None else status_lbl
                    st.markdown(f"**{s.get('name')}** (`{score_str}`)")
                    st.caption(f"_{s.get('evidence')}_")
            else:
                st.write("All evaluated signals flagged unusual characteristics.")

        # Task 3: SIGNAL STATUS TABLE (All signals: ran / failed / skipped)
        st.markdown("#### 📋 Signal Status & Health Table")
        st.caption("Every registered forensic test with explicit operational status and error diagnostic:")
        status_table = [parse_signal_status(s) for s in all_signals_raw]
        st.dataframe(status_table, use_container_width=True)

        col_ov1, col_ov2 = st.columns(2)
        with col_ov1:
            st.markdown("#### Cryptographic Chain of Custody")
            st.caption("Immutable original assets and SHA-256 integrity checksums:")
            hashes = report.get("input_hashes", {})
            if hashes:
                table_data = [{"File": fn, "SHA-256 Checksum": h} for fn, h in hashes.items()]
                st.dataframe(table_data, use_container_width=True)
            else:
                st.write("No files registered.")

        with col_ov2:
            st.markdown("#### Signal Distribution")
            elevated_cnt = sum(1 for s in all_signals_raw if s.get("score") and s.get("score") >= 0.60)
            moderate_cnt = sum(1 for s in all_signals_raw if s.get("score") and 0.35 <= s.get("score") < 0.60)
            low_cnt = sum(1 for s in all_signals_raw if s.get("score") and s.get("score") < 0.35)
            null_cnt = sum(1 for s in all_signals_raw if s.get("score") is None)

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Elevated", elevated_cnt)
            c2.metric("Moderate", moderate_cnt)
            c3.metric("Low", low_cnt)
            c4.metric("Inconclusive/Skipped", null_cnt)

    # --------------------------------------------------------------------------
    # TAB 2: IMAGE FORENSICS
    # --------------------------------------------------------------------------
    with tab_image:
        st.subheader("Image Analysis: ELA & Metadata Audit")
        img_signals = [s for s in report.get("signals", []) if s.get("modality") == "image"]

        if not img_signals:
            st.info("No image media submitted for this case.")
        else:
            # Check for heatmap artifact
            heatmap_path = None
            for name, path in artifacts.items():
                if "ela_heatmap" in name:
                    heatmap_path = path
                    break

            if heatmap_path and Path(heatmap_path).is_file():
                col_i1, col_i2 = st.columns(2)
                with col_i1:
                    st.markdown("##### Error Level Analysis (Heatmap & Bounding Box)")
                    st.image(str(heatmap_path), caption="ELA Heatmap Overlay (Peak anomaly flagged in bounding box)", use_container_width=True)
                with col_i2:
                    st.markdown("##### ELA Diagnostic Insights")
                    ela_sig = next((s for s in img_signals if s.get("signal_id") == "img_ela_001"), None)
                    if ela_sig:
                        st.markdown(f"**Evidence:** {ela_sig.get('evidence')}")
                        st.caption(f"**Limitation:** {ela_sig.get('limitation')}")
                        with st.expander("Technical details"):
                            st.write(f"Raw Score: `{ela_sig.get('score')}`")
                            st.write(f"Flagged Region (BBox): `{ela_sig.get('location')}`")
                            st.write("Algorithm: Fixed JPEG recompression divergence at Q=90.")

            # Plain-English Signal Display (Task 8)
            st.markdown("##### Image Forensic Signals")
            for s in img_signals:
                score_str = f"{s.get('score'):.2f}" if s.get("score") is not None else "--"
                st.markdown(f"**{s.get('name')}** (Score: `{score_str}`)")
                st.markdown(f"_{s.get('evidence')}_")
                with st.expander("Technical details"):
                    st.write(f"Signal ID: `{s.get('signal_id')}`")
                    st.write(f"Source Asset: `{s.get('source_file')}`")
                    st.write(f"Limitation: {s.get('limitation')}")
                st.markdown("---")

    # --------------------------------------------------------------------------
    # TAB 3: VIDEO FORENSICS
    # --------------------------------------------------------------------------
    with tab_video:
        st.subheader("Video Analysis: Keyframe Sampling & Temporal Consistency")
        vid_signals = [s for s in report.get("signals", []) if s.get("modality") == "video"]

        if not vid_signals:
            st.info("No video media submitted for this case.")
        else:
            # Signal Status Table for Video Forensics (Task 1)
            st.markdown("#### 📋 Video Signal Status Table")
            st.caption("Every video forensic check with operational health and status:")
            vid_status_table = [parse_signal_status(s) for s in vid_signals]
            st.dataframe(vid_status_table, use_container_width=True)

            # Task 6: Keyframe AI Detector Timeline Chart
            chart_path = None
            for name, p in artifacts.items():
                if "frame_scores" in name and name.endswith(".png"):
                    chart_path = p
                    break
            if chart_path and Path(chart_path).is_file():
                st.markdown("##### 📈 Keyframe AI Probability Timeline")
                st.image(str(chart_path), caption="AI Detector Suspicion Score Per Sampled Keyframe", use_container_width=True)

            # Task 6: Top 3 Flagged Keyframes Gallery
            json_scores_path = None
            for name, p in artifacts.items():
                if "frame_scores" in name and name.endswith(".json"):
                    json_scores_path = p
                    break

            if json_scores_path and Path(json_scores_path).is_file():
                try:
                    with open(json_scores_path, "r", encoding="utf-8") as jf:
                        frecords = json.load(jf)
                    top_flagged = sorted(frecords, key=lambda r: r.get("score", 0.0), reverse=True)[:3]
                    if top_flagged and any(r.get("score", 0.0) >= 0.35 for r in top_flagged):
                        st.markdown("##### 🎯 Top Flagged Keyframes")
                        st.caption("Keyframes exhibiting the highest generative AI synthesis probability:")
                        fcols = st.columns(len(top_flagged))
                        for fi, fr in enumerate(top_flagged):
                            fp = fr.get("path")
                            if fp and Path(fp).is_file():
                                face_tag = " (Face Detected)" if fr.get("is_face") else ""
                                fcols[fi].image(
                                    str(fp),
                                    caption=f"Frame #{fr.get('index')} ({fr.get('timestamp', 0):.2f}s){face_tag}\nAI Score: {fr.get('score', 0):.0%}",
                                    use_container_width=True,
                                )
                except Exception:
                    pass

            # Sampled uniform keyframes gallery (collapsed)
            frame_artifacts = [p for name, p in artifacts.items() if "frame_" in name and Path(p).is_file() and not name.startswith("frame_scores")]
            if frame_artifacts:
                with st.expander(f"🎞️ View All {len(frame_artifacts)} Sampled Keyframes", expanded=False):
                    fcols_all = st.columns(min(len(frame_artifacts), 6))
                    for i, fp in enumerate(frame_artifacts[:12]):
                        fcols_all[i % 6].image(str(fp), caption=f"Frame #{i+1}", use_container_width=True)

            # Task 6: Plain-English Video Signals ("What we saw / Why it matters / How sure we are")
            st.markdown("##### Video Forensic Signals")
            for s in vid_signals:
                score_str = f"{s.get('score'):.2f}" if s.get("score") is not None else "--"
                st.markdown(f"**{s.get('name')}** (Score: `{score_str}`)")

                ev_str = str(s.get("evidence", ""))
                if "SKIPPED" in ev_str:
                    sureness = "Test was skipped: " + ev_str.split("SKIPPED:")[-1].strip()
                elif "FAILED" in ev_str:
                    sureness = "Test failed: " + ev_str.split("FAILED:")[-1].strip()
                elif s.get("score") is not None:
                    if s.get("score") >= 0.60:
                        sureness = f"High suspicion (score {score_str}). Strongly indicates synthetic generation artifacts."
                    elif s.get("score") >= 0.35:
                        sureness = f"Moderate suspicion (score {score_str}). Indicates potential synthesis or compression anomalies."
                    else:
                        sureness = f"Low suspicion (score {score_str}). No indicators found by this check."
                else:
                    sureness = "Inconclusive / not evaluated."

                sig_id = s.get("signal_id", "")
                if "ai" in sig_id:
                    why_matters = "Deep neural vision models scan individual video keyframes for micro-textures, diffusion noise, and GAN synthesis patterns."
                elif "plaus" in sig_id:
                    why_matters = "Vision-language models audit physical realism across frames to detect anatomy distortions, floating elements, or impossible physical motion."
                elif "temp" in sig_id:
                    why_matters = "Frame-to-frame continuity checks inspect color divergence and edge transitions; modern generative AI produces smooth transitions, so a clean result here proves nothing."
                elif "meta" in sig_id:
                    why_matters = "Container metadata reveals encoding tools and compression signatures; re-compressed messaging app videos frequently strip this data."
                elif "cap" in sig_id:
                    why_matters = "Cross-checks video scene content against user captions to flag out-of-context video misattribution."
                elif "ela" in sig_id:
                    why_matters = "Error Level Analysis flags divergent compression levels across keyframe macroblocks, though lossy container re-encoding makes this weak evidence."
                else:
                    why_matters = "Audits video parameters and frame integrity."

                st.markdown(f"- **What we saw:** _{s.get('evidence')}_")
                st.markdown(f"- **Why it matters:** {why_matters}")
                st.markdown(f"- **How sure we are:** {sureness}")

                with st.expander("Technical details"):
                    st.write(f"Signal ID: `{s.get('signal_id')}`")
                    st.write(f"Anomaly Location: `{s.get('location')}`")
                    st.write(f"Limitation: {s.get('limitation')}")
                st.markdown("---")

    # --------------------------------------------------------------------------
    # TAB 4: AUDIO FORENSICS
    # --------------------------------------------------------------------------
    with tab_audio:
        st.subheader("Audio Analysis: Acoustic Spectrum & Voice Synthesis")
        aud_signals = [s for s in report.get("signals", []) if s.get("modality") == "audio"]

        if not aud_signals:
            st.info("No audio media submitted for this case.")
        else:
            # Signal Status Table for Audio Forensics (Task 1)
            st.markdown("#### 📋 Audio Signal Status Table")
            st.caption("Every audio forensic check with operational health and status:")
            aud_status_table = [parse_signal_status(s) for s in aud_signals]
            st.dataframe(aud_status_table, use_container_width=True)

            spec_path = None
            for name, path in artifacts.items():
                if "spectrogram" in name:
                    spec_path = path
                    break

            if spec_path and Path(spec_path).is_file():
                st.image(str(spec_path), caption="Log-Power Spectrogram & Amplitude Waveform", use_container_width=True)

            # Task D: Transcript in collapsed expander, never in Top Reasons
            trans_sig = next((s for s in aud_signals if s.get("signal_id") == "aud_trans_001"), None)
            with st.expander("📝 Speech Transcript (Collapsed)", expanded=False):
                if trans_sig:
                    ev = str(trans_sig.get("evidence", ""))
                    if "Transcript:" in ev:
                        t_part = ev.split("Transcript:")[1].strip().strip('"')
                        st.markdown(f"**Extracted Dialogue:**\n\n> \"{t_part}\"")
                    elif "transcribed:" in ev:
                        t_part = ev.split("transcribed:")[1].strip().strip('"')
                        st.markdown(f"**Extracted Dialogue:**\n\n> \"{t_part}\"")
                    elif "SKIPPED" in ev:
                        st.info(f"**Status:** {ev}")
                    elif "FAILED" in ev:
                        st.warning(f"**Status:** {ev}")
                    else:
                        st.write(ev)
                else:
                    st.info("SKIPPED: Speech transcription did not run.")

            # Task E: Plain-English Signal Display ("What we saw / Why it matters / How sure we are")
            st.markdown("##### Audio Forensic Signals")
            for s in aud_signals:
                score_str = f"{s.get('score'):.2f}" if s.get("score") is not None else "--"
                st.markdown(f"**{s.get('name')}** (Score: `{score_str}`)")

                # Plain-English "How sure we are"
                ev_str = str(s.get("evidence", ""))
                if "SKIPPED" in ev_str:
                    sureness = "Test was skipped: " + ev_str.split("SKIPPED:")[-1].strip()
                elif "FAILED" in ev_str:
                    sureness = "Test failed: " + ev_str.split("FAILED:")[-1].strip()
                elif s.get("score") is not None:
                    if s.get("score") >= 0.35:
                        sureness = f"Moderate suspicion (score {s.get('score'):.2f}). Weak indicator, unvalidated on real speech."
                    else:
                        sureness = f"Low suspicion (score {s.get('score'):.2f}). No indicators found by this check."
                else:
                    sureness = "Inconclusive / not evaluated."

                # Why it matters context
                sig_id = s.get("signal_id", "")
                if "spec" in sig_id:
                    why_matters = "Acoustic roll-off checks detect sharp artificial bandwidth cutoffs from older vocoders or lossy compression."
                elif "noise" in sig_id:
                    why_matters = "Synthesized speech often contains unnaturally flat background noise floors or abrupt ambient shifts."
                elif "prosody" in sig_id:
                    why_matters = "Human speech has dynamic pitch modulation; text-to-speech generators often exhibit robotic or constrained pitch."
                elif "silence" in sig_id:
                    why_matters = "Artificial voice generators often segment sentences with unnaturally uniform pause durations without breath pauses."
                elif "voice" in sig_id:
                    why_matters = "Deep neural classifiers evaluate raw audio waveforms for vocoder generation artifacts."
                elif "trans" in sig_id:
                    why_matters = "Cross-references spoken dialogue against external claims to detect out-of-context misattribution."
                else:
                    why_matters = "Audits container metadata and audio parameters for tampering."

                st.markdown(f"- **What we saw:** _{s.get('evidence')}_")
                st.markdown(f"- **Why it matters:** {why_matters}")
                st.markdown(f"- **How sure we are:** {sureness}")

                with st.expander("Technical details"):
                    st.write(f"Signal ID: `{s.get('signal_id')}`")
                    st.write(f"Source Asset: `{s.get('source_file')}`")
                    st.write(f"Location: `{s.get('location')}`")
                    st.write(f"Limitation: {s.get('limitation')}")
                st.markdown("---")

    # --------------------------------------------------------------------------
    # TAB 5: TEXT & CONTEXT
    # --------------------------------------------------------------------------
    with tab_text:
        st.subheader("📝 Text & Context Forensic Analysis")

        # 1. Check for structured claim analysis artifact
        analysis_data = None
        analysis_path = artifacts.get("text_context_analysis.json")
        if analysis_path and Path(analysis_path).is_file():
            try:
                analysis_data = json.loads(Path(analysis_path).read_text(encoding="utf-8"))
            except Exception:
                analysis_data = None

        txt_signals = [s for s in report.get("signals", []) if s.get("modality") == "text"]
        match_sig = next((s for s in txt_signals if s.get("signal_id") == "txt_vis_match_001"), None)
        is_caption_skipped = (
            (match_sig and "SKIPPED" in str(match_sig.get("evidence", "")))
            or (analysis_data and analysis_data.get("status") == "SKIPPED: no caption provided")
        )

        if is_caption_skipped:
            st.info("ℹ️ **SKIPPED: no caption provided.** No caption or contextual claims were provided for this case. Caption analysis was excluded from overall scoring.")
        elif analysis_data and analysis_data.get("status", "").startswith("FAILED:"):
            st.error(f"🚨 **{analysis_data.get('status')}**")
            st.caption("Caption analysis encountered an unrecoverable failure and could not extract or verify claims.")
        elif analysis_data and analysis_data.get("comparisons"):
            counts = analysis_data.get("counts", {})
            s_cnt = counts.get("supported", 0)
            c_cnt = counts.get("contradicted", 0)
            u_cnt = counts.get("cannot_verify", 0)
            tot_cnt = counts.get("total", len(analysis_data.get("comparisons", [])))
            summary_txt = analysis_data.get("summary_text", "")

            # A. Plain-English Summary Box (Top of Tab)
            summary_markup = (
                '<div style="background-color: #f8f9fa; border-left: 5px solid #007bff; border-radius: 6px; padding: 14px 18px; margin-bottom: 20px;">'
                '<div style="font-weight: 600; color: #212529; font-size: 1.05rem; margin-bottom: 6px;">'
                '🔍 Plain-English Context Summary'
                '</div>'
                f'<div style="color: #343a40; font-size: 0.95rem; line-height: 1.5;">{summary_txt}</div>'
                '<div style="margin-top: 10px; font-size: 0.88rem; color: #6c757d;">'
                '<b>Findings Breakdown:</b> '
                f'<span style="color: #28a745; font-weight: bold; margin-left: 4px;">{s_cnt} Supported</span> • '
                f'<span style="color: #dc3545; font-weight: bold; margin-left: 4px;">{c_cnt} Contradicted</span> • '
                f'<span style="color: #6c757d; font-weight: bold; margin-left: 4px;">{u_cnt} Cannot Verify</span> '
                f'(Total: {tot_cnt} atomic claims)'
                '</div>'
                '</div>'
            )
            st.markdown(summary_markup, unsafe_allow_html=True)

            # Vision failure or rate limit notice
            bundle = analysis_data.get("evidence_bundle", {})
            bundle_status = str(bundle.get("status", ""))
            ev_list = bundle.get("evidence_items", [])
            has_vis_failure = bundle_status.startswith("FAILED:") or any("Visual observation unavailable" in str(ev.get("text", "")) for ev in ev_list)
            if has_vis_failure:
                st.warning(
                    "⚠️ **Visual Observation Notice**: The vision model could not examine the visual media (e.g. Groq Vision API rate limit or error). "
                    "Claims were safely evaluated against available container/EXIF metadata only, which is why visual claims are marked **cannot_verify**."
                )

            # B. Caption Display
            orig_caption = analysis_data.get("original_caption", "")
            trans_caption = analysis_data.get("english_translation", "")
            det_lang = analysis_data.get("detected_language", "English")
            trans_note = analysis_data.get("translation_note")

            if analysis_data.get("is_trimmed"):
                st.warning("⚠️ **Note:** Caption exceeded 1000 characters and was trimmed to the first 1000 characters for analysis.")

            col_c1, col_c2 = st.columns([1, 1])
            with col_c1:
                st.markdown(f"**Original Caption:**")
                st.info(orig_caption if orig_caption else "None provided")
            with col_c2:
                if det_lang.lower() not in ["english", "none"]:
                    st.markdown(f"**English Translation:** *(Detected Language: {det_lang})*")
                    st.success(trans_caption if trans_caption else orig_caption)
                    if trans_note:
                        st.caption(f"ℹ️ Translation Note: {trans_note}")
                else:
                    st.markdown(f"**Language:** `{det_lang}`")
                    st.caption("Caption provided in English; no translation required.")

            st.markdown("---")

            # C. Color-Coded Claim Table
            st.markdown("#### 📋 Atomic Claims & Grounded Verification Table")
            st.caption("Each claim is evaluated against evidence from visual media, frames, audio transcript, and container metadata:")

            table_rows_html = []
            for comp in analysis_data.get("comparisons", []):
                cid = comp.get("claim_id", "")
                ctext = comp.get("claim_text", "")
                ctype = comp.get("type", "other")
                cstatus = comp.get("status", "cannot_verify")
                cevs = comp.get("evidence_ids", [])
                ev_str = ", ".join(cevs) if cevs else "None"
                creason = comp.get("reason", "")
                cconf = comp.get("confidence", 0.5)

                if cstatus == "supported":
                    badge_html = '<span style="background-color: #28a745; color: white; padding: 3px 8px; border-radius: 4px; font-weight: bold; font-size: 0.85rem;">supported</span>'
                elif cstatus == "contradicted":
                    badge_html = '<span style="background-color: #dc3545; color: white; padding: 3px 8px; border-radius: 4px; font-weight: bold; font-size: 0.85rem;">contradicted</span>'
                else:
                    badge_html = '<span style="background-color: #6c757d; color: white; padding: 3px 8px; border-radius: 4px; font-weight: bold; font-size: 0.85rem;">cannot_verify</span>'

                table_rows_html.append(
                    f'<tr style="border-bottom: 1px solid #dee2e6;">'
                    f'<td style="padding: 10px; font-weight: 500; color: #212529;"><b>{cid}:</b> {ctext}</td>'
                    f'<td style="padding: 10px; color: #495057;"><code>{ctype}</code></td>'
                    f'<td style="padding: 10px; text-align: center;">{badge_html}</td>'
                    f'<td style="padding: 10px; color: #495057;"><code>{ev_str}</code></td>'
                    f'<td style="padding: 10px; color: #343a40; font-size: 0.9rem;">{creason}</td>'
                    f'<td style="padding: 10px; text-align: right; color: #495057;"><b>{cconf:.0%}</b></td>'
                    f'</tr>'
                )

            table_content = "".join(table_rows_html)
            table_markup = (
                '<div style="overflow-x: auto; margin-bottom: 20px;">'
                '<table style="width: 100%; border-collapse: collapse; border: 1px solid #dee2e6; border-radius: 6px; font-family: -apple-system, BlinkMacSystemFont, sans-serif;">'
                '<thead>'
                '<tr style="background-color: #f1f3f5; text-align: left; border-bottom: 2px solid #dee2e6;">'
                '<th style="padding: 10px; color: #495057;">Claim</th>'
                '<th style="padding: 10px; color: #495057;">Type</th>'
                '<th style="padding: 10px; color: #495057; text-align: center;">Status</th>'
                '<th style="padding: 10px; color: #495057;">Evidence IDs</th>'
                '<th style="padding: 10px; color: #495057;">Forensic Reason</th>'
                '<th style="padding: 10px; color: #495057; text-align: right;">Confidence</th>'
                '</tr>'
                '</thead>'
                f'<tbody>{table_content}</tbody>'
                '</table>'
                '</div>'
            )
            st.markdown(table_markup, unsafe_allow_html=True)

            # D. Collapsed Expander: "What we looked at" (Evidence Bundle)
            ev_items = analysis_data.get("evidence_bundle", {}).get("evidence_items", [])
            with st.expander("🔍 What we looked at (Forensic Evidence Bundle)", expanded=False):
                st.caption("Exact visual, acoustic, and metadata facts gathered from the media that each claim was compared to:")
                if ev_items:
                    for ev in ev_items:
                        st.markdown(f"- **`[{ev.get('id')}]`** `({ev.get('source')})`: {ev.get('text')}")
                else:
                    st.write("No evidence items bundle found.")

            # E. Separate Context Notes (Sensational wording & Unverifiable sources)
            context_notes = analysis_data.get("context_notes", [])
            st.markdown("#### ℹ️ Context Notes (Rhetoric & Attribution Clues)")
            st.caption("These notes highlight rhetorical certainty patterns and unverified attributions in caption text. They are context notes, **NOT tampering evidence**.")
            if context_notes:
                for n in context_notes:
                    cat = n.get("category", "context_note")
                    phrase = n.get("phrase", "")
                    expl = n.get("explanation", "")
                    st.markdown(f"- **`[{cat}]`** *'{phrase}'*: {expl}")
            else:
                st.info("No absolute certainty markers, claims of causation, or unverified sources detected in caption text.")

            # F. "What we could NOT check" Box
            unverifiable_items = analysis_data.get("unverifiable_claims", [])
            if unverifiable_items:
                unv_rows = []
                for uv in unverifiable_items:
                    unv_rows.append(
                        f"<li style='margin-bottom: 8px;'><b>{uv.get('claim_id')} ({uv.get('type')}):</b> \"{uv.get('claim_text')}\"<br>"
                        f"<span style='color: #495057;'><b>Why:</b> {uv.get('reason')}</span><br>"
                        f"<span style='color: #0056b3;'><b>Recommended Human Check:</b> {uv.get('human_check')}</span></li>"
                    )
                unv_markup = (
                    '<div style="background-color: #fff3cd; border: 1px solid #ffeeba; border-left: 5px solid #ffc107; border-radius: 6px; padding: 14px 18px; margin-top: 15px; margin-bottom: 20px;">'
                    '<div style="font-weight: 600; color: #856404; font-size: 1rem; margin-bottom: 8px;">'
                    '⚠️ What we could NOT check (Human OSINT Required)'
                    '</div>'
                    '<div style="color: #856404; font-size: 0.9rem; margin-bottom: 10px;">'
                    'A date or place claim can almost never be proven from media alone without verifiable metadata or visible signage. <i>\'Cannot verify\' is an honest forensic result, not a failure.</i>'
                    '</div>'
                    f'<ul style="margin: 0; padding-left: 20px; font-size: 0.88rem;">{"".join(unv_rows)}</ul>'
                    '</div>'
                )
                st.markdown(unv_markup, unsafe_allow_html=True)

        # G. Text & Context Signal Status Cards
        st.markdown("---")
        st.markdown("#### 🔬 Registered Text & Plausibility Signals")
        for s in txt_signals:
            score_str = f"{s.get('score'):.2f}" if s.get("score") is not None else "--"
            status_badge = "SKIPPED" if "SKIPPED" in str(s.get("evidence", "")) else ("FAILED" if "FAILED" in str(s.get("evidence", "")) else "NORMAL")
            st.markdown(f"**{s.get('name')}** (Score: `{score_str}` • Status: `{status_badge}`)")
            st.markdown(f"_{s.get('evidence')}_")
            with st.expander(f"Technical details: {s.get('signal_id')}", expanded=False):
                st.write(f"Signal ID: `{s.get('signal_id')}`")
                st.write(f"Limitation: {s.get('limitation')}")
            st.markdown("---")

        # H. Technical Details Collapsed Expander
        with st.expander("🛠️ Technical Details & Raw Inspection", expanded=False):
            st.write(f"**Groq Text Model:** `{settings.GROQ_TEXT_MODEL}`")
            st.write(f"**Groq Vision Model:** `{settings.GROQ_VISION_MODEL}`")
            if analysis_data:
                st.markdown("**Structured Analysis JSON:**")
                st.json(analysis_data)

    # --------------------------------------------------------------------------
    # TAB 6: CROSS-MODAL FINDINGS
    # --------------------------------------------------------------------------
    with tab_corr:
        st.subheader("Cross-Modal Correlated Findings")
        findings = report.get("cross_modal_findings", [])

        if not findings:
            st.info("No correlated cross-modal interactions detected.")
        else:
            for f in findings:
                eff = f.get("effect", "strengthens")
                badge_color = "#dc3545" if eff == "strengthens" else "#28a745"
                cites = ", ".join(f.get("supporting_signals", []))
                st.markdown(
                    f"""
                    <div style="border-left: 4px solid {badge_color}; background-color: #f8f9fa; padding: 12px; margin-bottom: 10px; border-radius: 4px;">
                        <span style="background-color: {badge_color}; color: white; padding: 2px 6px; border-radius: 3px; font-size: 0.75rem; font-weight: bold;">
                            {eff.upper()} SUSPICION
                        </span>
                        <div style="margin-top: 6px; font-size: 0.95rem; color: #212529;">
                            {f.get('finding')}
                        </div>
                        <div style="margin-top: 4px; font-size: 0.8rem; color: #6c757d;">
                            <b>Supporting Signal IDs:</b> {cites}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        col_cm1, col_cm2 = st.columns(2)
        with col_cm1:
            st.markdown("#### System Forensic Limitations")
            for lim in report.get("limitations", []):
                st.markdown(f"- *{lim}*")
        with col_cm2:
            st.markdown("#### Recommended Human Checks (OSINT)")
            for chk in report.get("recommended_human_checks", []):
                st.markdown(f"- [ ] {chk}")

    # --------------------------------------------------------------------------
    # TAB 7: REPORT & EXPORT
    # --------------------------------------------------------------------------
    with tab_report:
        st.subheader("Forensic Dossier & Export")
        st.write("Download complete authenticated deliverables for investigative documentation:")

        col_d1, col_d2 = st.columns(2)
        with col_d1:
            st.download_button(
                label="📄 Download Forensic Dossier (PDF)",
                data=active_case.get("pdf_bytes", b""),
                file_name=f"TruthLens_{report.get('case_id')}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        with col_d2:
            st.download_button(
                label="📊 Download Raw Audit Report (JSON)",
                data=active_case.get("json_bytes", b""),
                file_name=f"TruthLens_{report.get('case_id')}.json",
                mime="application/json",
                use_container_width=True,
            )

        st.markdown("---")
        st.markdown("#### Case Audit History")
        history = report.get("history", [])
        if history:
            h_table = [{"Timestamp": h.get("time"), "Forensic Operation": h.get("action")} for h in history]
            st.dataframe(h_table, use_container_width=True)
