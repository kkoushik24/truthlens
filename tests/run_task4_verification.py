import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from video_forensics.frame_sampler import sample_video_frames
from video_forensics.temporal_consistency import check_temporal_consistency
from video_forensics.video_metadata import analyze_video_metadata
from video_forensics.audio_extractor import extract_audio_from_video
from video_forensics.visual_plausibility import check_video_visual_plausibility, check_video_caption_alignment
from video_forensics.pipeline import analyze_video_pipeline

def run_task4_verification():
    print("=" * 70)
    print("TASK 4: OTHER VIDEO SIGNALS VERIFICATION")
    print("=" * 70)

    vid_whatsapp = BASE_DIR / "samples" / "whatsapp_ai_test_video.mp4"
    vid_sample = BASE_DIR / "samples" / "sample_video.mp4"

    # 1. Temporal Consistency
    print("\n1. Testing Temporal Consistency:")
    _, frames_wa = sample_video_frames(vid_whatsapp, max_frames=12)
    sig_temp_wa = check_temporal_consistency(frames_wa, vid_whatsapp.name)
    print(f"   [WhatsApp Video] Score: {sig_temp_wa.score}")
    print(f"   Evidence: {sig_temp_wa.evidence}")
    print(f"   Limitation: {sig_temp_wa.limitation}")

    _, frames_sample = sample_video_frames(vid_sample, max_frames=12)
    sig_temp_sample = check_temporal_consistency(frames_sample, vid_sample.name)
    print(f"\n   [Spliced Sample Video] Score: {sig_temp_sample.score}")
    print(f"   Evidence: {sig_temp_sample.evidence}")
    print(f"   Location: {sig_temp_sample.location}")

    # 2. Metadata Audit
    print("\n2. Testing Metadata Audit (max 0.35 cap):")
    sig_meta = analyze_video_metadata(vid_whatsapp)
    print(f"   Score: {sig_meta.score} (Max allowed: 0.35)")
    print(f"   Evidence: {sig_meta.evidence}")
    print(f"   Limitation: {sig_meta.limitation}")

    # 3. Audio Extraction
    print("\n3. Testing Audio Extraction from Video Container:")
    extracted_wav = BASE_DIR / "samples" / "_temp_task4_audio.wav"
    extracted_path = extract_audio_from_video(vid_whatsapp, extracted_wav)
    if extracted_path and extracted_path.is_file():
        print(f"   Audio extracted successfully: {extracted_path.name} ({extracted_path.stat().st_size} bytes)")
        extracted_path.unlink()
    else:
        print("   No audio track in container.")

    # 4. Caption Alignment: without caption
    print("\n4. Testing Caption Alignment (No caption provided):")
    sig_cap_none = check_video_caption_alignment(frames_wa, caption=None, source_file=vid_whatsapp.name)
    print(f"   Score: {sig_cap_none.score}")
    print(f"   Evidence: {sig_cap_none.evidence}")

    # 5. Visual Plausibility (with graceful offline/sandbox handling)
    print("\n5. Testing Visual Plausibility Inspection:")
    sig_plaus = check_video_visual_plausibility(frames_wa, None, vid_whatsapp.name)
    print(f"   Signal ID: {sig_plaus.signal_id}")
    print(f"   Score: {sig_plaus.score}")
    print(f"   Evidence: {sig_plaus.evidence}")

    # 6. Full Pipeline Integration
    print("\n6. Full Pipeline Signals Extraction:")
    signals, aud = analyze_video_pipeline(vid_whatsapp, caption="")
    for s in signals:
        score_disp = f"{s.score:.2f}" if s.score is not None else "--"
        print(f"   [{s.signal_id}] {s.name:<40} Score: {score_disp:<6} Evidence: {s.evidence[:70]}...")

    print("\n" + "=" * 70)
    print("TASK 4 VERIFICATION COMPLETE")
    print("=" * 70)

if __name__ == "__main__":
    run_task4_verification()
