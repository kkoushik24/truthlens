"""TruthLens Audio Forensics Module."""

from .spectral_analyzer import analyze_audio_spectrum
from .voice_detector import classify_synthetic_voice
from .transcriber import transcribe_audio, compare_transcript_to_caption
from .pipeline import analyze_audio_pipeline

__all__ = [
    "analyze_audio_spectrum",
    "classify_synthetic_voice",
    "transcribe_audio",
    "compare_transcript_to_caption",
    "analyze_audio_pipeline",
]
