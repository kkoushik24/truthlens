"""Comprehensive verification for Task 4: Caption Signal and Overall Effect."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import json
from core.schemas import Signal
from text_analysis.caption_checker import compute_caption_signal, LIMITATION_TEXT
from correlation.rules_engine import evaluate_rule_based_correlation, BASE_WEIGHTS


def verify_task_4():
    print("=" * 80)
    print("RUNNING TASK 4 CAPTION SIGNAL AND OVERALL EFFECT VERIFICATION")
    print("=" * 80)

    # 1. Verification of Score Formula & Consistency Check
    print("\n--- TEST CASE 1: Score Formula & Consistency Check ---")
    # Case A: Contradicted claim present (e.g. 1 contradicted, 1 cannot_verify, 2 supported out of 4)
    comp_a = {
        "status": "COMPLETED",
        "comparisons": [
            {"claim_id": "c1", "claim_text": "banana", "status": "supported", "checkable_from_media": True},
            {"claim_id": "c2", "claim_text": "walking", "status": "supported", "checkable_from_media": True},
            {"claim_id": "c3", "claim_text": "beach", "status": "contradicted", "checkable_from_media": True},
            {"claim_id": "c4", "claim_text": "2019", "status": "cannot_verify", "checkable_from_media": True},
        ]
    }
    sig_a = compute_caption_signal(comp_a, "test.png")
    print(f"Case A (1 contradicted, 1 unverified, 2 supported):")
    print(f"  Signal ID: {sig_a.signal_id}")
    print(f"  Name: {sig_a.name}")
    print(f"  Score: {sig_a.score}")
    print(f"  Evidence: {sig_a.evidence}")
    print(f"  Limitation: {sig_a.limitation}")

    assert sig_a.signal_id == "txt_vis_match_001"
    assert sig_a.name == "Possible out-of-context use"
    assert sig_a.score >= 0.35, f"Expected score >= 0.35 for contradicted claim, got {sig_a.score}"
    assert "beach" in sig_a.evidence
    assert sig_a.limitation == LIMITATION_TEXT

    # Case B: Fully supported claims
    comp_b = {
        "status": "COMPLETED",
        "comparisons": [
            {"claim_id": "c1", "claim_text": "banana", "status": "supported", "checkable_from_media": True},
            {"claim_id": "c2", "claim_text": "walking", "status": "supported", "checkable_from_media": True},
        ]
    }
    sig_b = compute_caption_signal(comp_b, "test.png")
    print(f"\nCase B (Fully supported):")
    print(f"  Score: {sig_b.score}")
    print(f"  Evidence: {sig_b.evidence}")

    assert sig_b.score == 0.0
    assert sig_b.evidence == "The caption matches what is visible. This does not show the media is unedited."

    # Case C: Skipped caption
    comp_c = {"status": "SKIPPED: no caption provided", "comparisons": []}
    sig_c = compute_caption_signal(comp_c, "test.png")
    print(f"\nCase C (Skipped caption):")
    print(f"  Score: {sig_c.score}")
    print(f"  Evidence: {sig_c.evidence}")

    assert sig_c.score is None
    assert sig_c.evidence == "SKIPPED: no caption provided"
    print("Verified: Score calculation, consistency check, limitation, and naming verified.")

    # 2. Overall Effect: Caption Mismatch Never Pushes Overall Level Above MODERATE By Itself
    print("\n--- TEST CASE 2: Caption Mismatch Capped at MODERATE By Itself ---")
    # Simulate a scenario where caption mismatch is severe (0.95), but image signals are clean (< 0.20)
    signals_solo_mismatch = [
        Signal(signal_id="img_ai_001", modality="image", name="AI Image Detector", score=0.10, evidence="Clean image capture.", limitation="AI detector limitation", source_file="clean.jpg"),
        Signal(signal_id="txt_plaus_001", modality="text", name="Visual Plausibility", score=0.10, evidence="Plausible scene.", limitation="Plausibility limitation", source_file="clean.jpg"),
        Signal(signal_id="img_exif_001", modality="image", name="EXIF Metadata Audit", score=0.10, evidence="Valid camera EXIF.", limitation="EXIF limitation", source_file="clean.jpg"),
        Signal(signal_id="txt_vis_match_001", modality="text", name="Possible out-of-context use", score=0.95, evidence="Direct contradiction.", limitation=LIMITATION_TEXT, source_file="clean.jpg"),
    ]
    ind_solo, findings_solo = evaluate_rule_based_correlation(signals_solo_mismatch)
    print(f"Solo Mismatch Indicator Level: {ind_solo.level.upper()}")
    print(f"Solo Mismatch Warnings: {ind_solo.warnings}")

    assert ind_solo.level == "moderate", f"Caption mismatch alone must NEVER exceed MODERATE, got {ind_solo.level}"
    assert any("possible out-of-context use" in w.lower() for w in ind_solo.warnings)

    # Test that even if composite score is very high from caption mismatch, level is capped at MODERATE
    signals_extreme = [
        Signal(signal_id="txt_vis_match_001", modality="text", name="Possible out-of-context use", score=1.0, evidence="Contradicted", limitation=LIMITATION_TEXT, source_file="clean.jpg"),
        Signal(signal_id="txt_heur_001", modality="text", name="Caption Linguistic Heuristics", score=0.90, evidence="Sensational wording", limitation="Heuristic", source_file="clean.jpg"),
    ]
    ind_extreme, _ = evaluate_rule_based_correlation(signals_extreme)
    assert ind_extreme.level == "moderate", f"Caption mismatch must NEVER push level above MODERATE by itself, got {ind_extreme.level}"
    assert any("level capped at moderate" in w.lower() for w in ind_extreme.warnings)
    print("Verified: Caption mismatch alone is strictly capped at MODERATE.")

    # 3. Overall Effect: Strengthening Finding When Combined With Independent Signal >= 0.60
    print("\n--- TEST CASE 3: Strengthening Finding With Independent Signal >= 0.60 ---")
    signals_strengthen = [
        Signal(signal_id="img_ai_001", modality="image", name="AI Image Detector", score=0.88, evidence="AI generated face detected.", limitation="AI detector limitation", source_file="ai.jpg"),
        Signal(signal_id="txt_vis_match_001", modality="text", name="Possible out-of-context use", score=0.75, evidence="Contradicted caption.", limitation=LIMITATION_TEXT, source_file="ai.jpg"),
    ]
    ind_str, findings_str = evaluate_rule_based_correlation(signals_strengthen)
    print(f"Strengthened Indicator Level: {ind_str.level.upper()}")
    print(f"Cross-Modal Findings ({len(findings_str)}):")
    for f in findings_str:
        print(f"  - [{f.effect}] {f.finding} (citing: {f.supporting_signals})")

    match_findings = [
        f for f in findings_str
        if "txt_vis_match_001" in f.supporting_signals and "img_ai_001" in f.supporting_signals
    ]
    assert len(match_findings) >= 1, "Expected finding citing both txt_vis_match_001 and img_ai_001"
    assert match_findings[0].effect == "strengthens"
    print("Verified: Strengthening finding citing both signal IDs created successfully.")

    # 4. Fully Supported Caption Never Lowers Overall Level
    print("\n--- TEST CASE 4: Fully Supported Caption Never Lowers Overall Level ---")
    signals_supported_with_tampering = [
        Signal(signal_id="img_ai_001", modality="image", name="AI Image Detector", score=0.72, evidence="AI generation detected.", limitation="AI detector limitation", source_file="ai.jpg"),
        Signal(signal_id="txt_plaus_001", modality="text", name="Visual Plausibility", score=0.55, evidence="Surreal anatomy.", limitation="Plausibility limitation", source_file="ai.jpg"),
        Signal(signal_id="txt_vis_match_001", modality="text", name="Possible out-of-context use", score=0.0, evidence="The caption matches what is visible. This does not show the media is unedited.", limitation=LIMITATION_TEXT, source_file="ai.jpg"),
    ]
    ind_sup, findings_sup = evaluate_rule_based_correlation(signals_supported_with_tampering)
    print(f"Indicator Level with Supported Caption: {ind_sup.level.upper()}")
    print(f"Warnings: {ind_sup.warnings}")

    assert ind_sup.level in ["moderate", "elevated"], f"Supported caption must NEVER pull down tampering level to LOW, got {ind_sup.level}"
    assert any("This does not show the media is unedited" in w for w in ind_sup.warnings)
    print("Verified: Fully supported caption never pulls down level and warns that media may still be edited.")

    # 5. Re-normalization When Caption Is Missing
    print("\n--- TEST CASE 5: Re-normalization When Caption Is Missing ---")
    signals_no_cap = [
        Signal(signal_id="img_ai_001", modality="image", name="AI Image Detector", score=0.40, evidence="Mild artifacts.", limitation="AI detector limitation", source_file="photo.jpg"),
        Signal(signal_id="txt_plaus_001", modality="text", name="Visual Plausibility", score=0.40, evidence="Plausible scene.", limitation="Plausibility limitation", source_file="photo.jpg"),
        Signal(signal_id="txt_vis_match_001", modality="text", name="Possible out-of-context use", score=None, evidence="SKIPPED: no caption provided", limitation=LIMITATION_TEXT, source_file="photo.jpg"),
    ]
    ind_nocap, _ = evaluate_rule_based_correlation(signals_no_cap)
    print(f"Indicator Level when caption skipped: {ind_nocap.level.upper()}")
    # With AI (0.40) and Plaus (0.40), composite should be 0.40 -> MODERATE
    assert ind_nocap.level == "moderate"
    # Ensure BASE_WEIGHTS are intact and not mutated
    assert BASE_WEIGHTS["img_ai_001"] == 0.30
    assert BASE_WEIGHTS["txt_vis_match_001"] == 0.10
    print("Verified: Weights re-normalized cleanly without mutating base weights.")

    print("\n" + "=" * 80)
    print("ALL TASK 4 VERIFICATIONS PASSED SUCCESSFULLY!")
    print("=" * 80)


if __name__ == "__main__":
    verify_task_4()
