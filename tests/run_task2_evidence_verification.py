"""Comprehensive verification for Task 2: Evidence Collection."""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import json
from text_analysis.evidence_collector import (
    collect_evidence_bundle,
    extract_image_metadata,
    extract_video_metadata,
    select_video_frames_for_evidence,
)


def verify_task_2():
    print("=" * 80)
    print("RUNNING TASK 2 EVIDENCE COLLECTION VERIFICATION")
    print("=" * 80)

    # 1. Image Case: walking_banana.png (No EXIF)
    print("\n--- TEST CASE 1: Image without EXIF (samples/walking_banana.png) ---")
    img_banana = PROJECT_ROOT / "samples" / "walking_banana.png"
    bundle1 = collect_evidence_bundle(media_path=img_banana, media_type="image")
    print(f"Status: {bundle1['status']}")
    print(f"Total Evidence Items: {len(bundle1['evidence_items'])}")
    for item in bundle1["evidence_items"]:
        print(f"  [{item['id']}] ({item['source']}) {item['text']}")

    assert bundle1["status"] == "COMPLETED", f"Expected COMPLETED, got {bundle1['status']}"
    assert any("Timestamp: missing" in item["text"] for item in bundle1["evidence_items"]), "Expected missing timestamp"
    assert any("GPS Coordinates: missing" in item["text"] for item in bundle1["evidence_items"]), "Expected missing GPS"
    assert any("banana" in item["text"].lower() for item in bundle1["evidence_items"]), "Expected banana in visual description"

    # 2. Image Case: clean_photo.jpg (Has Canon EXIF DateTime)
    print("\n--- TEST CASE 2: Image with EXIF DateTime & Camera (samples/clean_photo.jpg) ---")
    img_clean = PROJECT_ROOT / "samples" / "clean_photo.jpg"
    bundle2 = collect_evidence_bundle(media_path=img_clean, media_type="image")
    print(f"Status: {bundle2['status']}")
    print(f"Total Evidence Items: {len(bundle2['evidence_items'])}")
    for item in bundle2["evidence_items"]:
        print(f"  [{item['id']}] ({item['source']}) {item['text']}")

    assert bundle2["status"] == "COMPLETED"
    assert any("2024:05:12" in item["text"] for item in bundle2["evidence_items"]), "Expected EXIF timestamp 2024:05:12"
    assert any("Canon" in item["text"] for item in bundle2["evidence_items"]), "Expected Canon camera tag"

    # 3. Image Case: edited_photo.jpg (Has Photoshop & 2026 DateTime)
    print("\n--- TEST CASE 3: Image with Editing Software & DateTime (samples/edited_photo.jpg) ---")
    img_edited = PROJECT_ROOT / "samples" / "edited_photo.jpg"
    bundle3 = collect_evidence_bundle(media_path=img_edited, media_type="image")
    print(f"Status: {bundle3['status']}")
    print(f"Total Evidence Items: {len(bundle3['evidence_items'])}")
    for item in bundle3["evidence_items"]:
        print(f"  [{item['id']}] ({item['source']}) {item['text']}")

    assert bundle3["status"] == "COMPLETED"
    assert any("2026:01:01" in item["text"] for item in bundle3["evidence_items"]), "Expected EXIF timestamp 2026:01:01"
    assert any("Photoshop" in item["text"] for item in bundle3["evidence_items"]), "Expected Photoshop software tag"

    # 4. Video Case: sample_video.mp4 (Sampled Frames + Metadata + Transcript)
    print("\n--- TEST CASE 4: Video Evidence Bundle (samples/sample_video.mp4) ---")
    vid_path = PROJECT_ROOT / "samples" / "sample_video.mp4"
    bundle4 = collect_evidence_bundle(
        media_path=vid_path,
        media_type="video",
        transcript="Test spoken dialogue in video",
    )
    print(f"Status: {bundle4['status']}")
    print(f"Total Evidence Items: {len(bundle4['evidence_items'])}")
    for item in bundle4["evidence_items"]:
        print(f"  [{item['id']}] ({item['source']}) {item['text']}")

    assert bundle4["status"] == "COMPLETED"
    assert any(item["source"].startswith("frame_") for item in bundle4["evidence_items"]), "Expected frame sources"
    assert any(item["source"] == "transcript" for item in bundle4["evidence_items"]), "Expected transcript source"
    assert any(item["source"] == "metadata" for item in bundle4["evidence_items"]), "Expected metadata source"

    # 5. Audio Case: samples/1.wav (Transcript only + Audio Metadata)
    print("\n--- TEST CASE 5: Audio Evidence Bundle (samples/1.wav) ---")
    aud_path = PROJECT_ROOT / "samples" / "1.wav"
    bundle5 = collect_evidence_bundle(media_path=aud_path, media_type="audio", transcript="Hello world test audio")
    print(f"Status: {bundle5['status']}")
    print(f"Total Evidence Items: {len(bundle5['evidence_items'])}")
    for item in bundle5["evidence_items"]:
        print(f"  [{item['id']}] ({item['source']}) {item['text']}")

    assert bundle5["status"] == "COMPLETED"
    assert any(item["source"] == "transcript" for item in bundle5["evidence_items"]), "Expected transcript"
    assert any(item["source"] == "metadata" for item in bundle5["evidence_items"]), "Expected audio metadata"
    # Audio must NOT have visual frame evidence items
    assert not any(item["source"] in ["image", "frame_0"] for item in bundle5["evidence_items"]), "Audio must not have visual frames"

    # 6. Check Forbidden Words Rule:
    print("\n--- TEST CASE 6: Global Rules Compliance Check ---")
    for b_idx, b in enumerate([bundle1, bundle2, bundle3, bundle4, bundle5], 1):
        for item in b["evidence_items"]:
            lower_text = item["text"].lower()
            assert "natural" not in lower_text, f"Forbidden word 'natural' found in Bundle {b_idx} item {item['id']}: {item['text']}"
            assert "authentic" not in lower_text, f"Forbidden word 'authentic' found in Bundle {b_idx} item {item['id']}: {item['text']}"
    print("Verified: Forbidden words ('natural', 'authentic') do not appear in any evidence item text.")

    # 7. Check Video Frame Selector
    print("\n--- TEST CASE 7: Video Frame Selection logic ---")
    dummy_frames = [{"index": i, "timestamp": i * 0.5, "path": f"/dummy/frame_{i}.jpg"} for i in range(10)]
    dummy_scores = [{"frame_index": 7, "score": 0.95}, {"frame_index": 3, "score": 0.85}]
    chosen = select_video_frames_for_evidence(dummy_frames, per_frame_records=dummy_scores, min_frames=3, max_frames=5)
    chosen_indices = [f["index"] for f in chosen]
    print(f"10 frames with peak AI scores at frame 7 and 3 -> Chosen indices: {chosen_indices}")
    # Must include first (0), middle (5), last (9), and peak scores (7, 3)
    assert 0 in chosen_indices, "Must include first frame"
    assert 5 in chosen_indices, "Must include middle frame"
    assert 9 in chosen_indices, "Must include last frame"
    assert 7 in chosen_indices, "Must include top scoring frame 7"
    assert len(chosen_indices) <= 5, "Must not exceed max 5 frames"
    print("Frame selection algorithm verified successfully.")

    print("\n" + "=" * 80)
    print("ALL TASK 2 VERIFICATIONS PASSED SUCCESSFULLY!")
    print("=" * 80)


if __name__ == "__main__":
    verify_task_2()
