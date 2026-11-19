"""Synthetic voice and deepfake audio classification using Hugging Face transformers."""

import socket
from pathlib import Path
from typing import Optional, Dict, Any

from core.schemas import Signal, create_fallback_signal
from core.config import settings

_VOICE_DETECTOR_PIPELINE = None


def is_internet_available(timeout: float = 0.4) -> bool:
    """Fast non-blocking raw IP socket check to avoid DNS hangs in offline environments."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        res = sock.connect_ex(("1.1.1.1", 80))
        sock.close()
        return res == 0
    except Exception:
        return False


def is_audio_model_cached(model_name: str) -> bool:
    """Check if model weights are actually stored in local Hugging Face cache."""
    try:
        from huggingface_hub import try_to_load_from_cache
        for weight_file in ["model.safetensors", "pytorch_model.bin", "model.onnx"]:
            res = try_to_load_from_cache(model_name, weight_file)
            if isinstance(res, str):
                return True
        return False
    except Exception:
        return False


def get_voice_pipeline(model_name: Optional[str] = None):
    """Lazily load and cache the Hugging Face audio classification pipeline."""
    global _VOICE_DETECTOR_PIPELINE
    if _VOICE_DETECTOR_PIPELINE is None:
        target_model = model_name or settings.AUDIO_VOICE_DETECTOR_MODEL

        cached = is_audio_model_cached(target_model)
        if not cached and not settings.AUTO_DOWNLOAD_HF_MODELS:
            raise ConnectionError(
                f"Audio model '{target_model}' weights are not pre-cached and AUTO_DOWNLOAD_HF_MODELS=False."
            )

        if not cached and not is_internet_available(timeout=0.3):
            raise ConnectionError(
                f"Audio model '{target_model}' is not present in local cache, and environment is offline. "
                "Audio classification skipped to avoid application hang."
            )

        from transformers import pipeline
        _VOICE_DETECTOR_PIPELINE = pipeline(
            "audio-classification",
            model=target_model,
            device=-1,  # CPU strictly
            local_files_only=cached and not is_internet_available(0.2),
        )
    return _VOICE_DETECTOR_PIPELINE


def classify_synthetic_voice(
    audio_path: Path,
    model_name: Optional[str] = None,
) -> Signal:
    """Classify an audio recording for synthetic speech / TTS artifacts using pretrained acoustic models.

    NOTE: The current neural classifier (MelodyMachine/Deepfake-audio-detection-V2) failed the empirical sanity check
    (producing identical static outputs on every speech clip regardless of ground truth).
    Per specification, it is disabled in scoring until a validated model is provided.
    """
    filename = audio_path.name

    return Signal(
        signal_id="aud_voice_001",
        modality="audio",
        name="Synthetic Voice / Deepfake Audio Detection",
        score=None,
        evidence="SKIPPED: synthetic-voice classifier failed a sanity check (identical output on every speech clip)",
        location=None,
        limitation="Voice-clone detectors are trained on specific generators and can miss newer ones or be fooled by compression and noise. Treat this as one signal, not proof.",
        source_file=filename,
    )
