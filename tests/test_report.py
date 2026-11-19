"""Unit and integration tests for Report Generation (Module 7)."""

import pytest
import json
from pathlib import Path

from core.case_manager import CaseManager
from core.schemas import (
    ForensicReport,
    Signal,
    CrossModalFinding,
    OverallIndicator,
    HistoryItem,
    RegionLocation,
)
from correlation.engine import correlate_forensic_signals
from report.json_exporter import export_report_to_json
from report.pdf_exporter import export_report_to_pdf
from report.generator import generate_forensic_report_bundle


SAMPLES_DIR = Path(__file__).resolve().parent.parent / "samples"
CLEAN_IMG = SAMPLES_DIR / "clean_photo.jpg"


@pytest.fixture
def sample_report():
    return ForensicReport(
        case_id="TEST-REPORT-001",
        inputs=["test_photo.jpg", "test_claim.txt"],
        input_hashes={
            "test_photo.jpg": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "test_claim.txt": "ca978112ca1bbdcafac231b39a23dc4da786eff8147c4e72b9807785afee48bb",
        },
        signals=[
            Signal(
                signal_id="img_exif_001",
                modality="image",
                name="EXIF Metadata Audit",
                score=0.75,
                evidence="Explicit editing tag: 'Adobe Photoshop 2024'.",
                limitation="Editing tags can indicate simple non-malicious cropping.",
                source_file="test_photo.jpg",
            ),
            Signal(
                signal_id="img_ela_001",
                modality="image",
                name="Error Level Analysis",
                score=0.82,
                evidence="Pronounced compression divergence in region [100, 50, 200, 150].",
                location=RegionLocation(bbox=[100, 50, 200, 150]),
                limitation="Sharp texture edges naturally exhibit higher ELA rates.",
                source_file="test_photo.jpg",
            ),
        ],
        cross_modal_findings=[
            CrossModalFinding(
                finding="Metadata editing signatures corroborate localized ELA compression divergence.",
                supporting_signals=["img_exif_001", "img_ela_001"],
                effect="strengthens",
            )
        ],
        overall_indicator=OverallIndicator(level="elevated", confidence=0.85),
        limitations=[
            "A detection score is an INDICATOR, never a definitive verdict.",
            "Social media uploads routinely strip metadata and recompress media.",
        ],
        recommended_human_checks=[
            "Perform reverse image search on Google Lens and TinEye.",
            "Request original uncompressed camera files.",
        ],
        history=[
            HistoryItem(time="2026-11-19T05:00:00Z", action="Case initialized."),
            HistoryItem(time="2026-11-19T05:00:05Z", action="Forensic analysis executed."),
        ],
    )


def test_export_report_to_json(tmp_path: Path, sample_report):
    """Verify that report exports to valid, conforming JSON."""
    json_out = tmp_path / "test_report.json"
    exported_path = export_report_to_json(sample_report, json_out)

    assert exported_path.is_file()
    assert exported_path.stat().st_size > 200

    # Read back and validate JSON structure
    with open(exported_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["case_id"] == "TEST-REPORT-001"
    assert "test_photo.jpg" in data["input_hashes"]
    assert len(data["signals"]) == 2
    assert data["overall_indicator"]["level"] == "elevated"
    assert data["overall_indicator"]["confidence"] == 0.85


def test_export_report_to_pdf(tmp_path: Path, sample_report):
    """Verify that report exports to a valid, well-structured PDF."""
    pdf_out = tmp_path / "test_report.pdf"
    exported_path = export_report_to_pdf(
        report=sample_report,
        output_path=pdf_out,
        artifact_images=[CLEAN_IMG],
        summary_text="Executive summary of forensic findings.",
    )

    assert exported_path.is_file()
    assert exported_path.stat().st_size > 2000

    # Verify standard PDF magic header
    with open(exported_path, "rb") as f:
        header = f.read(5)
    assert header == b"%PDF-"


def test_generate_forensic_report_bundle(tmp_path: Path, sample_report):
    """Verify generate_forensic_report_bundle integrates with CaseManager."""
    case_mgr = CaseManager("TEST-BUNDLE-001")
    # Save a dummy original to populate input hashes
    case_mgr.save_original("sample.jpg", b"FAKE IMAGE BYTES FOR REPORT TEST")

    corr_data = {
        "overall_indicator": sample_report.overall_indicator,
        "cross_modal_findings": sample_report.cross_modal_findings,
        "summary": "Full bundle summary text.",
        "limitations": sample_report.limitations,
        "recommended_human_checks": sample_report.recommended_human_checks,
    }

    report, json_p, pdf_p = generate_forensic_report_bundle(
        case_manager=case_mgr,
        signals=sample_report.signals,
        correlation_data=corr_data,
    )

    assert isinstance(report, ForensicReport)
    assert json_p.is_file()
    assert pdf_p.is_file()
    assert pdf_p.stat().st_size > 2000
    assert "report.pdf" in [h.action for h in case_mgr.history if "report.pdf" in h.action][0]
