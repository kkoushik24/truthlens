"""Tests for Groq API integration (Vision, Correlation, and Whisper ASR)."""

from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from core.schemas import Signal, OverallIndicator, CrossModalFinding
from text_analysis.llm_provider import GroqVisionProvider, get_llm_provider
from correlation.llm_correlator import synthesize_llm_correlation
from audio_forensics.transcriber import transcribe_audio_groq

BASE_DIR = Path(__file__).resolve().parent.parent
SAMPLE_IMAGE = BASE_DIR / "samples" / "clean_photo.jpg"
SAMPLE_AUDIO = BASE_DIR / "samples" / "synthetic_chord_test.wav"  # Signal-processing test only, not speech


def test_groq_vision_provider_mock():
    """Verify GroqVisionProvider processes response into structured dictionary."""
    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = (
        '{"visual_description": "A sunny mountain scene.", '
        '"mismatches": ["Caption claims blizzard."], '
        '"suspicion_score": 0.85, '
        '"evidence": "Severe contradiction between weather and claim."}'
    )
    mock_response.choices = [mock_choice]

    with patch("groq.Groq") as mock_groq_cls:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_groq_cls.return_value = mock_client

        provider = GroqVisionProvider(api_key="gsk_test_mock_key_123456")
        res = provider.analyze_image_caption_alignment(SAMPLE_IMAGE, "Blizzard in the mountains")

        assert isinstance(res, dict)
        assert res["suspicion_score"] == 0.85
        assert len(res["mismatches"]) == 1
        assert "contradiction" in res["evidence"].lower()


def test_groq_correlator_mock():
    """Verify Groq correlator parses JSON summary and validates signal citations."""
    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = (
        '{"summary": "Forensic correlation demonstrates high inconsistency across image and caption.", '
        '"cross_modal_findings": ['
        '  {"finding": "Visual setting contradicts text.", "supporting_signals": ["sig_01", "sig_02"], "effect": "strengthens"}'
        ']}'
    )
    mock_response.choices = [mock_choice]

    signals = [
        Signal(
            signal_id="sig_01",
            modality="image",
            name="ELA",
            score=0.8,
            evidence="High error divergence.",
            limitation="Test limitation",
            source_file="photo.jpg",
        ),
        Signal(
            signal_id="sig_02",
            modality="text",
            name="Caption",
            score=0.75,
            evidence="Tropical blizzard claim.",
            limitation="Test limitation",
            source_file="claim.txt",
        ),
    ]
    indicator = OverallIndicator(level="elevated", confidence=0.85, primary_drivers=["sig_01"])
    fallback_findings = [CrossModalFinding(finding="Fallback finding", supporting_signals=["sig_01"], effect="strengthens")]

    with patch("core.config.settings.GROQ_API_KEY", "gsk_test_key_123456"):
        with patch("core.config.settings.LLM_PROVIDER", "groq"):
            with patch("groq.Groq") as mock_groq_cls:
                mock_client = MagicMock()
                mock_client.chat.completions.create.return_value = mock_response
                mock_groq_cls.return_value = mock_client

                findings, summary = synthesize_llm_correlation(signals, indicator, fallback_findings)

                assert len(findings) == 1
                assert findings[0].supporting_signals == ["sig_01", "sig_02"]
                assert "inconsistency" in summary.lower()


def test_groq_whisper_transcriber_mock():
    """Verify Groq Whisper ASR extraction."""
    with patch("core.config.settings.GROQ_API_KEY", "gsk_test_key_123456"):
        with patch("groq.Groq") as mock_groq_cls:
            mock_client = MagicMock()
            mock_client.audio.transcriptions.create.return_value = "Official economic conference proceedings."
            mock_groq_cls.return_value = mock_client

            text = transcribe_audio_groq(SAMPLE_AUDIO)
            assert text == "Official economic conference proceedings."
