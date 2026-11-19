"""Unit and forensic integration tests for Cross-Modal Correlation (Module 6)."""

import pytest
from core.case_manager import CaseManager
from core.schemas import Signal, RegionLocation, FrameLocation
from correlation.rules_engine import evaluate_rule_based_correlation
from correlation.llm_correlator import synthesize_llm_correlation
from correlation.human_checks import generate_system_limitations, generate_recommended_human_checks
from correlation.engine import correlate_forensic_signals


@pytest.fixture
def clean_signals():
    return [
        Signal(
            signal_id="img_exif_001",
            modality="image",
            name="EXIF Metadata Audit",
            score=0.10,
            evidence="Camera hardware identified: Canon EOS 80D.",
            limitation="EXIF can be easily forged or stripped.",
            source_file="clean.jpg",
        ),
        Signal(
            signal_id="img_ela_001",
            modality="image",
            name="Error Level Analysis",
            score=0.15,
            evidence="Uniform compression error across all quadrants.",
            limitation="High-frequency textures can elevate ELA.",
            source_file="clean.jpg",
        ),
        Signal(
            signal_id="txt_heur_001",
            modality="text",
            name="Caption Linguistic Integrity",
            score=0.15,
            evidence="Neutral descriptive phrasing without absolute markers.",
            limitation="Linguistic tests cannot verify real-world truth.",
            source_file="caption.txt",
        ),
    ]


@pytest.fixture
def elevated_spliced_signals():
    return [
        Signal(
            signal_id="img_exif_001",
            modality="image",
            name="EXIF Metadata Audit",
            score=0.75,
            evidence="Software tag explicitly records: 'Adobe Photoshop 2024'.",
            limitation="Editing tags can indicate simple cropping.",
            source_file="edited.jpg",
        ),
        Signal(
            signal_id="img_ela_001",
            modality="image",
            name="Error Level Analysis",
            score=0.82,
            evidence="Pronounced compression divergence flagged in region [200, 20, 300, 100].",
            location=RegionLocation(bbox=[200, 20, 300, 100]),
            limitation="Sharp edges produce high ELA variance.",
            source_file="edited.jpg",
        ),
        Signal(
            signal_id="txt_vis_match_001",
            modality="text",
            name="Caption-Image Visual Alignment",
            score=0.85,
            evidence="Caption claims 2024 protest, but visual scene features 2012 vehicles.",
            limitation="Vision models may misread text or context.",
            source_file="caption.txt",
        ),
    ]


def test_clean_signals_produce_low_indicator(clean_signals):
    """Verify consistent clean signals evaluate to 'low' indicator level."""
    indicator, findings = evaluate_rule_based_correlation(clean_signals)
    assert indicator.level == "low"
    assert indicator.confidence >= 0.50
    assert len(findings) >= 1
    assert any(f.effect == "weakens" for f in findings)


def test_compounding_elevated_signals(elevated_spliced_signals):
    """Verify cross-modal image + text indicators compound to 'elevated' indicator level."""
    indicator, findings = evaluate_rule_based_correlation(elevated_spliced_signals)
    assert indicator.level == "elevated"
    assert indicator.confidence >= 0.70
    assert len(findings) >= 1

    # Verify supporting signals citation and strengthening effect
    strengthen_findings = [f for f in findings if f.effect == "strengthens"]
    assert len(strengthen_findings) >= 1
    cited_ids = set()
    for f in strengthen_findings:
        cited_ids.update(f.supporting_signals)
    assert "img_ela_001" in cited_ids or "txt_vis_match_001" in cited_ids


def test_fallback_with_null_scores():
    """Verify graceful handling when some signals failed and produced null scores."""
    mixed_signals = [
        Signal(
            signal_id="img_exif_001",
            modality="image",
            name="EXIF Metadata Audit",
            score=0.75,
            evidence="Photoshop detected",
            limitation="Limit",
            source_file="f.jpg",
        ),
        Signal(
            signal_id="img_ai_001",
            modality="image",
            name="AI Detector",
            score=None,
            evidence="Offline model skipped",
            limitation="Offline",
            source_file="f.jpg",
        ),
    ]
    indicator, findings = evaluate_rule_based_correlation(mixed_signals)
    assert indicator.level in ["low", "moderate", "elevated"]
    assert 0.0 <= indicator.confidence <= 1.0


def test_human_checks_and_limitations(elevated_spliced_signals):
    """Verify system limitations and OSINT human verification recommendations are generated."""
    limits = generate_system_limitations(elevated_spliced_signals)
    checks = generate_recommended_human_checks(elevated_spliced_signals)

    assert len(limits) >= 4
    assert any("INDICATOR" in l for l in limits)

    assert len(checks) >= 4
    assert any("Reverse Image" in c for c in checks)
    assert any("RAW" in c for c in checks)


def test_full_correlation_coordinator(elevated_spliced_signals):
    """Verify end-to-end correlation engine orchestration with CaseManager."""
    case_mgr = CaseManager("TEST-CORR-001")
    result = correlate_forensic_signals(
        signals=elevated_spliced_signals,
        inputs=["edited.jpg", "caption.txt"],
        case_manager=case_mgr,
    )

    assert "overall_indicator" in result
    assert result["overall_indicator"].level == "elevated"
    assert "cross_modal_findings" in result
    assert len(result["cross_modal_findings"]) >= 1
    assert "summary" in result
    assert "limitations" in result
    assert "recommended_human_checks" in result
    assert len(case_mgr.history) >= 2
