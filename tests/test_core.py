"""Unit tests for TruthLens Core Module (Module 1)."""

import pytest
from pathlib import Path
from pydantic import ValidationError

from core.schemas import (
    Signal,
    RegionLocation,
    TimeLocation,
    FrameLocation,
    CrossModalFinding,
    OverallIndicator,
    HistoryItem,
    ForensicReport,
    create_fallback_signal,
)
from core.hashing import calculate_sha256, calculate_bytes_sha256
from core.case_manager import CaseManager


def test_signal_schema_valid():
    """Verify valid signal creation with region location."""
    signal = Signal(
        signal_id="ela_001",
        modality="image",
        name="Error Level Analysis",
        score=0.85,
        evidence="High compression divergence detected in upper quadrant",
        location=RegionLocation(bbox=[10, 20, 150, 200]),
        limitation="ELA can flag high-frequency edges even in unedited images",
        source_file="sample.jpg",
    )
    assert signal.signal_id == "ela_001"
    assert signal.score == 0.85
    assert signal.location.type == "region"
    assert signal.location.bbox == [10, 20, 150, 200]


def test_signal_score_bounds_and_null():
    """Verify signal score must be between 0.0 and 1.0 or None."""
    # Score 0.0 is valid
    s0 = Signal(
        signal_id="sig_0",
        modality="text",
        name="Test",
        score=0.0,
        evidence="None",
        limitation="None",
        source_file="f.txt",
    )
    assert s0.score == 0.0

    # Score None is valid
    s_none = Signal(
        signal_id="sig_none",
        modality="video",
        name="Test",
        score=None,
        evidence="None",
        limitation="Test limit",
        source_file="f.mp4",
    )
    assert s_none.score is None

    # Score > 1.0 must fail
    with pytest.raises(ValidationError):
        Signal(
            signal_id="sig_invalid",
            modality="image",
            name="Test",
            score=1.5,
            evidence="Too high",
            limitation="Limit",
            source_file="f.jpg",
        )


def test_fallback_signal_helper():
    """Verify fallback helper creates safe null-score signals without raising errors."""
    fallback = create_fallback_signal(
        signal_id="ai_001",
        modality="image",
        name="AI Image Detector",
        source_file="test.png",
        reason="Model failed to load due to network timeout",
    )
    assert fallback.score is None
    assert "Model failed to load" in fallback.evidence
    assert fallback.limitation != ""


def test_hashing_consistency(tmp_path: Path):
    """Verify SHA-256 calculation for both byte streams and files."""
    test_data = b"TruthLens Forensic Integrity Test Data"
    expected_hash = "f3dfc8496c4ab2a8a27f04831c3c9e2bbbebf5f2d324b2acb322b64135a23ef0"

    # Test raw bytes hash
    byte_hash = calculate_bytes_sha256(test_data)
    assert byte_hash == expected_hash

    # Test file hash
    test_file = tmp_path / "test_file.bin"
    test_file.write_bytes(test_data)
    file_hash = calculate_sha256(test_file)
    assert file_hash == expected_hash


def test_case_manager_preserves_originals(tmp_path: Path):
    """Verify case manager saves immutable originals and logs history."""
    case_mgr = CaseManager(case_id="TEST-CASE-001")
    assert case_mgr.case_id == "TEST-CASE-001"
    assert len(case_mgr.history) >= 1

    sample_content = b"ORIGINAL IMAGE BYTES NEVER MODIFIED"
    saved_path = case_mgr.save_original("sample_photo.jpg", sample_content)

    assert saved_path.exists()
    assert saved_path.read_bytes() == sample_content
    assert "sample_photo.jpg" in case_mgr.input_hashes
    assert len(case_mgr.history) == 2


def test_forensic_report_schema():
    """Verify full report schema validation."""
    report = ForensicReport(
        case_id="CASE-20261119-ABCDEF",
        inputs=["photo.jpg"],
        input_hashes={"photo.jpg": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"},
        signals=[
            Signal(
                signal_id="exif_001",
                modality="image",
                name="EXIF Analysis",
                score=0.2,
                evidence="Camera metadata intact",
                limitation="EXIF can be easily forged or stripped",
                source_file="photo.jpg",
            )
        ],
        cross_modal_findings=[
            CrossModalFinding(
                finding="Metadata confirms camera timestamps match caption claims",
                supporting_signals=["exif_001"],
                effect="weakens",
            )
        ],
        overall_indicator=OverallIndicator(level="low", confidence=0.85),
        limitations=["Analysis based on single image without raw sensor files."],
        recommended_human_checks=["Perform reverse image search."],
        history=[
            HistoryItem(time="2026-11-19T03:30:00Z", action="Case initialized")
        ],
    )
    assert report.case_id == "CASE-20261119-ABCDEF"
    assert report.overall_indicator.level == "low"
    assert report.overall_indicator.confidence == 0.85
