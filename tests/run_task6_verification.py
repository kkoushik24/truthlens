import sys
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from video_forensics.pipeline import analyze_video_pipeline
from correlation.rules_engine import evaluate_rule_based_correlation
from correlation.human_checks import generate_recommended_human_checks
from core.case_manager import CaseManager

def run_task6_verification():
    print("=" * 70)
    print("TASK 6: VIDEO UI DATA & STRUCTURE VERIFICATION")
    print("=" * 70)

    vid_path = BASE_DIR / "samples" / "whatsapp_ai_test_video.mp4"
    case_mgr = CaseManager("TASK6-UI-TEST")

    print("\nRunning pipeline with CaseManager to generate artifacts...")
    signals, aud = analyze_video_pipeline(vid_path, caption="", case_manager=case_mgr)
    overall, findings = evaluate_rule_based_correlation(signals)

    # 1. OVERVIEW TAB DATA
    print("\n--- 1. OVERVIEW TAB VERIFICATION ---")
    
    # Check warning banner
    has_comp_warning = any("Compression may hide AI artifacts" in w for w in overall.warnings)
    print(f"Warning Banner Displayed: {has_comp_warning}")
    if has_comp_warning:
        print("  -> '⚠️ Compression may hide AI artifacts. A low result here is not reliable.'")

    # Top Reasons (strictly >= 0.35)
    scored = [s for s in signals if s.score is not None and s.score >= 0.35]
    scored.sort(key=lambda s: s.score, reverse=True)
    print(f"\nTop Reasons (strictly score >= 0.35, count: {len(scored)}):")
    for s in scored[:3]:
        first_sentence = s.evidence.split(". ")[0] + "."
        print(f"  * {s.name}: {first_sentence} (Score: {s.score:.2f})")

    # Checks that found nothing unusual / skipped
    unremarkable = [s for s in signals if s.score is None or s.score < 0.35]
    print(f"\nChecks that found nothing unusual (collapsed expander, count: {len(unremarkable)}):")
    for s in unremarkable:
        status_lbl = "SKIPPED" if "SKIPPED" in s.evidence else ("FAILED" if "FAILED" in s.evidence else "NORMAL")
        print(f"  * {s.name} [{status_lbl}]: {s.evidence[:65]}...")

    # Human checks for video
    human_checks = generate_recommended_human_checks(signals)
    print("\nRecommended Next Steps (Human OSINT Checklist):")
    for c in human_checks:
        print(f"  - {c}")

    # 2. VIDEO FORENSICS TAB DATA
    print("\n--- 2. VIDEO FORENSICS TAB VERIFICATION ---")

    # Signal Status Table
    print("Video Signal Status Table rows:")
    for s in signals:
        status = "SKIPPED" if "SKIPPED" in s.evidence else ("FAILED" if "FAILED" in s.evidence else "RAN")
        score_str = f"{s.score:.2f}" if s.score is not None else "--"
        print(f"  [{status:<7}] {s.name:<40} Score: {score_str}")

    # Chart artifact
    chart_file = case_mgr.artifacts_dir / f"frame_scores_{vid_path.stem}.png"
    print(f"\nKeyframe AI Probability Timeline Chart Artifact: {chart_file.name} exists: {chart_file.is_file()}")

    # Top 3 flagged keyframes JSON artifact
    json_file = case_mgr.artifacts_dir / f"frame_scores_{vid_path.stem}.json"
    print(f"Keyframe AI Scores JSON Artifact: {json_file.name} exists: {json_file.is_file()}")
    if json_file.is_file():
        records = json.loads(json_file.read_text(encoding="utf-8"))
        top3 = sorted(records, key=lambda r: r.get("score", 0.0), reverse=True)[:3]
        print("Top 3 Flagged Keyframes Gallery Data:")
        for r in top3:
            print(f"  * Frame #{r['index']} (t={r['timestamp']:.2f}s) | Score: {r['score']:.0%} | Face: {r['has_face']}")

    # Plain-English Format: What we saw / Why it matters / How sure we are
    print("\nPlain-English Video Signals Format:")
    for s in signals[:2]:
        ev_str = s.evidence
        if s.score and s.score >= 0.60:
            sureness = f"High suspicion (score {s.score:.2f}). Strongly indicates synthetic generation artifacts."
        elif s.score and s.score >= 0.35:
            sureness = f"Moderate suspicion (score {s.score:.2f}). Indicates potential synthesis or compression anomalies."
        elif s.score:
            sureness = f"Low suspicion (score {s.score:.2f}). No indicators found by this check."
        else:
            sureness = ev_str
        print(f"  Signal: {s.name}")
        print(f"   - What we saw:    {s.evidence[:70]}...")
        print(f"   - Why it matters: Evaluates video generation parameters.")
        print(f"   - How sure we are: {sureness}")

    print("\n" + "=" * 70)
    print("TASK 6 VERIFICATION COMPLETE")
    print("=" * 70)

if __name__ == "__main__":
    run_task6_verification()
