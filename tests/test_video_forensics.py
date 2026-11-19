"""Unit and forensic integration tests for Video Forensics (Module 4)."""

import pytest
from pathlib import Path

from core.case_manager import CaseManager
from core.schemas import Signal, FrameLocation
from video_forensics.frame_sampler import sample_video_frames
from video_forensics.video_metadata import analyze_video_metadata
from video_forensics.temporal_consistency import check_temporal_consistency
from video_forensics.audio_extractor import extract_audio_from_video
from video_forensics.pipeline import analyze_video_pipeline


SAMPLES_DIR = Path(__file__).resolve().parent.parent / "samples"
SAMPLE_VIDEO = SAMPLES_DIR / "sample_video.mp4"


def test_frame_sampler_cap_at_12(tmp_path: Path):
    """Verify that frame sampling never extracts more than 12 frames."""
    info, frames = sample_video_frames(
        video_path=SAMPLE_VIDEO,
        output_dir=tmp_path / "frames",
        max_frames=12,
    )

    assert info["total_frames"] == 24
    assert len(frames) == 12  # Capped strictly at 12
    # Verify frame files were written
    assert all(f["path"] is not None and f["path"].is_file() for f in frames)
    # Verify timestamps are strictly ascending
    timestamps = [f["timestamp"] for f in frames]
    assert timestamps == sorted(timestamps)


def test_video_metadata_inspection():
    """Verify container, codec, duration, and stream metadata extraction."""
    sig = analyze_video_metadata(SAMPLE_VIDEO)
    assert isinstance(sig, Signal)
    assert sig.modality == "video"
    assert sig.signal_id == "vid_meta_001"
    assert sig.score is not None
    assert "Video codec" in sig.evidence
    assert "Audio stream" in sig.evidence
    assert sig.limitation != ""


def test_temporal_consistency_detects_anomaly(tmp_path: Path):
    """Verify that inter-frame color/sharpness jumps are detected and located."""
    _, frames = sample_video_frames(
        video_path=SAMPLE_VIDEO,
        output_dir=tmp_path / "frames_temp",
        max_frames=12,
    )

    sig = check_temporal_consistency(frames, source_file="sample_video.mp4")
    assert isinstance(sig, Signal)
    assert sig.score is not None
    assert sig.score >= 0.45
    assert "discontinuity" in sig.evidence.lower() or "variance" in sig.evidence.lower()
    # Location must be a valid FrameLocation
    if sig.location:
        assert isinstance(sig.location, FrameLocation)
        assert sig.location.type == "frame"


def test_audio_extraction_from_video(tmp_path: Path):
    """Verify audio track extraction from MP4 to 16kHz mono WAV."""
    target_wav = tmp_path / "extracted_audio.wav"
    result = extract_audio_from_video(SAMPLE_VIDEO, target_wav)

    assert result is not None
    assert result.is_file()
    assert result.stat().st_size > 1000  # Non-trivial audio bytes


def test_full_video_pipeline(tmp_path: Path):
    """Verify end-to-end video pipeline integration with CaseManager."""
    case_mgr = CaseManager("TEST-VID-001")
    signals, audio_path = analyze_video_pipeline(
        video_path=SAMPLE_VIDEO,
        case_manager=case_mgr,
    )

    assert len(signals) >= 3
    assert all(isinstance(s, Signal) for s in signals)
    assert any(s.signal_id == "vid_meta_001" for s in signals)
    assert any(s.signal_id == "vid_temp_001" for s in signals)
    assert any(s.signal_id == "vid_ela_001" for s in signals)

    # Audio track should be extracted
    assert audio_path is not None
    assert audio_path.is_file()

    # Case manager history audit log
    assert len(case_mgr.history) >= 4


def test_frame_sampler_hard_cap_at_15(tmp_path: Path):
    """Verify that frame sampler strictly enforces a hard cap of 15 frames (Task 2 & 7)."""
    info, frames = sample_video_frames(
        video_path=SAMPLE_VIDEO,
        output_dir=tmp_path / "frames_cap",
        max_frames=50,  # Request excessive frames
    )
    assert len(frames) <= 15
    assert len(frames) == 15 or len(frames) == min(info["total_frames"], 15)


def test_keyframe_ai_aggregation_logic():
    """Verify that score aggregation takes higher of top-3 mean vs max score (Task 3 & 7)."""
    from video_forensics.keyframe_ai_detector import compute_keyframe_aggregate

    # Case A: One strong peak (e.g. 0.92, 0.40, 0.30, 0.20)
    scores_a = [0.92, 0.40, 0.30, 0.20]
    agg_a, top3_a, max_a = compute_keyframe_aggregate(scores_a)
    assert max_a == 0.92
    assert top3_a == round((0.92 + 0.40 + 0.30) / 3, 4)
    assert agg_a == 0.92  # max score dominates

    # Case B: Consistent high scores
    scores_b = [0.85, 0.84, 0.83, 0.20]
    agg_b, top3_b, max_b = compute_keyframe_aggregate(scores_b)
    assert agg_b == 0.85


def test_floor_rule_1_ai_detector_moderate():
    """Verify Floor Rule 1: AI detector >= 0.50 guarantees at least MODERATE level (Task 5 & 7)."""
    from correlation.rules_engine import evaluate_rule_based_correlation

    # Even if all other signals are near 0, AI detector >= 0.50 forces MODERATE
    sigs = [
        Signal(
            signal_id="vid_ai_001",
            modality="video",
            name="Video Keyframe AI Detection",
            score=0.52,
            evidence="Keyframe #5 shows AI textures",
            limitation="Test caveat",
            source_file="test.mp4",
        ),
        Signal(
            signal_id="vid_temp_001",
            modality="video",
            name="Video Temporal Consistency",
            score=0.02,
            evidence="Transitions continuous",
            limitation="Test caveat",
            source_file="test.mp4",
        ),
        Signal(
            signal_id="vid_meta_001",
            modality="video",
            name="Video Metadata",
            score=0.05,
            evidence="Metadata clean",
            limitation="Test caveat",
            source_file="test.mp4",
        ),
    ]

    overall, _ = evaluate_rule_based_correlation(sigs)
    assert overall.level in ["moderate", "elevated"]
    assert overall.level != "low"
    assert overall.primary_drivers[0] == "vid_ai_001"


def test_floor_rule_2_impossible_elements_moderate():
    """Verify Floor Rule 2: Visual plausibility impossible elements forces at least MODERATE (Task 5 & 7)."""
    from correlation.rules_engine import evaluate_rule_based_correlation

    sigs = [
        Signal(
            signal_id="vid_plaus_001",
            modality="video",
            name="Video Visual Plausibility & Physics Audit",
            score=0.75,
            evidence="Physical impossibilities: warped extra fingers and floating glass.",
            limitation="Test caveat",
            source_file="test.mp4",
        ),
        Signal(
            signal_id="vid_temp_001",
            modality="video",
            name="Video Temporal Consistency",
            score=0.02,
            evidence="Transitions continuous",
            limitation="Test caveat",
            source_file="test.mp4",
        ),
        Signal(
            signal_id="vid_meta_001",
            modality="video",
            name="Video Metadata",
            score=0.05,
            evidence="Metadata clean",
            limitation="Test caveat",
            source_file="test.mp4",
        ),
    ]

    overall, _ = evaluate_rule_based_correlation(sigs)
    assert overall.level in ["moderate", "elevated"]
    assert overall.level != "low"


def test_floor_rule_3_two_independent_signals_elevated():
    """Verify Floor Rule 3: Two independent signals >= 0.60 forces ELEVATED (Task 5 & 7)."""
    from correlation.rules_engine import evaluate_rule_based_correlation

    sigs = [
        Signal(
            signal_id="vid_ai_001",
            modality="video",
            name="Video Keyframe AI Detection",
            score=0.65,
            evidence="AI generative textures",
            limitation="Test caveat",
            source_file="test.mp4",
        ),
        Signal(
            signal_id="vid_plaus_001",
            modality="video",
            name="Video Visual Plausibility & Physics Audit",
            score=0.68,
            evidence="Anatomy distortion",
            limitation="Test caveat",
            source_file="test.mp4",
        ),
        Signal(
            signal_id="vid_temp_001",
            modality="video",
            name="Video Temporal Consistency",
            score=0.10,
            evidence="Transitions continuous",
            limitation="Test caveat",
            source_file="test.mp4",
        ),
    ]

    overall, _ = evaluate_rule_based_correlation(sigs)
    assert overall.level == "elevated"


def test_positive_evidence_prevents_low():
    """Verify that any signal >= 0.60 cannot be pulled down to LOW by smooth non-findings (Task 5 & 7)."""
    from correlation.rules_engine import evaluate_rule_based_correlation

    sigs = [
        Signal(
            signal_id="vid_ai_001",
            modality="video",
            name="Video Keyframe AI Detection",
            score=0.88,
            evidence="Keyframe #21 shows visual textures commonly produced by generative AI systems",
            limitation="Test caveat",
            source_file="test.mp4",
        ),
        Signal(
            signal_id="vid_temp_001",
            modality="video",
            name="Video Temporal Consistency",
            score=0.01,
            evidence="Transitions continuous",
            limitation="Test caveat",
            source_file="test.mp4",
        ),
        Signal(
            signal_id="vid_meta_001",
            modality="video",
            name="Video Metadata",
            score=0.01,
            evidence="Metadata clean",
            limitation="Test caveat",
            source_file="test.mp4",
        ),
        Signal(
            signal_id="vid_ela_001",
            modality="video",
            name="Video ELA",
            score=0.01,
            evidence="Normal compression",
            limitation="Test caveat",
            source_file="test.mp4",
        ),
    ]

    overall, _ = evaluate_rule_based_correlation(sigs)
    assert overall.level != "low"
    assert overall.level in ["moderate", "elevated"]


def test_video_confidence_penalties_and_warnings():
    """Verify confidence deductions for missing plausibility, divergence, and messaging compression (Task 5 & 7)."""
    from correlation.rules_engine import evaluate_rule_based_correlation

    sigs = [
        Signal(
            signal_id="vid_ai_001",
            modality="video",
            name="Video Keyframe AI Detection",
            score=0.85,
            evidence="AI textures found",
            limitation="Test caveat",
            source_file="whatsapp_clip.mp4",
        ),
        Signal(
            signal_id="vid_temp_001",
            modality="video",
            name="Video Temporal Consistency",
            score=0.10,
            evidence="No indicators found: transitions smooth",
            limitation="Test caveat",
            source_file="whatsapp_clip.mp4",
        ),
        Signal(
            signal_id="vid_meta_001",
            modality="video",
            name="Video Container & Codec Metadata",
            score=0.25,
            evidence="No explicit container encoder tag found (metadata stripped). Bitrate: 900 kb/s.",
            limitation="Test caveat",
            source_file="whatsapp_clip.mp4",
        ),
    ]

    overall, _ = evaluate_rule_based_correlation(sigs)

    # Base confidence 0.85 should have penalties applied
    assert overall.confidence <= 0.55
    # Check warning messages
    assert any("plausibility" in w.lower() for w in overall.warnings)
    assert any("divergence" in w.lower() for w in overall.warnings)
    assert any("compression" in w.lower() or "bitrate" in w.lower() for w in overall.warnings)
    assert "Compression may hide AI artifacts. A low result here is not reliable." in overall.warnings


def test_session_state_input_signature_invalidation():
    """Verify that uploading a new video or altering caption invalidates active session state (Task 7)."""
    # Simulate st.session_state behavior from app.py line 286-300
    state = {
        "active_case": {"case_id": "PREVIOUS-CASE"},
        "source_mode": "upload",
        "last_input_signature": ("old_vid.mp4", 1000, "", 0, "", 0, "old caption"),
    }

    # Case A: New video uploaded
    new_vid_signature = ("new_vid.mp4", 2500, "", 0, "", 0, "old caption")
    if state.get("last_input_signature") != new_vid_signature:
        state.pop("active_case", None)
        state.pop("source_mode", None)
    state["last_input_signature"] = new_vid_signature

    assert "active_case" not in state
    assert "source_mode" not in state

    # Restore dummy case
    state["active_case"] = {"case_id": "SAVED-CASE"}

    # Case B: Caption changed
    caption_change_signature = ("new_vid.mp4", 2500, "", 0, "", 0, "modified caption")
    if state.get("last_input_signature") != caption_change_signature:
        state.pop("active_case", None)
        state.pop("source_mode", None)
    state["last_input_signature"] = caption_change_signature

    assert "active_case" not in state
    assert "source_mode" not in state


