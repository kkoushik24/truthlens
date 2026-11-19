"""Integration and smoke tests for Streamlit App (Module 8)."""

import pytest
from pathlib import Path
from app import load_demo_case, run_cached_forensic_pipeline


SAMPLES_DIR = Path(__file__).resolve().parent.parent / "samples"
CLEAN_IMG = SAMPLES_DIR / "clean_photo.jpg"
NATURAL_AUD = SAMPLES_DIR / "synthetic_chord_test.wav"  # Signal-processing test only, not speech


def test_load_demo_cases():
    """Verify loading pre-computed cases from /demo_cases without errors."""
    # Test Case 1
    case1 = load_demo_case("case_01_spliced_photo_claim")
    assert case1["case_id"] == "DEMO-2026-ELEVATED"
    assert "report" in case1
    assert case1["report"]["overall_indicator"]["level"] == "elevated"
    assert len(case1["json_bytes"]) > 100
    assert len(case1["pdf_bytes"]) > 1000
    assert len(case1["artifacts"]) >= 1

    # Test Case 2
    case2 = load_demo_case("case_02_authentic_wildlife")
    assert case2["case_id"] == "DEMO-2026-AUTHENTIC"
    assert case2["report"]["overall_indicator"]["level"] in ["low", "moderate"]
    assert len(case2["json_bytes"]) > 100
    assert len(case2["pdf_bytes"]) > 1000
    assert len(case2["artifacts"]) >= 2


def test_run_cached_pipeline_end_to_end(tmp_path: Path):
    """Verify live analysis execution function runs end-to-end and returns expected structure."""
    img_bytes = CLEAN_IMG.read_bytes()
    aud_bytes = NATURAL_AUD.read_bytes()
    caption = "A quiet sunny afternoon in the park."

    result = run_cached_forensic_pipeline(
        input_hashes_key="test_smoke_key_123",
        image_bytes=img_bytes,
        image_name="test_clean.jpg",
        video_bytes=None,
        video_name=None,
        audio_bytes=aud_bytes,
        audio_name="test_audio.wav",
        caption_text=caption,
    )

    assert "report" in result
    assert "pdf_bytes" in result
    assert len(result["pdf_bytes"]) > 1000
    assert "json_bytes" in result
    assert len(result["json_bytes"]) > 100
    assert result["report"]["overall_indicator"]["level"] in ["low", "moderate", "elevated"]
    assert len(result["report"]["signals"]) >= 4
