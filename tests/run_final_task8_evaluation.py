import sys
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core.case_manager import CaseManager
from video_forensics.pipeline import analyze_video_pipeline
from correlation.rules_engine import evaluate_rule_based_correlation
from correlation.human_checks import generate_recommended_human_checks

def main():
    print("=" * 80)
    print("TRUTHLENS FORENSIC INVESTIGATION — FINAL EVALUATION (TASK 8)")
    print("Target: samples/whatsapp_ai_test_video.mp4 (Uploaded with NO caption)")
    print("=" * 80)

    vid_path = BASE_DIR / "samples" / "whatsapp_ai_test_video.mp4"
    if not vid_path.exists():
        print(f"ERROR: Video file not found at {vid_path}")
        return

    case_mgr = CaseManager("FINAL-EVAL-WHATSAPP-AI")

    # Run complete video pipeline
    signals, extracted_audio = analyze_video_pipeline(
        video_path=vid_path,
        caption="",
        case_manager=case_mgr,
    )

    # Run correlation and rules engine
    overall, findings = evaluate_rule_based_correlation(signals)

    # -------------------------------------------------------------------------
    # 1. VIDEO SIGNAL STATUS TABLE
    # -------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("1. VIDEO SIGNAL STATUS TABLE")
    print("=" * 80)
    print(f"{'Signal ID':<15} {'Forensic Test Name':<42} {'Score':<8} {'Status':<10} {'Details / Diagnostic Reason'}")
    print("-" * 110)
    for s in signals:
        if "SKIPPED" in s.evidence:
            status = "SKIPPED"
            reason = s.evidence.split("SKIPPED:")[-1].strip()
        elif "FAILED" in s.evidence:
            status = "FAILED"
            reason = s.evidence.split("FAILED:")[-1].strip()
        else:
            status = "RAN"
            reason = s.evidence[:55] + "..." if len(s.evidence) > 55 else s.evidence

        score_str = f"{s.score:.2f}" if s.score is not None else "--"
        print(f"{s.signal_id:<15} {s.name:<42} {score_str:<8} {status:<10} {reason}")

    # -------------------------------------------------------------------------
    # 2. PER-FRAME SCORE DATA & TOP FLAGGED FRAMES
    # -------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("2. PER-FRAME AI DETECTION DATA & TOP FLAGGED KEYFRAMES")
    print("=" * 80)
    json_path = case_mgr.artifacts_dir / f"frame_scores_{vid_path.stem}.json"
    if json_path.exists():
        records = json.loads(json_path.read_text(encoding="utf-8"))
        print(f"Total sampled frames evaluated: {len(records)}")
        print(f"{'Frame #':<10} {'Timestamp':<14} {'AI Score':<12} {'Face Detected':<15} {'Frame Path'}")
        print("-" * 90)
        for r in sorted(records, key=lambda x: x["index"]):
            p_name = Path(r["path"]).name if r.get("path") else "--"
            print(f"#{r['index']:<9} {r['timestamp']:<13.2f}s {r['score']:<11.4f} {str(r['has_face']):<15} {p_name}")

        print("\n--- TOP 3 FLAGGED FRAMES ---")
        top3 = sorted(records, key=lambda x: x["score"], reverse=True)[:3]
        for rank, r in enumerate(top3, 1):
            face_str = " (Face detected & verified)" if r.get("has_face") else ""
            print(f"  Rank {rank}: Frame #{r['index']} at timestamp {r['timestamp']:.2f}s | AI Suspicion: {r['score']:.1%}{face_str}")

    # -------------------------------------------------------------------------
    # 3. FINAL LEVEL, CONFIDENCE & CONFIDENCE-REDUCTION REASONS
    # -------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("3. FINAL CORRELATION RESULTS & CONFIDENCE ASSESSMENT")
    print("=" * 80)
    print(f"Overall Suspicion Tier:  {overall.level.upper()}")
    print(f"Assessed Confidence:     {overall.confidence:.0%}")
    print(f"Primary Drivers:         {overall.primary_drivers}")

    print("\nConfidence Reduction Reasons Logged:")
    for w in overall.warnings:
        print(f"  * {w}")

    # -------------------------------------------------------------------------
    # 4. TOP REASONS (PLAIN ENGLISH) & CHECKS THAT FOUND NOTHING UNUSUAL
    # -------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("4. TOP REASONS (RANKED >= 0.35) & UNREMARKABLE CHECKS")
    print("=" * 80)

    scored_signals = [s for s in signals if s.score is not None and s.score >= 0.35]
    scored_signals.sort(key=lambda s: s.score, reverse=True)

    print("TOP REASONS (Plain English, strictly score >= 0.35):")
    for s in scored_signals:
        first_sentence = s.evidence.split(". ")[0] + "."
        print(f"  * [{s.name}] (Score: {s.score:.2f})")
        print(f"    Evidence: {first_sentence}")

    unremarkable = [s for s in signals if s.score is None or s.score < 0.35]
    print("\nCHECKS THAT FOUND NOTHING UNUSUAL (Collapsed Section):")
    for s in unremarkable:
        status_lbl = "SKIPPED" if "SKIPPED" in s.evidence else ("FAILED" if "FAILED" in s.evidence else "NORMAL")
        print(f"  * [{status_lbl:<7}] {s.name}")
        print(f"    Detail: {s.evidence}")

    human_checks = generate_recommended_human_checks(signals)
    print("\nRECOMMENDED NEXT STEPS (Human OSINT Checklist):")
    for c in human_checks:
        print(f"  - {c}")

    print("\n" + "=" * 80)
    print("END OF PIPELINE INVESTIGATION")
    print("=" * 80)

if __name__ == "__main__":
    main()
