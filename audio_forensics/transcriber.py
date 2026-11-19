"""Speech-to-text transcription (Groq Whisper API & faster-whisper) and cross-modal transcript alignment."""

import json
import re
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

from core.schemas import Signal, create_fallback_signal
from core.config import settings

_WHISPER_MODEL = None


def get_whisper_model():
    """Lazily load and cache the faster-whisper model."""
    global _WHISPER_MODEL
    if _WHISPER_MODEL is None:
        from faster_whisper import WhisperModel
        _WHISPER_MODEL = WhisperModel(
            settings.WHISPER_MODEL_SIZE,
            device="cpu",
            compute_type="int8",
        )
    return _WHISPER_MODEL


def transcribe_audio_groq(audio_path: Path) -> Optional[str]:
    """Transcribe spoken audio via Groq Whisper API (whisper-large-v3)."""
    if not settings.GROQ_API_KEY or len(settings.GROQ_API_KEY.strip()) < 5:
        return None
    try:
        from groq import Groq
        client = Groq(api_key=settings.GROQ_API_KEY)
        with open(audio_path, "rb") as f:
            result = client.audio.transcriptions.create(
                file=(audio_path.name, f.read()),
                model="whisper-large-v3",
                response_format="text",
                timeout=15.0,
            )
            if isinstance(result, str):
                return result.strip() or None
            return getattr(result, "text", str(result)).strip() or None
    except Exception:
        return None


def transcribe_audio(audio_path: Path) -> Optional[str]:
    """Transcribe spoken audio to text using Groq Whisper API or local faster-whisper."""
    # 1. Try Groq Whisper API first if key is present
    if settings.GROQ_API_KEY and len(settings.GROQ_API_KEY.strip()) > 5:
        text = transcribe_audio_groq(audio_path)
        if text:
            return text

    # 2. Fall back to local faster-whisper if installed
    try:
        model = get_whisper_model()
        segments, _ = model.transcribe(str(audio_path), beam_size=1)
        transcript_text = " ".join([seg.text.strip() for seg in segments]).strip()
        return transcript_text or None
    except Exception:
        return None


def _compare_transcript_groq(transcript: str, caption: str) -> Optional[Tuple[float, str]]:
    """Compare transcript and caption claim using Groq text LLM."""
    if not settings.GROQ_API_KEY or len(settings.GROQ_API_KEY.strip()) < 5:
        return None
    try:
        from groq import Groq
        client = Groq(api_key=settings.GROQ_API_KEY)
        prompt = (
            "You are a forensic auditor evaluating whether spoken dialogue in an audio recording matches an external claim/caption.\n"
            f"Transcript: \"{transcript}\"\n"
            f"Caption: \"{caption}\"\n\n"
            "Evaluate if the spoken audio contradicts, misattributes, or aligns with the claim.\n"
            "Return ONLY a JSON object: {\"score\": <float between 0.10 and 0.80>, \"evidence\": \"<one-sentence explanation>\"}.\n"
            "Score guidance: 0.10-0.20 if strongly aligned; 0.35-0.50 if partial overlap; 0.65-0.80 if contradicted/misattributed."
        )
        response = client.chat.completions.create(
            model=settings.GROQ_TEXT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            timeout=10.0,
        )
        res_json = json.loads(response.choices[0].message.content)
        score = float(res_json.get("score", 0.40))
        evidence = str(res_json.get("evidence", "Transcript evaluated against caption claim."))
        return score, evidence
    except Exception:
        return None


def compare_transcript_to_caption(
    audio_path: Path,
    caption: Optional[str] = None,
    mock_transcript: Optional[str] = None,
) -> Signal:
    """Compare transcribed speech against submitted text caption to detect misattributed or altered audio (Task D)."""
    filename = audio_path.name
    try:
        # Rule: If no caption: "SKIPPED: no caption provided", excluded from scoring
        if not caption or not caption.strip():
            return Signal(
                signal_id="aud_trans_001",
                modality="audio",
                name="Speech Transcript vs Caption Alignment",
                score=None,
                evidence="SKIPPED: no caption provided",
                location=None,
                limitation="Alignment verification requires both an audio transcript and an external claim.",
                source_file=filename,
            )

        transcript = mock_transcript if mock_transcript is not None else transcribe_audio(audio_path)

        # Rule: If unavailable: "SKIPPED: <reason>"
        if not transcript:
            return Signal(
                signal_id="aud_trans_001",
                modality="audio",
                name="Speech Transcript vs Caption Alignment",
                score=None,
                evidence="SKIPPED: speech recognition unavailable or no intelligible speech detected",
                location=None,
                limitation="Audio may contain instrumental music, background ambient noise, or low signal-to-noise ratio.",
                source_file=filename,
            )

        # Try Groq comparison first
        groq_result = _compare_transcript_groq(transcript, caption)
        if groq_result:
            suspicion_score, evidence = groq_result
        else:
            # Deterministic keyword overlap calculation
            clean_transcript = set(re.findall(r"\b[a-zA-Z]{3,}\b", transcript.lower()))
            clean_caption = set(re.findall(r"\b[a-zA-Z]{3,}\b", caption.lower()))

            stopwords = {
                "the", "and", "that", "this", "with", "from", "for", "are", "was", "were",
                "been", "have", "has", "had", "they", "will", "would", "about", "there"
            }
            words_t = clean_transcript - stopwords
            words_c = clean_caption - stopwords

            overlap = words_t.intersection(words_c)
            overlap_ratio = len(overlap) / float(max(len(words_c), 1))

            if overlap_ratio >= 0.40:
                suspicion_score = 0.15
                evidence = (
                    f"Spoken dialogue strongly aligns with caption claim ({len(overlap)} matching core terms). "
                    f"Transcript snippet: \"{transcript[:120]}...\"."
                )
            elif overlap_ratio >= 0.15:
                suspicion_score = 0.40
                evidence = (
                    f"Moderate thematic overlap between spoken words and caption ({len(overlap)} matching terms). "
                    f"Transcript: \"{transcript[:120]}...\"."
                )
            else:
                suspicion_score = 0.75
                evidence = (
                    f"Significant discrepancy between spoken dialogue and external caption claim (only {len(overlap)} matching terms). "
                    f"Audio transcript: \"{transcript[:120]}...\"."
                )

        return Signal(
            signal_id="aud_trans_001",
            modality="audio",
            name="Speech Transcript vs Caption Alignment",
            score=round(suspicion_score, 2),
            evidence=evidence,
            location=None,
            limitation="Transcript keyword matching relies on lexical overlap and does not capture full nuances or parody context.",
            source_file=filename,
        )

    except Exception as e:
        return create_fallback_signal(
            signal_id="aud_trans_001",
            modality="audio",
            name="Speech Transcript vs Caption Alignment",
            source_file=filename,
            reason=f"Speech transcription check failed: {str(e)}",
            limitation="Failed speech recognition execution.",
        )
