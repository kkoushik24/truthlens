import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from video_forensics.frame_sampler import sample_video_frames
from video_forensics.keyframe_ai_detector import analyze_video_frames_ai, compute_keyframe_aggregate

def run_task3_verification():
    print("=" * 70)
    print("TASK 3: PER-FRAME AI DETECTION VERIFICATION")
    print("=" * 70)

    # 1. Verification of Aggregation Logic
    print("\n1. Testing Score Aggregation Logic (Higher of top-3 mean vs max score):")
    sample_scores_a = [0.92, 0.40, 0.30, 0.20]
    agg_a, top3_a, max_a = compute_keyframe_aggregate(sample_scores_a)
    print(f"   Scores: {sample_scores_a}")
    print(f"   -> Top-3 Mean: {top3_a:.4f}, Max Score: {max_a:.4f} => Aggregated: {agg_a:.4f}")

    sample_scores_b = [0.85, 0.84, 0.83, 0.20]
    agg_b, top3_b, max_b = compute_keyframe_aggregate(sample_scores_b)
    print(f"   Scores: {sample_scores_b}")
    print(f"   -> Top-3 Mean: {top3_b:.4f}, Max Score: {max_b:.4f} => Aggregated: {agg_b:.4f}")

    # 2. Run Per-Frame AI Detection on WhatsApp test video
    vid_path = BASE_DIR / "samples" / "whatsapp_ai_test_video.mp4"
    print(f"\n2. Evaluating Keyframes of {vid_path.name} with AI Image Detector:")
    
    info, sampled_frames = sample_video_frames(vid_path, max_frames=12)
    print(f"   Extracted {len(sampled_frames)} frames across {info['duration_seconds']}s")

    signal, records = analyze_video_frames_ai(sampled_frames, source_file=vid_path.name)

    print("\n   Per-Frame AI Detection Records (all sampled frames):")
    print(f"   {'Index':<8} {'Timestamp':<12} {'AI Score':<12} {'Face Detected':<15}")
    print("   " + "-" * 50)
    for r in sorted(records, key=lambda x: x['index']):
        print(f"   #{r['index']:<7} {r['timestamp']:<11.2f}s {r['score']:<11.4f} {str(r['has_face']):<15}")

    print("\n3. Generated Signal Output:")
    print(f"   Signal ID:  {signal.signal_id}")
    print(f"   Modality:   {signal.modality}")
    print(f"   Name:       {signal.name}")
    print(f"   Score:      {signal.score}")
    print(f"   Location:   {signal.location}")
    print(f"   Evidence:   {signal.evidence}")
    print(f"   Limitation: {signal.limitation}")

    print("\n" + "=" * 70)
    print("TASK 3 VERIFICATION COMPLETE")
    print("=" * 70)

if __name__ == "__main__":
    run_task3_verification()
