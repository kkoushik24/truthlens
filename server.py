"""TruthLens: FastAPI Server & Production Web Application Backend.

Serves the modern, interactive HTML5 forensic workstation frontend,
processes multimodal evidence through forensic analysis pipelines,
and serves pre-computed demo cases and cryptographic reports.
"""

import sys
import os
import json
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, List

# Add workspace root to Python path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from core.case_manager import CaseManager
from core.schemas import ForensicReport, Signal, CrossModalFinding, OverallIndicator
from core.config import settings

app = FastAPI(
    title="TruthLens Forensic Workstation",
    description="Multimodal Digital Forensics & Contextual Claim Verification Platform",
    version="2.0.0",
)

# Enable CORS for local testing and cross-origin access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = BASE_DIR / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)


# ==============================================================================
# STATIC & FRONTEND ROUTING
# ==============================================================================
@app.get("/", response_class=HTMLResponse)
def serve_index():
    """Serve the primary forensic workstation single-page application."""
    index_path = STATIC_DIR / "index.html"
    if not index_path.is_file():
        raise HTTPException(status_code=404, detail="Frontend index.html not found.")
    return HTMLResponse(content=index_path.read_text(encoding="utf-8"))


@app.get("/health")
@app.get("/api/health")
def health_check():
    """Health check endpoint for cloud hosting platforms like Render."""
    return {"status": "ok", "service": "TruthLens Forensic Workstation"}


# ==============================================================================
# DEMO CASES APIS
# ==============================================================================
@app.get("/api/demos")
def list_demos():
    """List available pre-computed forensic demo cases."""
    return [
        {
            "id": "case_01_spliced_photo_claim",
            "title": "Case 1: Spliced Photo with Context Mismatch",
            "modality": "Image + Claim",
            "level": "ELEVATED",
            "description": "Composite photo with Photoshop metadata, ELA compression divergence, and context contradiction.",
        },
        {
            "id": "case_02_authentic_wildlife",
            "title": "Case 2: Authentic Multi-Modal Wildlife Capture",
            "modality": "Image + Claim",
            "level": "LOW",
            "description": "Genuine Canon DSLR photo with matching EXIF baseline and grounded descriptive caption.",
        },
    ]


@app.get("/api/demo/{case_id}")
def get_demo_case(case_id: str):
    """Load a pre-computed demo case and return report and artifact URLs."""
    case_dir = settings.DEMO_CASES_DIR / case_id
    report_json_path = case_dir / "report.json"
    if not report_json_path.is_file():
        raise HTTPException(status_code=404, detail=f"Demo case '{case_id}' not found.")

    try:
        report_data = json.loads(report_json_path.read_text(encoding="utf-8"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read demo report: {str(e)}")

    artifacts_dir = case_dir / "artifacts"
    artifacts_map: Dict[str, str] = {}
    if artifacts_dir.exists():
        for f in artifacts_dir.glob("*.*"):
            artifacts_map[f.name] = f"/api/demo_artifacts/{case_id}/{f.name}"

    # Also check if text_context_analysis exists
    text_analysis = None
    txt_analysis_file = artifacts_dir / "text_context_analysis.json"
    if txt_analysis_file.is_file():
        try:
            text_analysis = json.loads(txt_analysis_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    has_pdf = (case_dir / "report.pdf").is_file()

    return {
        "status": "success",
        "case_id": report_data.get("case_id", "DEMO-CASE"),
        "source_mode": "demo",
        "report": report_data,
        "artifacts": artifacts_map,
        "text_analysis": text_analysis,
        "pdf_url": f"/api/demo_pdf/{case_id}" if has_pdf else None,
        "json_url": f"/api/demo_json/{case_id}",
    }


@app.get("/api/demo_artifacts/{case_id}/{filename}")
def get_demo_artifact(case_id: str, filename: str):
    """Serve artifact file from a demo case."""
    art_path = settings.DEMO_CASES_DIR / case_id / "artifacts" / filename
    if not art_path.is_file():
        raise HTTPException(status_code=404, detail="Artifact not found.")
    return FileResponse(art_path)


@app.get("/api/demo_pdf/{case_id}")
def get_demo_pdf(case_id: str):
    """Download PDF dossier for a demo case."""
    pdf_path = settings.DEMO_CASES_DIR / case_id / "report.pdf"
    if not pdf_path.is_file():
        raise HTTPException(status_code=404, detail="Demo PDF report not found.")
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=f"TruthLens_{case_id}.pdf",
    )


@app.get("/api/demo_json/{case_id}")
def get_demo_json(case_id: str):
    """Download JSON report for a demo case."""
    json_path = settings.DEMO_CASES_DIR / case_id / "report.json"
    if not json_path.is_file():
        raise HTTPException(status_code=404, detail="Demo JSON report not found.")
    return FileResponse(
        json_path,
        media_type="application/json",
        filename=f"TruthLens_{case_id}.json",
    )


# ==============================================================================
# LIVE FORENSIC INVESTIGATION PIPELINE
# ==============================================================================
@app.post("/api/analyze")
async def analyze_media(
    image: Optional[UploadFile] = File(None),
    video: Optional[UploadFile] = File(None),
    audio: Optional[UploadFile] = File(None),
    caption: Optional[str] = Form(None),
):
    """Execute complete multimodal forensic pipeline on live uploaded media and claims."""
    # Lazy import forensic pipelines on demand for ultra-fast server boot & healthchecks
    from image_forensics.pipeline import analyze_image_pipeline
    from video_forensics.pipeline import analyze_video_pipeline
    from audio_forensics.pipeline import analyze_audio_pipeline
    from text_analysis.pipeline import analyze_text_pipeline
    from correlation.engine import correlate_forensic_signals
    from report.generator import generate_forensic_report_bundle

    has_inputs = any([image, video, audio, caption and caption.strip()])
    if not has_inputs:
        raise HTTPException(
            status_code=400,
            detail="Please provide at least one media asset (image, video, audio) or a textual claim.",
        )

    case_mgr = CaseManager()
    all_signals: List[Signal] = []

    orig_img_path = None
    orig_vid_path = None
    orig_aud_path = None

    # 1. Image Forensics
    if image and image.filename:
        img_bytes = await image.read()
        if len(img_bytes) > 0:
            orig_img_path = case_mgr.save_original(image.filename, img_bytes)
            img_signals = analyze_image_pipeline(orig_img_path, case_manager=case_mgr)
            all_signals.extend(img_signals)

    # 2. Video Forensics
    if video and video.filename:
        vid_bytes = await video.read()
        if len(vid_bytes) > 0:
            orig_vid_path = case_mgr.save_original(video.filename, vid_bytes)
            vid_signals, extracted_audio = analyze_video_pipeline(
                orig_vid_path,
                caption=caption,
                case_manager=case_mgr,
            )
            all_signals.extend(vid_signals)
            if extracted_audio and not audio:
                extracted_aud_signals = analyze_audio_pipeline(
                    extracted_audio,
                    caption=caption,
                    case_manager=case_mgr,
                )
                all_signals.extend(extracted_aud_signals)

    # 3. Audio Forensics
    if audio and audio.filename:
        aud_bytes = await audio.read()
        if len(aud_bytes) > 0:
            orig_aud_path = case_mgr.save_original(audio.filename, aud_bytes)
            aud_signals = analyze_audio_pipeline(
                orig_aud_path,
                caption=caption,
                case_manager=case_mgr,
            )
            all_signals.extend(aud_signals)

    # 4. Text & Context Claim Forensics
    clean_caption = (caption or "").strip()
    if clean_caption or orig_img_path or orig_vid_path or orig_aud_path:
        if clean_caption:
            case_mgr.save_original("caption.txt", clean_caption.encode("utf-8"))
        target_media = orig_img_path or orig_vid_path or orig_aud_path
        target_type = "video" if orig_vid_path else ("audio" if orig_aud_path else "image")
        txt_signals = analyze_text_pipeline(
            caption=clean_caption,
            image_path=orig_img_path,
            media_path=target_media,
            media_type=target_type,
            case_manager=case_mgr,
        )
        all_signals.extend(txt_signals)

    # 5. Cross-Modal Correlation
    input_names = [p.name for p in case_mgr.list_originals()]
    correlation_data = correlate_forensic_signals(
        signals=all_signals,
        inputs=input_names,
        case_manager=case_mgr,
    )

    # 6. Report Generation
    report_obj, json_path, pdf_path = generate_forensic_report_bundle(
        case_manager=case_mgr,
        signals=all_signals,
        correlation_data=correlation_data,
    )

    # Gather artifact URLs
    artifacts_map: Dict[str, str] = {}
    if case_mgr.artifacts_dir.exists():
        for art in case_mgr.artifacts_dir.glob("*.*"):
            artifacts_map[art.name] = f"/api/artifacts/{case_mgr.case_id}/{art.name}"

    # Load text_context_analysis artifact if present
    text_analysis = None
    txt_analysis_file = case_mgr.get_artifact_path("text_context_analysis.json")
    if txt_analysis_file.is_file():
        try:
            text_analysis = json.loads(txt_analysis_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    return {
        "status": "success",
        "case_id": case_mgr.case_id,
        "source_mode": "live",
        "report": report_obj.model_dump(),
        "artifacts": artifacts_map,
        "text_analysis": text_analysis,
        "pdf_url": f"/api/pdf/{case_mgr.case_id}",
        "json_url": f"/api/json/{case_mgr.case_id}",
        "input_hashes": case_mgr.input_hashes,
    }


@app.get("/api/pdf/{case_id}")
def get_pdf_dossier(case_id: str):
    """Download official forensic PDF dossier for a case."""
    # 1. Check live cases
    pdf_path = settings.CASES_DIR / case_id / "report.pdf"
    if not pdf_path.is_file():
        # 2. Check demo cases
        pdf_path = settings.DEMO_CASES_DIR / case_id / "report.pdf"
    if not pdf_path.is_file():
        raise HTTPException(status_code=404, detail=f"PDF dossier for case '{case_id}' not found.")
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=f"TruthLens_Dossier_{case_id}.pdf",
    )


@app.get("/api/json/{case_id}")
def get_json_bundle(case_id: str):
    """Download cryptographic JSON report bundle for a case."""
    json_path = settings.CASES_DIR / case_id / "report.json"
    if not json_path.is_file():
        json_path = settings.DEMO_CASES_DIR / case_id / "report.json"
    if not json_path.is_file():
        raise HTTPException(status_code=404, detail=f"JSON report for case '{case_id}' not found.")
    return FileResponse(
        json_path,
        media_type="application/json",
        filename=f"TruthLens_Report_{case_id}.json",
    )


@app.get("/api/artifacts/{case_id}/{filename}")
def get_artifact(case_id: str, filename: str):
    """Serve generated artifact or report file for a case."""
    # 1. Check in cases/{case_id}/artifacts/
    art_path = settings.CASES_DIR / case_id / "artifacts" / filename
    if art_path.is_file():
        return FileResponse(art_path)

    # 2. Check directly in cases/{case_id}/ (e.g. report.pdf or report.json)
    root_path = settings.CASES_DIR / case_id / filename
    if root_path.is_file():
        media_type = "application/pdf" if filename.endswith(".pdf") else ("application/json" if filename.endswith(".json") else None)
        return FileResponse(root_path, media_type=media_type, filename=f"TruthLens_{filename}")

    # 3. Check in demo cases artifacts
    demo_path = settings.DEMO_CASES_DIR / case_id / "artifacts" / filename
    if demo_path.is_file():
        return FileResponse(demo_path)

    # 4. Check in demo cases root
    demo_root = settings.DEMO_CASES_DIR / case_id / filename
    if demo_root.is_file():
        media_type = "application/pdf" if filename.endswith(".pdf") else ("application/json" if filename.endswith(".json") else None)
        return FileResponse(demo_root, media_type=media_type, filename=f"TruthLens_{filename}")

    raise HTTPException(status_code=404, detail="Artifact not found.")


# Mount static directory for JS/CSS assets
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    print(f"🚀 TruthLens Forensic Web Server starting on http://localhost:{port}")
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=True)
