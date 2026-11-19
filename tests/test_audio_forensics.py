"""Unit and forensic integration tests for Audio Forensics (Module 5)."""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import pytest

from core.case_manager import CaseManager
from core.schemas import Signal, TimeLocation
from audio_forensics.audio_loader import load_and_preprocess_audio, create_audio_metadata_signal
from audio_forensics.heuristics import (
    analyze_high_frequency_cutoff,
    analyze_spectral_flatness_and_noise_floor,
    analyze_pitch_and_prosody,
    analyze_silence_and_breath_patterns,
)
from audio_forensics.spectral_analyzer import analyze_audio_spectrum
from audio_forensics.voice_detector import classify_synthetic_voice
from audio_forensics.transcriber import compare_transcript_to_caption
from audio_forensics.pipeline import analyze_audio_pipeline
from correlation.rules_engine import evaluate_rule_based_correlation


SAMPLES_DIR = Path(__file__).resolve().parent.parent / "samples"
SYNTHETIC_CHORD_WAV = SAMPLES_DIR / "synthetic_chord_test.wav"  # Signal-processing test only, not speech
CUTOFF_WAV = SAMPLES_DIR / "synthetic_cutoff_audio.wav"
AUDIO_EVAL_DIR = SAMPLES_DIR / "audio_eval"


def test_spectral_natural_audio(tmp_path: Path):
    """Verify spectrogram analysis and artifact generation on mathematical multi-harmonic chord."""
    artifact_plot = tmp_path / "spec_natural.png"
    sig, saved_plot = analyze_audio_spectrum(SYNTHETIC_CHORD_WAV, artifact_output_path=artifact_plot)

    assert isinstance(sig, Signal)
    assert sig.modality == "audio"
    assert sig.signal_id == "aud_spec_001"
    assert sig.limitation != ""
    assert artifact_plot.is_file()


def test_low_sample_rate_skip():
    """Verify Task B rule: High-frequency cutoff SKIPS if sample rate <= 16 kHz or bitrate < 64 kbps."""
    eval_file = AUDIO_EVAL_DIR / "real_1.wav"  # 16 kHz WAV
    loaded, err = load_and_preprocess_audio(eval_file)
    assert err is None
    assert loaded.original_sr <= 16000

    sig = analyze_high_frequency_cutoff(loaded, eval_file.name)
    assert sig.score is None
    assert "SKIPPED: Low sample rate / low bitrate files always show a high-frequency cutoff." in sig.evidence


def test_moderate_cap_for_audio_heuristics():
    """Verify Task C rule: Heuristics alone can NEVER push the level above MODERATE."""
    # Create signals where heuristic scores would normally push composite above 0.60
    mock_signals = [
        Signal(
            signal_id="aud_meta_001",
            modality="audio",
            name="Audio Container & Metadata Audit",
            score=0.70,
            evidence="Anomalous header structures detected.",
            limitation="Audio container headers can be converted.",
            source_file="test.wav",
        ),
        Signal(
            signal_id="aud_spec_001",
            modality="audio",
            name="Acoustic High-Frequency Cutoff (Heuristic)",
            score=0.75,
            evidence="Unusual audio characteristics were found: acoustic energy drops sharply above 7 kHz.",
            limitation="Compression can produce the same result.",
            source_file="test.wav",
        ),
        Signal(
            signal_id="aud_noise_001",
            modality="audio",
            name="Noise Floor & Spectral Flatness (Heuristic)",
            score=0.80,
            evidence="Unusual audio characteristics were found: background noise floor is unusually clean.",
            limitation="Studio recording can produce the same result.",
            source_file="test.wav",
        ),
        Signal(
            signal_id="aud_voice_001",
            modality="audio",
            name="Synthetic Voice / Deepfake Audio Detection",
            score=None,
            evidence="SKIPPED: synthetic-voice classifier failed a sanity check (identical output on every speech clip)",
            limitation="Classifier disabled.",
            source_file="test.wav",
        ),
    ]

    indicator, findings = evaluate_rule_based_correlation(mock_signals)

    # Must be capped at moderate, never elevated!
    assert indicator.level == "moderate"
    assert any("Level capped at MODERATE" in w for w in indicator.warnings)
    assert any("the synthetic-voice classifier is disabled" in w for w in indicator.warnings)


def test_audio_confidence_reduction():
    """Verify Task C confidence formula: starts at 0.50, -0.10 for <=16kHz, -0.10 for <3s, min 0.30."""
    eval_file = AUDIO_EVAL_DIR / "real_1.wav"  # 16 kHz and 2.0s duration
    case_mgr = CaseManager("TEST-CONF-001")
    signals = analyze_audio_pipeline(eval_file, case_manager=case_mgr)

    indicator, findings = evaluate_rule_based_correlation(signals)

    # 0.50 - 0.10 (<= 16 kHz) - 0.10 (< 3s) = 0.30
    assert indicator.confidence == 0.30
    assert any("audio sample rate is low (<= 16 kHz)" in w for w in indicator.warnings)
    assert any("audio duration is under 3 seconds" in w for w in indicator.warnings)


def test_contradiction_check():
    """Verify Task C consistency check: level matches findings without contradiction and no forbidden words."""
    eval_file = AUDIO_EVAL_DIR / "real_1.wav"
    case_mgr = CaseManager("TEST-CONTRA-001")
    signals = analyze_audio_pipeline(eval_file, case_manager=case_mgr)

    indicator, findings = evaluate_rule_based_correlation(signals)

    for f in findings:
        text = f.finding.lower()
        # Forbidden words check
        assert "natural" not in text
        assert "authentic" not in text
        assert "synthetic voice" not in text
        assert "cloned voice" not in text

        # Consistency check: If level is low, finding must weaken suspicion
        if indicator.level == "low":
            assert f.effect == "weakens"
            assert "no indicators" in text or "consistent" in text


def test_voice_classifier_fail_safe():
    """Verify synthetic voice classifier returns safe fallback in offline sandbox without hangs."""
    sig = classify_synthetic_voice(SYNTHETIC_CHORD_WAV, model_name="dummy/offline-model")
    assert isinstance(sig, Signal)
    assert sig.modality == "audio"
    assert sig.score is None
    assert "skipped" in sig.evidence.lower()
    assert len(sig.limitation) > 10


def test_transcript_comparison_matching_and_mismatch():
    """Verify transcript alignment scoring between audio content and textual claims."""
    # Matching case
    matching_sig = compare_transcript_to_caption(
        audio_path=SYNTHETIC_CHORD_WAV,
        caption="Breaking announcement regarding economic development and financial growth.",
        mock_transcript="The official report on economic development and financial growth in the city.",
    )
    assert isinstance(matching_sig, Signal)
    assert matching_sig.score is not None
    assert matching_sig.score <= 0.25
    assert "aligns" in matching_sig.evidence.lower()

    # Mismatch case
    mismatch_sig = compare_transcript_to_caption(
        audio_path=SYNTHETIC_CHORD_WAV,
        caption="Military declaration of national emergency and martial law in effect.",
        mock_transcript="Today we celebrate the opening of the community library and gardening festival.",
    )
    assert isinstance(mismatch_sig, Signal)
    assert mismatch_sig.score is not None
    assert mismatch_sig.score >= 0.70
    assert "discrepancy" in mismatch_sig.evidence.lower()


def test_full_audio_pipeline(tmp_path: Path):
    """Verify end-to-end audio pipeline integration with CaseManager."""
    case_mgr = CaseManager("TEST-AUD-001")
    signals = analyze_audio_pipeline(
        audio_path=CUTOFF_WAV,
        caption="Weather forecast and climate update.",
        case_manager=case_mgr,
    )

    assert len(signals) == 7
    assert all(isinstance(s, Signal) for s in signals)
    assert any(s.signal_id == "aud_meta_001" for s in signals)
    assert any(s.signal_id == "aud_spec_001" for s in signals)
    assert any(s.signal_id == "aud_noise_001" for s in signals)
    assert any(s.signal_id == "aud_prosody_001" for s in signals)
    assert any(s.signal_id == "aud_silence_001" for s in signals)
    assert any(s.signal_id == "aud_voice_001" for s in signals)
    assert any(s.signal_id == "aud_trans_001" for s in signals)

    # Check spectrogram artifact was created
    spec_artifact = case_mgr.get_artifact_path("spectrogram_synthetic_cutoff_audio.png")
    assert spec_artifact.is_file()
    assert len(case_mgr.history) >= 3
