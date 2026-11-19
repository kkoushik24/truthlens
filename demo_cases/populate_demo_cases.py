"""Generate pre-computed demo cases for TruthLens instant presentation."""

import sys
from pathlib import Path

# Add project root to path
base_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(base_dir))

import json
import shutil

from core.case_manager import CaseManager
from core.schemas import ForensicReport, Signal, CrossModalFinding, OverallIndicator, RegionLocation, TimeLocation, HistoryItem
from image_forensics.pipeline import analyze_image_pipeline
from text_analysis.pipeline import analyze_text_pipeline
from text_analysis.llm_provider import LocalHeuristicVisionProvider
from audio_forensics.pipeline import analyze_audio_pipeline
from correlation.engine import correlate_forensic_signals
from report.generator import generate_forensic_report_bundle

demo_cases_dir = base_dir / "demo_cases"
samples_dir = base_dir / "samples"
demo_cases_dir.mkdir(parents=True, exist_ok=True)

# ==============================================================================
# DEMO CASE 1: Elevated Suspicion - Spliced Photo with Context Contradiction
# ==============================================================================
case1_dir = demo_cases_dir / "case_01_spliced_photo_claim"
case1_dir.mkdir(parents=True, exist_ok=True)
case1_mgr = CaseManager(case_id="DEMO-2026-ELEVATED")

# Save inputs
edited_sample = samples_dir / "edited_photo.jpg"
case1_mgr.save_original("edited_photo.jpg", edited_sample.read_bytes())
claim_text = "Undeniable proof: Alien spacecraft spotted in downtown Miami in 2024!"
case1_mgr.save_original("claim.txt", claim_text.encode("utf-8"))

# Run image pipeline (generates heatmap artifact)
img_signals = analyze_image_pipeline(edited_sample, case_manager=case1_mgr)

# Run text pipeline
txt_signals = analyze_text_pipeline(
    caption=claim_text,
    image_path=edited_sample,
    case_manager=case1_mgr,
    llm_provider=LocalHeuristicVisionProvider(),
)

all_signals_c1 = img_signals + txt_signals
corr_c1 = correlate_forensic_signals(all_signals_c1, inputs=["edited_photo.jpg", "claim.txt"], case_manager=case1_mgr)
report_c1, json_c1, pdf_c1 = generate_forensic_report_bundle(case1_mgr, all_signals_c1, corr_c1)

# Copy case artifacts to demo_cases folder
shutil.copy2(json_c1, case1_dir / "report.json")
shutil.copy2(pdf_c1, case1_dir / "report.pdf")
case1_art_dir = case1_dir / "artifacts"
case1_art_dir.mkdir(parents=True, exist_ok=True)
for f in case1_mgr.artifacts_dir.glob("*.*"):
    shutil.copy2(f, case1_art_dir / f.name)

# ==============================================================================
# DEMO CASE 2: Low Suspicion - Authentic Corroborated Capture
# ==============================================================================
case2_dir = demo_cases_dir / "case_02_authentic_wildlife"
case2_dir.mkdir(parents=True, exist_ok=True)
case2_mgr = CaseManager(case_id="DEMO-2026-AUTHENTIC")

clean_sample = samples_dir / "clean_photo.jpg"
case2_mgr.save_original("clean_photo.jpg", clean_sample.read_bytes())
caption_clean = "A quiet sunny afternoon in the public park with trees and clear sky."
case2_mgr.save_original("caption.txt", caption_clean.encode("utf-8"))

img_signals_c2 = analyze_image_pipeline(clean_sample, case_manager=case2_mgr)
txt_signals_c2 = analyze_text_pipeline(
    caption=caption_clean,
    image_path=clean_sample,
    case_manager=case2_mgr,
    llm_provider=LocalHeuristicVisionProvider(),
)

all_signals_c2 = img_signals_c2 + txt_signals_c2
corr_c2 = correlate_forensic_signals(all_signals_c2, inputs=["clean_photo.jpg", "caption.txt"], case_manager=case2_mgr)
report_c2, json_c2, pdf_c2 = generate_forensic_report_bundle(case2_mgr, all_signals_c2, corr_c2)

shutil.copy2(json_c2, case2_dir / "report.json")
shutil.copy2(pdf_c2, case2_dir / "report.pdf")
case2_art_dir = case2_dir / "artifacts"
case2_art_dir.mkdir(parents=True, exist_ok=True)
for f in case2_mgr.artifacts_dir.glob("*.*"):
    shutil.copy2(f, case2_art_dir / f.name)

print("Pre-computed demo cases successfully populated in /demo_cases.")
