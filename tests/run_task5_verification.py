import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core.schemas import Signal, FrameLocation
from correlation.rules_engine import evaluate_rule_based_correlation
from video_forensics.pipeline import analyze_video_pipeline

def run_task5_verification():
    print("=" * 70)
    print("TASK 5: VIDEO COMBINER & CONFIDENCE RULES VERIFICATION")
    print("=" * 70)

    # Rule 1: Positive evidence rule & Floor Rule 1 (AI >= 0.50 -> at least MODERATE)
    print("\n1. Testing Floor Rule 1 (AI detector >= 0.50 forces MODERATE even if others are ~0):")
    sigs_r1 = [
        Signal(signal_id="vid_ai_001", modality="video", name="Video Keyframe AI Detection", score=0.52, evidence="Keyframe #21 shows AI textures (score: 52%)", limitation="test", source_file="clip.mp4"),
        Signal(signal_id="vid_temp_001", modality="video", name="Video Temporal Consistency", score=0.02, evidence="Transitions smooth", limitation="test", source_file="clip.mp4"),
        Signal(signal_id="vid_meta_001", modality="video", name="Video Metadata", score=0.05, evidence="Clean", limitation="test", source_file="clip.mp4"),
    ]
    ov1, _ = evaluate_rule_based_correlation(sigs_r1)
    print(f"   Level: {ov1.level} (Expected: moderate)")
    print(f"   Primary Drivers: {ov1.primary_drivers} (vid_ai_001 prioritized at index 0)")
    assert ov1.level in ["moderate", "elevated"]
    assert ov1.primary_drivers[0] == "vid_ai_001"

    # Rule 2: Floor Rule 2 (Impossible elements -> at least MODERATE)
    print("\n2. Testing Floor Rule 2 (Visual plausibility impossible elements forces MODERATE):")
    sigs_r2 = [
        Signal(signal_id="vid_plaus_001", modality="video", name="Video Visual Plausibility & Physics Audit", score=0.75, evidence="Physical impossibilities: surreal lighting and extra fingers.", limitation="test", source_file="clip.mp4"),
        Signal(signal_id="vid_temp_001", modality="video", name="Video Temporal Consistency", score=0.02, evidence="Transitions smooth", limitation="test", source_file="clip.mp4"),
        Signal(signal_id="vid_meta_001", modality="video", name="Video Metadata", score=0.05, evidence="Clean", limitation="test", source_file="clip.mp4"),
    ]
    ov2, _ = evaluate_rule_based_correlation(sigs_r2)
    print(f"   Level: {ov2.level} (Expected: moderate)")
    assert ov2.level in ["moderate", "elevated"]

    # Rule 3: Floor Rule 3 (Two independent signals >= 0.60 -> ELEVATED)
    print("\n3. Testing Floor Rule 3 (Two independent signals >= 0.60 forces ELEVATED):")
    sigs_r3 = [
        Signal(signal_id="vid_ai_001", modality="video", name="Video Keyframe AI Detection", score=0.65, evidence="AI textures detected", limitation="test", source_file="clip.mp4"),
        Signal(signal_id="vid_plaus_001", modality="video", name="Video Visual Plausibility & Physics Audit", score=0.68, evidence="Impossible anatomy", limitation="test", source_file="clip.mp4"),
        Signal(signal_id="vid_temp_001", modality="video", name="Video Temporal Consistency", score=0.10, evidence="Transitions smooth", limitation="test", source_file="clip.mp4"),
    ]
    ov3, _ = evaluate_rule_based_correlation(sigs_r3)
    print(f"   Level: {ov3.level} (Expected: elevated)")
    assert ov3.level == "elevated"

    # Rule 4: Contradiction Check (prevents LOW if positive indicators exist)
    print("\n4. Testing Contradiction Check:")
    sigs_r4 = [
        Signal(signal_id="vid_ai_001", modality="video", name="Video Keyframe AI Detection", score=0.88, evidence="Keyframe #21 shows visual textures commonly produced by generative AI systems", limitation="test", source_file="clip.mp4"),
        Signal(signal_id="vid_temp_001", modality="video", name="Video Temporal Consistency", score=0.01, evidence="Transitions continuous", limitation="test", source_file="clip.mp4"),
        Signal(signal_id="vid_meta_001", modality="video", name="Video Metadata", score=0.01, evidence="Metadata clean", limitation="test", source_file="clip.mp4"),
        Signal(signal_id="vid_ela_001", modality="video", name="Video ELA", score=0.05, evidence="Normal compression", limitation="test", source_file="clip.mp4"),
    ]
    ov4, _ = evaluate_rule_based_correlation(sigs_r4)
    print(f"   Level: {ov4.level} (Expected: moderate or elevated, never low)")
    assert ov4.level != "low"

    # Rule 5: Confidence Penalties & Explanations
    print("\n5. Testing Confidence Reductions & Explanations:")
    sigs_r5 = [
        Signal(signal_id="vid_ai_001", modality="video", name="Video Keyframe AI Detection", score=0.85, evidence="AI textures found", limitation="test", source_file="whatsapp_clip.mp4"),
        Signal(signal_id="vid_temp_001", modality="video", name="Video Temporal Consistency", score=0.10, evidence="Transitions smooth", limitation="test", source_file="whatsapp_clip.mp4"),
        Signal(signal_id="vid_meta_001", modality="video", name="Video Container & Codec Metadata", score=0.25, evidence="No explicit container encoder tag found (metadata stripped). Bitrate: 900 kb/s.", limitation="test", source_file="whatsapp_clip.mp4"),
    ]
    ov5, _ = evaluate_rule_based_correlation(sigs_r5)
    print(f"   Confidence: {ov5.confidence:.2f} (Base: 0.85, Penalties applied: -0.15 missing plaus, -0.15 divergence, -0.10 compression)")
    print("   Warnings / Logged Reductions:")
    for w in ov5.warnings:
        print(f"    - {w}")
    assert ov5.confidence <= 0.55

    # 6. Evaluation on the Known Test Case: WhatsApp Video
    print("\n6. Evaluating on Known Test Case (samples/whatsapp_ai_test_video.mp4):")
    vid_path = BASE_DIR / "samples" / "whatsapp_ai_test_video.mp4"
    signals, aud = analyze_video_pipeline(vid_path, caption="")
    overall, findings = evaluate_rule_based_correlation(signals)
    print(f"   Final Overall Indicator Level: {overall.level.upper()}")
    print(f"   Assessed Confidence:          {overall.confidence:.0%}")
    print(f"   Primary Drivers:              {overall.primary_drivers}")
    print("   Warnings:")
    for w in overall.warnings:
        print(f"    - {w}")

    print("\n" + "=" * 70)
    print("TASK 5 VERIFICATION COMPLETE: ZERO FAILURES")
    print("=" * 70)

if __name__ == "__main__":
    run_task5_verification()
