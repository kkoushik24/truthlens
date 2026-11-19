"""Test script for Task 11: Final Test on Walking Banana image."""

import json
from pathlib import Path
from core.case_manager import CaseManager
from image_forensics.pipeline import analyze_image_pipeline
from text_analysis.pipeline import analyze_text_pipeline
from correlation.engine import correlate_forensic_signals
from app import parse_signal_status

def run_test():
    image_path = Path("samples/walking_banana.png")
    caption = "A banana walking on a beach in 2019"

    print("=" * 70)
    print("TASK 11: FINAL FORENSIC RUN ON WALKING BANANA")
    print(f"Asset: {image_path} ({image_path.stat().st_size} bytes)")
    print(f"Caption: '{caption}'")
    print("=" * 70)

    case_mgr = CaseManager("TASK11-VERIFY")
    saved_img = case_mgr.save_original("walking_banana.png", image_path.read_bytes())
    case_mgr.save_original("caption.txt", caption.encode("utf-8"))

    # 1. Run Image Forensics Pipeline
    print("\n[1/3] Executing Image Forensics...")
    img_signals = analyze_image_pipeline(saved_img, case_manager=case_mgr)

    # 2. Run Text & Plausibility Pipeline
    print("[2/3] Executing Text & Vision Plausibility Pipeline...")
    txt_signals = analyze_text_pipeline(caption=caption, image_path=saved_img, case_manager=case_mgr)

    all_signals = img_signals + txt_signals

    # 3. Run Correlation Engine
    print("[3/3] Correlating Multimodal Signals...")
    correlation = correlate_forensic_signals(
        signals=all_signals,
        inputs=["walking_banana.png", "caption.txt"],
        case_manager=case_mgr,
    )

    indicator = correlation["overall_indicator"]
    summary = correlation.get("summary", "")
    findings = correlation.get("cross_modal_findings", [])
    human_checks = correlation.get("recommended_human_checks", [])
    limitations = correlation.get("limitations", [])

    # Format Signal Status Table
    table_rows = [parse_signal_status(s.model_dump()) for s in all_signals]

    print("\n" + "=" * 70)
    print("1. SIGNAL STATUS & HEALTH TABLE (Task 3 & 11)")
    print("=" * 70)
    col_fmt = "{:<18} {:<34} {:<10} {:<10} {:<8} {:<30}"
    print(col_fmt.format("Signal ID", "Signal Name", "Modality", "Status", "Score", "Error / Reason"))
    print("-" * 115)
    for row in table_rows:
        print(col_fmt.format(
            row["Signal ID"],
            row["Signal Name"][:33],
            row["Modality"],
            row["Status"],
            row["Score"],
            row["Error / Reason"][:30],
        ))

    print("\n" + "=" * 70)
    print("2. FINAL LEVEL & CONFIDENCE (Task 7 & 11)")
    print("=" * 70)
    print(f"Overall Level:      {indicator.level.upper()}")
    print(f"Assessed Confidence: {indicator.confidence:.0%}")
    print(f"Primary Drivers:    {indicator.primary_drivers}")

    print("\n" + "=" * 70)
    print("3. FORENSIC EVIDENCE & EVIDENCE SUMMARY")
    print("=" * 70)
    print(f"Summary: {summary}")
    print("\nSignals Evidence:")
    for s in all_signals:
        print(f"  * [{s.signal_id}] {s.name} (score={s.score}): {s.evidence}")

    print("\nCross-Modal Correlated Findings:")
    for f in findings:
        print(f"  * [{f.effect.upper()}] {f.finding} (supporting: {f.supporting_signals})")

    print("\nRecommended Human Checks:")
    for c in human_checks:
        print(f"  * {c}")

    if limitations:
        print("\nLimitations & Warnings:")
        for lim in limitations:
            print(f"  ! {lim}")

    print("\n" + "=" * 70)

if __name__ == "__main__":
    run_test()
