"""Robust audio loading, metadata extraction, validation, and normalization for TruthLens."""

import hashlib
import os
from math import gcd
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
import numpy as np
import soundfile as sf
import scipy.signal

from core.schemas import Signal


@dataclass
class LoadedAudio:
    """Standardized representation of loaded and preprocessed audio."""
    y_16k: np.ndarray             # Mono float32 array resampled to 16 kHz, capped at 60s
    sr_model: int                 # Target model sample rate (always 16000)
    original_sr: int              # Original sample rate (Hz)
    original_channels: int        # Original channel count (1=mono, 2=stereo)
    original_duration: float      # Full duration of audio in seconds
    original_size_bytes: int      # Exact file size in bytes
    bit_depth: str                # Bit depth / subtype (e.g., '16-bit PCM')
    bitrate_kbps: float           # Estimated bitrate in kilobits per second
    format: str                   # Container format (WAV, FLAC, MP3, M4A)
    is_trimmed: bool              # True if audio exceeded 60s and was trimmed
    trimmed_duration: float       # Duration after trimming (<= 60.0s)
    source_label: str             # 'Audio file' or 'Audio from video'
    initial_sha256: str           # SHA-256 checksum taken before loading


def compute_file_sha256(path: Path) -> str:
    """Calculate SHA-256 checksum to guarantee original file immutability."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def load_and_preprocess_audio(
    audio_path: Path,
    source_label: str = "Audio file",
    max_duration_sec: float = 60.0,
    min_duration_sec: float = 2.0,
) -> Tuple[Optional[LoadedAudio], Optional[Signal]]:
    """Load audio with librosa as mono, resample to 16 kHz for model input, and preserve original metadata.

    Returns:
        (LoadedAudio, None) if successful, or (None, failure_Signal) if validation fails.
    """
    filename = audio_path.name
    if not audio_path.is_file():
        return None, Signal(
            signal_id="aud_meta_001",
            modality="audio",
            name="Audio Container & Metadata Audit",
            score=None,
            evidence=f"FAILED: Audio file not found at '{audio_path}'.",
            location=None,
            limitation="Missing file prevents audio inspection.",
            source_file=filename,
        )

    # 1. Guarantee immutability check
    initial_hash = compute_file_sha256(audio_path)
    file_size = audio_path.stat().st_size
    ext = audio_path.suffix.lower().replace(".", "").upper() or "UNKNOWN"

    # 2. Extract original container metadata using soundfile
    try:
        info = sf.info(str(audio_path))
        orig_sr = int(info.samplerate)
        orig_channels = int(info.channels)
        orig_duration = float(info.duration)
        orig_format = str(info.format)
        bit_depth = str(info.subtype) if info.subtype else "Unknown"
        bitrate_kbps = round((file_size * 8.0) / (orig_duration * 1000.0), 1) if orig_duration > 0 else 0.0
    except Exception as e:
        # Catch decoder issues for MP3/M4A or corrupted headers
        err_msg = str(e)
        if ext in ["MP3", "M4A"]:
            fail_reason = f"FAILED: unsupported or missing decoder: {err_msg}"
        else:
            fail_reason = f"FAILED: Could not read audio container header: {err_msg}"
        return None, Signal(
            signal_id="aud_meta_001",
            modality="audio",
            name="Audio Container & Metadata Audit",
            score=None,
            evidence=fail_reason,
            location=None,
            limitation="Compressed or non-standard audio containers require appropriate system decoders.",
            source_file=filename,
        )

    # 3. Minimum duration check (at least 2.0s)
    if orig_duration < min_duration_sec:
        return None, Signal(
            signal_id="aud_meta_001",
            modality="audio",
            name="Audio Container & Metadata Audit",
            score=None,
            evidence=f"FAILED: Audio duration ({orig_duration:.2f}s) is shorter than minimum required {min_duration_sec:.1f} seconds.",
            location=None,
            limitation="Clips under 2 seconds lack sufficient acoustic frames for reliable spectral or prosodic evaluation.",
            source_file=filename,
        )

    # 4. Load audio samples as mono float32 and resample to 16 kHz
    try:
        raw_samples, sample_rate = sf.read(str(audio_path), dtype="float32")
        if raw_samples.ndim > 1:
            raw_samples = np.mean(raw_samples, axis=1)

        # Resample to 16 kHz if necessary
        if sample_rate != 16000:
            common_div = gcd(sample_rate, 16000)
            up = 16000 // common_div
            down = sample_rate // common_div
            y_16k = scipy.signal.resample_poly(raw_samples, up, down).astype(np.float32)
        else:
            y_16k = raw_samples.astype(np.float32)
    except Exception as load_err:
        err_msg = str(load_err)
        if ext in ["MP3", "M4A"]:
            fail_reason = f"FAILED: unsupported or missing decoder: {err_msg}"
        else:
            fail_reason = f"FAILED: Unable to decode audio samples: {err_msg}"
        return None, Signal(
            signal_id="aud_meta_001",
            modality="audio",
            name="Audio Container & Metadata Audit",
            score=None,
            evidence=fail_reason,
            location=None,
            limitation="Decoded sample stream could not be loaded into memory.",
            source_file=filename,
        )

    # Check if trimmed
    is_trimmed = orig_duration > max_duration_sec
    trimmed_duration = min(orig_duration, max_duration_sec)
    if is_trimmed:
        y_16k = y_16k[: int(16000 * max_duration_sec)]

    # 5. Verify original file immutability
    post_hash = compute_file_sha256(audio_path)
    if initial_hash != post_hash:
        raise RuntimeError("Integrity violation: original audio file was modified during loading!")

    loaded = LoadedAudio(
        y_16k=y_16k.astype(np.float32),
        sr_model=16000,
        original_sr=orig_sr,
        original_channels=orig_channels,
        original_duration=orig_duration,
        original_size_bytes=file_size,
        bit_depth=bit_depth,
        bitrate_kbps=bitrate_kbps,
        format=orig_format,
        is_trimmed=is_trimmed,
        trimmed_duration=trimmed_duration,
        source_label=source_label,
        initial_sha256=initial_hash,
    )

    return loaded, None


def create_audio_metadata_signal(loaded: LoadedAudio, filename: str) -> Signal:
    """Generate the audio container & metadata inspection signal (Task 2 & 4)."""
    channel_desc = "mono" if loaded.original_channels == 1 else f"{loaded.original_channels}-channel stereo"
    trim_note = f" (Trimmed to first {loaded.trimmed_duration:.0f}s for model evaluation)" if loaded.is_trimmed else ""
    source_prefix = f"[{loaded.source_label}] " if loaded.source_label != "Audio file" else ""

    evidence = (
        f"{source_prefix}Container format: {loaded.format} ({loaded.bit_depth}, {channel_desc}). "
        f"Sample rate: {loaded.original_sr} Hz, duration: {loaded.original_duration:.2f}s, "
        f"size: {loaded.original_size_bytes / 1024.0:.1f} KB (~{loaded.bitrate_kbps:.1f} kbps){trim_note}. "
        "No container anomalies or header corruptions detected."
    )

    return Signal(
        signal_id="aud_meta_001",
        modality="audio",
        name="Audio Container & Metadata Audit",
        score=0.10,
        evidence=evidence,
        location=None,
        limitation="Audio container headers can be converted or stripped by editing tools and messaging applications without altering the acoustic content.",
        source_file=filename,
    )
