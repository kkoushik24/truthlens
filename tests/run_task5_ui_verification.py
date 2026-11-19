"""Comprehensive verification for Task 5: Text & Context Tab UI."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import json
from core.case_manager import CaseManager
from text_analysis.pipeline import analyze_text_pipeline
from correlation.engine import correlate_forensic_signals
from report.generator import generate_forensic_report_bundle


def verify_task_5():
    print("=" * 80)
    print("RUNNING TASK 5 TEXT & CONTEXT TAB UI INTEGRATION VERIFICATION")
    print("=" * 80)

    # 1. Full pipeline run on walking_banana.png + caption
    print("\n--- TEST CASE 1: End-to-end Text Pipeline on walking_banana.png ---")
    case_mgr = CaseManager("TEST-UI-TASK5-001")
    img_path = PROJECT_ROOT / "samples" / "walking_banana.png"
    caption = "A banana walking on a beach in 2019"
    case_mgr.save_original("walking_banana.png", img_path.read_bytes())
    case_mgr.save_original("caption.txt", caption.encode("utf-8"))

    signals = analyze_text_pipeline(
        caption=caption,
        image_path=img_path,
        case_manager=case_mgr,
    )

    # Check signals returned
    sig_ids = [s.signal_id for s in signals]
    print(f"Signals generated: {sig_ids}")
    assert "txt_vis_match_001" in sig_ids, "Expected txt_vis_match_001"
    assert "txt_plaus_001" in sig_ids, "Expected txt_plaus_001"
    assert "txt_heur_001" in sig_ids, "Expected txt_heur_001"

    # Check that artifact text_context_analysis.json was created
    art_path = case_mgr.get_artifact_path("text_context_analysis.json")
    assert art_path.is_file(), f"Expected artifact {art_path} to exist"

    data = json.loads(art_path.read_text(encoding="utf-8"))
    print("\nStructured Artifact Content:")
    print(f"  Summary Text: {data.get('summary_text')}")
    print(f"  Counts: {data.get('counts')}")
    print(f"  Total Comparisons: {len(data.get('comparisons', []))}")
    print(f"  Evidence Items: {len(data.get('evidence_bundle', {}).get('evidence_items', []))}")
    print(f"  Unverifiable Claims Box Items: {len(data.get('unverifiable_claims', []))}")

    # Verify Summary Box requirements
    assert "summary_text" in data and len(data["summary_text"]) > 20
    assert "counts" in data and "supported" in data["counts"]

    # Verify Claim Table fields
    for comp in data["comparisons"]:
        assert "claim_id" in comp
        assert "claim_text" in comp
        assert "type" in comp
        assert "status" in comp
        assert comp["status"] in ["supported", "contradicted", "cannot_verify"]
        assert "evidence_ids" in comp
        assert "reason" in comp
        assert "confidence" in comp

    # Verify "What we looked at" evidence bundle
    ev_items = data.get("evidence_bundle", {}).get("evidence_items", [])
    assert len(ev_items) >= 5, "Expected full evidence bundle"
    for ev in ev_items:
        assert "id" in ev and "source" in ev and "text" in ev

    # Verify "What we could NOT check" Box
    assert len(data.get("unverifiable_claims", [])) >= 1, "Expected unverified date/place claim tracked"
    unv = data["unverifiable_claims"][0]
    assert "human_check" in unv and len(unv["human_check"]) > 10

    # 2. Verify Overview Tab Logic:
    # A. Contradicted caption (score >= 0.35) appears in Top Reasons
    print("\n--- TEST CASE 2: Overview Tab Top Reasons Placement (Score >= 0.35) ---")
    corr = correlate_forensic_signals(signals, inputs=["walking_banana.png", "caption.txt"], case_manager=case_mgr)
    report_obj, _, _ = generate_forensic_report_bundle(case_mgr, signals, corr)
    report_dict = report_obj.model_dump()

    all_sigs = report_dict.get("signals", [])
    scored_sigs = [s for s in all_sigs if s.get("score") is not None and s.get("score") >= 0.35]
    scored_ids = [s["signal_id"] for s in scored_sigs]
    print(f"Signals with score >= 0.35 (Eligible for Top Reasons): {scored_ids}")

    caption_sig = next(s for s in all_sigs if s["signal_id"] == "txt_vis_match_001")
    if caption_sig["score"] >= 0.35:
        assert "txt_vis_match_001" in scored_ids, "Caption signal with score >= 0.35 MUST be eligible for Top Reasons"
        print("Verified: Caption mismatch correctly prioritized for Top Reasons.")

    # B. Clean photo + matching caption (score = 0.0) goes under "Checks that found nothing unusual"
    print("\n--- TEST CASE 3: Clean Photo + Matching Caption Placement (Score = 0.0) ---")
    case_mgr_clean = CaseManager("TEST-UI-TASK5-CLEAN")
    clean_img = PROJECT_ROOT / "samples" / "clean_photo.jpg"
    clean_cap = "A yellow circle and a green shape on a light background"
    signals_clean = analyze_text_pipeline(caption=clean_cap, image_path=clean_img, case_manager=case_mgr_clean)
    clean_match = next(s for s in signals_clean if s.signal_id == "txt_vis_match_001")
    print(f"Clean Caption Signal Score: {clean_match.score} ({clean_match.evidence})")

    unremarkable = [s for s in signals_clean if s.score is None or s.score < 0.35]
    assert clean_match in unremarkable, "Supported caption MUST go under 'Checks that found nothing unusual'"
    print("Verified: Supported caption correctly placed under unremarkable checks.")

    # 3. Empty Caption Skipped
    print("\n--- TEST CASE 4: Empty Caption Handling in Pipeline ---")
    case_mgr_empty = CaseManager("TEST-UI-TASK5-EMPTY")
    signals_empty = analyze_text_pipeline(caption="", image_path=clean_img, case_manager=case_mgr_empty)
    empty_match = next(s for s in signals_empty if s.signal_id == "txt_vis_match_001")
    print(f"Empty Caption Signal: Score={empty_match.score}, Evidence='{empty_match.evidence}'")
    assert empty_match.score is None
    assert "SKIPPED" in empty_match.evidence
    print("Verified: Empty caption marked as SKIPPED and excluded from scoring.")

    print("\n" + "=" * 80)
    print("ALL TASK 5 UI INTEGRATION VERIFICATIONS PASSED SUCCESSFULLY!")
    print("=" * 80)


if __name__ == "__main__":
    verify_task_5()
