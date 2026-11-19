"""Acoustic spectral analysis, spectrogram/waveform plotting, and time-segment anomaly detection."""

import os
import tempfile
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, List
import numpy as np
from scipy import signal as scipy_signal

# Ensure writable matplotlib config directory
if "MPLCONFIGDIR" not in os.environ:
    mpl_cache_dir = Path(tempfile.gettempdir()) / "truthlens_mpl"
    mpl_cache_dir.mkdir(parents=True, exist_ok=True)
    os.environ["MPLCONFIGDIR"] = str(mpl_cache_dir)

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt

from core.schemas import Signal, TimeLocation, create_fallback_signal
from .audio_loader import LoadedAudio, load_and_preprocess_audio
from .heuristics import analyze_high_frequency_cutoff, HEURISTIC_LIMITATION


def generate_audio_spectrogram_plot(
    loaded: LoadedAudio,
    artifact_output_path: Path,
) -> Optional[Path]:
    """Generate log-power acoustic spectrogram plot artifact."""
    try:
        artifact_output_path.parent.mkdir(parents=True, exist_ok=True)
        samples = loaded.y_16k
        duration = min(loaded.trimmed_duration, len(samples) / 16000.0)

        nperseg = min(512, len(samples))
        noverlap = nperseg // 2
        freqs, times, Sxx = scipy_signal.spectrogram(
            samples, fs=16000, nperseg=nperseg, noverlap=noverlap
        )
        Sxx_db = 10 * np.log10(np.maximum(Sxx, 1e-10))

        fig, ax_spec = plt.subplots(figsize=(8, 3.8), dpi=100)
        im = ax_spec.pcolormesh(times, freqs, Sxx_db, shading="gouraud", cmap="magma")
        ax_spec.set_title("Log-Power Spectrogram (Frequency Domain)", fontsize=10, fontweight="bold")
        ax_spec.set_xlabel("Time (seconds)", fontsize=9)
        ax_spec.set_ylabel("Frequency (Hz)", fontsize=9)
        ax_spec.set_ylim(0, 8000)
        fig.colorbar(im, ax=ax_spec, format="%+2.0f dB")

        plt.tight_layout()
        plt.savefig(str(artifact_output_path))
        plt.close(fig)
        return artifact_output_path
    except Exception:
        return None


def generate_audio_waveform_plot(
    loaded: LoadedAudio,
    artifact_output_path: Path,
) -> Optional[Path]:
    """Generate standalone audio waveform plot artifact."""
    try:
        artifact_output_path.parent.mkdir(parents=True, exist_ok=True)
        samples = loaded.y_16k
        duration = min(loaded.trimmed_duration, len(samples) / 16000.0)

        fig, ax_wave = plt.subplots(figsize=(8, 3.8), dpi=100)
        time_axis = np.linspace(0, duration, len(samples))
        ax_wave.plot(time_axis, samples, color="#00d2ff", linewidth=0.7, alpha=0.85)
        ax_wave.set_title("Audio Waveform (Time Domain Amplitude)", fontsize=10, fontweight="bold")
        ax_wave.set_xlabel("Time (seconds)", fontsize=9)
        ax_wave.set_ylabel("Amplitude", fontsize=9)
        ax_wave.set_xlim(0, max(duration, 0.1))
        ax_wave.grid(True, linestyle=":", alpha=0.4)

        plt.tight_layout()
        plt.savefig(str(artifact_output_path))
        plt.close(fig)
        return artifact_output_path
    except Exception:
        return None


def analyze_audio_spectrum(
    audio_path: Path,
    artifact_output_path: Optional[Path] = None,
) -> Tuple[Signal, Optional[Path]]:
    """Analyze audio frequencies, detect artificial cutoffs, and plot spectrogram.

    Uses compliant Task B heuristic logic:
    - Skips if original_sr <= 16 kHz or bitrate < 64 kbps.
    - Max score 0.40.
    """
    filename = audio_path.name
    try:
        loaded, err_sig = load_and_preprocess_audio(audio_path)
        if err_sig:
            return err_sig, None

        signal = analyze_high_frequency_cutoff(loaded, filename)

        saved_artifact = None
        if artifact_output_path:
            saved_artifact = generate_audio_spectrogram_plot(loaded, artifact_output_path)

        return signal, saved_artifact

    except Exception as e:
        fallback = create_fallback_signal(
            signal_id="aud_spec_001",
            modality="audio",
            name="Acoustic High-Frequency Cutoff (Heuristic)",
            source_file=filename,
            reason=f"Spectral analysis error: {str(e)}",
            limitation=HEURISTIC_LIMITATION,
        )
        return fallback, None
