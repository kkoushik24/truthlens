"""Unit and forensic integration tests for Image Forensics (Module 2)."""

import pytest
from pathlib import Path
from PIL import Image

from core.case_manager import CaseManager
from core.schemas import Signal, RegionLocation
from image_forensics.exif_analyzer import analyze_exif
from image_forensics.ela_analyzer import perform_ela
from image_forensics.ai_detector import detect_ai_generated_image
from image_forensics.pipeline import analyze_image_pipeline


SAMPLES_DIR = Path(__file__).resolve().parent.parent / "samples"
CLEAN_IMG = SAMPLES_DIR / "clean_photo.jpg"
STRIPPED_IMG = SAMPLES_DIR / "stripped_photo.jpg"
EDITED_IMG = SAMPLES_DIR / "edited_photo.jpg"


def test_exif_clean_photo():
    """Verify clean camera EXIF metadata extraction and low suspicion score."""
    sig = analyze_exif(CLEAN_IMG)
    assert isinstance(sig, Signal)
    assert sig.modality == "image"
    assert sig.signal_id == "img_exif_001"
    assert sig.score is not None
    assert sig.score <= 0.2
    assert "Canon" in sig.evidence
    assert sig.limitation != ""


def test_exif_stripped_photo():
    """Verify stripped EXIF produces moderate score with explanatory caveat."""
    sig = analyze_exif(STRIPPED_IMG)
    assert isinstance(sig, Signal)
    assert sig.score == 0.35
    assert "completely absent" in sig.evidence
    assert "strip" in sig.limitation


def test_exif_edited_photo():
    """Verify editing software signature detection produces elevated suspicion score."""
    sig = analyze_exif(EDITED_IMG)
    assert isinstance(sig, Signal)
    assert sig.score is not None
    assert sig.score >= 0.70
    assert "Photoshop" in sig.evidence


def test_ela_analysis_and_heatmap(tmp_path: Path):
    """Verify ELA execution, bbox detection, and heatmap generation."""
    heatmap_out = tmp_path / "test_heatmap.png"
    sig, artifact = perform_ela(EDITED_IMG, artifact_output_path=heatmap_out)

    assert isinstance(sig, Signal)
    assert sig.modality == "image"
    assert sig.signal_id == "img_ela_001"
    assert sig.score is not None
    assert sig.score >= 0.30

    # Verify bounding box format [x1, y1, x2, y2]
    assert sig.location is not None
    assert isinstance(sig.location, RegionLocation)
    assert len(sig.location.bbox) == 4
    x1, y1, x2, y2 = sig.location.bbox
    assert 0 <= x1 < x2 <= 320
    assert 0 <= y1 < y2 <= 240

    # Verify heatmap artifact was saved and is a valid image
    assert artifact is not None
    assert heatmap_out.exists()
    with Image.open(heatmap_out) as img:
        assert img.size == (320, 240)


def test_ai_detector_fail_safe():
    """Verify AI detector returns valid signal and never raises an unhandled exception."""
    sig = detect_ai_generated_image(CLEAN_IMG, model_name="non-existent/dummy-model-test")
    assert isinstance(sig, Signal)
    assert sig.modality == "image"
    # Fallback must set score to None with explanation
    assert sig.score is None
    assert "failed" in sig.evidence.lower() or "skipped" in sig.evidence.lower()
    assert len(sig.limitation) > 10


def test_full_image_pipeline_with_case_manager(tmp_path: Path):
    """Verify end-to-end image pipeline with CaseManager integration."""
    case_mgr = CaseManager("TEST-IMG-001")
    signals = analyze_image_pipeline(EDITED_IMG, case_manager=case_mgr)

    assert len(signals) == 3
    assert all(isinstance(s, Signal) for s in signals)
    assert any(s.signal_id == "img_exif_001" for s in signals)
    assert any(s.signal_id == "img_ela_001" for s in signals)
    assert any(s.signal_id == "img_ai_001" for s in signals)

    # Check that artifact was created in case artifacts
    heatmap_artifact = case_mgr.get_artifact_path("ela_heatmap_edited_photo.png")
    assert heatmap_artifact.exists()
    assert len(case_mgr.history) >= 3
