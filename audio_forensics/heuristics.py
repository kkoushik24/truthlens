"""Deterministic acoustic heuristics for TruthLens Audio Forensics.

All heuristics are weak indicators, capped per specification:
- High-frequency cutoff: max score 0.40 (or SKIPPED if sr <= 16 kHz or bitrate < 64 kbps)
- Spectral flatness / noise-floor consistency: max score 0.40
- Pitch variation and prosody (jitter/shimmer): max score 0.40
- Silence and breath regularity: max score 0.30

GLOBAL RULES ENFORCED:
- Wording: only 'unusual audio characteristics were found' or 'no indicators found by this check'.
- Never mention synthetic or cloned voices in evidence text.
- Every limitation text states:
  'Compression, noise reduction, studio recording, phone microphones and text-to-speech readers can produce the same result.'
"""

from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
import numpy as np

from core.schemas import Signal
from .audio_loader import LoadedAudio

HEURISTIC_LIMITATION = (
    "Compression, noise reduction, studio recording, phone microphones and "
    "text-to-speech readers can produce the same result."
)


def analyze_high_frequency_cutoff(loaded: LoadedAudio, filename: str) -> Signal:
    """Analyze high-frequency acoustic bandwidth relative to original container sample rate (Task B)."""
    # Rule: If original sample rate is 16 kHz or lower, or bitrate < 64 kbps, SKIP
    if loaded.original_sr <= 16000 or (loaded.bitrate_kbps > 0 and loaded.bitrate_kbps < 64.0):
        return Signal(
            signal_id="aud_spec_001",
            modality="audio",
            name="Acoustic High-Frequency Cutoff (Heuristic)",
            score=None,
            evidence="SKIPPED: Low sample rate / low bitrate files always show a high-frequency cutoff.",
            location=None,
            limitation=HEURISTIC_LIMITATION,
            source_file=filename,
        )

    # For files with sr > 16 kHz, compute frequency roll-off using FFT
    y = loaded.y_16k
    if len(y) < 512:
        return Signal(
            signal_id="aud_spec_001",
            modality="audio",
            name="Acoustic High-Frequency Cutoff (Heuristic)",
            score=0.10,
            evidence="No indicators found by this check: clip duration is too short for frequency roll-off evaluation.",
            location=None,
            limitation=HEURISTIC_LIMITATION,
            source_file=filename,
        )

    # Compute FFT power spectrum
    fft_vals = np.abs(np.fft.rfft(y[:16000 * 5]))  # First 5s for speed
    freqs = np.fft.rfftfreq(len(y[:16000 * 5]), d=1.0 / 16000.0)

    mid_mask = (freqs >= 2000) & (freqs <= 5000)
    high_mask = freqs >= 7000

    mid_power = np.mean(fft_vals[mid_mask] ** 2) if np.any(mid_mask) else 1e-9
    high_power = np.mean(fft_vals[high_mask] ** 2) if np.any(high_mask) else 1e-9

    db_drop = 10 * np.log10(max(mid_power, 1e-9) / max(high_power, 1e-9))

    if db_drop > 35.0:
        score = min(0.40, max(0.20, round(0.20 + (db_drop - 35.0) * 0.01, 2)))
        evidence = (
            "Unusual audio characteristics were found: acoustic energy drops sharply above 7 kHz "
            f"(high-frequency attenuation of {db_drop:.1f} dB relative to midband)."
        )
    else:
        score = 0.10
        evidence = (
            "No indicators found by this check: acoustic frequency content extends across upper "
            "frequencies without sharp attenuation."
        )

    return Signal(
        signal_id="aud_spec_001",
        modality="audio",
        name="Acoustic High-Frequency Cutoff (Heuristic)",
        score=score,
        evidence=evidence,
        location=None,
        limitation=HEURISTIC_LIMITATION,
        source_file=filename,
    )


def analyze_spectral_flatness_and_noise_floor(loaded: LoadedAudio, filename: str) -> Signal:
    """Analyze noise floor consistency and spectral distribution (Task B). Max score 0.40."""
    y = loaded.y_16k
    if len(y) < 1024:
        return Signal(
            signal_id="aud_noise_001",
            modality="audio",
            name="Noise Floor & Spectral Flatness (Heuristic)",
            score=0.10,
            evidence="No indicators found by this check: insufficient samples for background noise analysis.",
            location=None,
            limitation=HEURISTIC_LIMITATION,
            source_file=filename,
        )

    # Frame-based RMS energy (1024 samples = 64ms per frame, 50% overlap)
    frame_len = 1024
    hop_len = 512
    num_frames = (len(y) - frame_len) // hop_len + 1
    if num_frames < 2:
        num_frames = 1
        frame_rms = np.array([np.sqrt(np.mean(y ** 2) + 1e-12)])
    else:
        frames = np.lib.stride_tricks.sliding_window_view(y, frame_len)[::hop_len]
        frame_rms = np.sqrt(np.mean(frames ** 2, axis=1) + 1e-12)

    rms_db = 20 * np.log10(np.maximum(frame_rms, 1e-6))
    noise_floor_db = float(np.percentile(rms_db, 10))

    # Spectral flatness on center segment
    center_chunk = y[:min(len(y), 16000 * 4)]
    spectrum = np.abs(np.fft.rfft(center_chunk)) + 1e-9
    geo_mean = np.exp(np.mean(np.log(spectrum)))
    ari_mean = np.mean(spectrum)
    flatness = float(geo_mean / ari_mean) if ari_mean > 0 else 0.0

    # Unusually clean background (below -65 dB) or abrupt noise floor shifts
    split_idx = len(rms_db) // 2
    if split_idx > 2:
        floor_diff = abs(np.percentile(rms_db[:split_idx], 10) - np.percentile(rms_db[split_idx:], 10))
    else:
        floor_diff = 0.0

    is_unusually_clean = noise_floor_db < -65.0
    is_inconsistent_floor = floor_diff > 12.0

    if is_unusually_clean or is_inconsistent_floor:
        anomaly_parts = []
        if is_unusually_clean:
            anomaly_parts.append(f"background noise floor is unusually clean ({noise_floor_db:.1f} dBFS)")
        if is_inconsistent_floor:
            anomaly_parts.append(f"ambient noise shifts abruptly across segments ({floor_diff:.1f} dB jump)")
        evidence = f"Unusual audio characteristics were found: {'; '.join(anomaly_parts)}."
        score = 0.35 if (is_unusually_clean and is_inconsistent_floor) else 0.25
    else:
        score = 0.10
        evidence = (
            f"No indicators found by this check: background noise floor ({noise_floor_db:.1f} dBFS) "
            "and spectral distribution appear consistent."
        )

    return Signal(
        signal_id="aud_noise_001",
        modality="audio",
        name="Noise Floor & Spectral Flatness (Heuristic)",
        score=min(0.40, score),
        evidence=evidence,
        location=None,
        limitation=HEURISTIC_LIMITATION,
        source_file=filename,
    )


def analyze_pitch_and_prosody(loaded: LoadedAudio, filename: str) -> Signal:
    """Analyze pitch variation and prosodic regularity (Task B). Max score 0.40."""
    y = loaded.y_16k
    sr = 16000

    if len(y) < sr * 1:  # Under 1 second
        return Signal(
            signal_id="aud_prosody_001",
            modality="audio",
            name="Pitch Variation & Prosody (Heuristic)",
            score=0.10,
            evidence="No indicators found by this check: clip duration is too short for prosodic cadence evaluation.",
            location=None,
            limitation=HEURISTIC_LIMITATION,
            source_file=filename,
        )

    # Frame autocorrelation pitch tracker (frames of 40ms = 640 samples, 20ms hop)
    frame_len = 640
    hop_len = 320
    min_lag = int(sr / 400.0)  # 400 Hz
    max_lag = int(sr / 60.0)   # 60 Hz

    num_frames = (len(y) - frame_len) // hop_len + 1
    frames = np.lib.stride_tricks.sliding_window_view(y, frame_len)[::hop_len]

    pitches = []
    energy_thresh = 0.02 * np.max(np.abs(y)) if np.max(np.abs(y)) > 0 else 0.01

    for frame in frames:
        rms = np.sqrt(np.mean(frame ** 2))
        if rms > energy_thresh:
            corr = np.correlate(frame, frame, mode="full")[frame_len - 1 :]
            corr_search = corr[min_lag:max_lag]
            if len(corr_search) > 0 and np.max(corr_search) > 0.3 * corr[0]:
                best_lag = min_lag + int(np.argmax(corr_search))
                pitch_hz = sr / float(best_lag)
                pitches.append(pitch_hz)

    if len(pitches) >= 8:
        pitch_std = float(np.std(pitches))
        # Unusually flat pitch contour (std < 6 Hz across sustained speech)
        if pitch_std < 6.0:
            score = 0.35
            evidence = (
                f"Unusual audio characteristics were found: pitch contour exhibits unusually flat "
                f"or robotic delivery (pitch variation std: {pitch_std:.1f} Hz)."
            )
        elif pitch_std < 10.0:
            score = 0.20
            evidence = (
                f"Unusual audio characteristics were found: pitch variation is relatively constrained "
                f"(pitch variation std: {pitch_std:.1f} Hz)."
            )
        else:
            score = 0.10
            evidence = (
                f"No indicators found by this check: vocal pitch modulation is within typical speech ranges "
                f"(pitch variation std: {pitch_std:.1f} Hz)."
            )
    else:
        score = 0.10
        evidence = "No indicators found by this check: insufficient voiced frames detected to measure pitch modulation."

    return Signal(
        signal_id="aud_prosody_001",
        modality="audio",
        name="Pitch Variation & Prosody (Heuristic)",
        score=min(0.40, score),
        evidence=evidence,
        location=None,
        limitation=HEURISTIC_LIMITATION,
        source_file=filename,
    )


def analyze_silence_and_breath_patterns(loaded: LoadedAudio, filename: str) -> Signal:
    """Analyze pause patterns and silence regularity between speech segments (Task B). Max score 0.30."""
    y = loaded.y_16k
    sr = 16000

    if len(y) < sr * 2:  # Under 2 seconds
        return Signal(
            signal_id="aud_silence_001",
            modality="audio",
            name="Silence & Breath Regularity (Heuristic)",
            score=0.10,
            evidence="No indicators found by this check: recording is too brief for pause regularity analysis.",
            location=None,
            limitation=HEURISTIC_LIMITATION,
            source_file=filename,
        )

    # Fast silence detection based on frame energy
    frame_len = 800  # 50ms
    hop_len = 400    # 25ms
    frames = np.lib.stride_tricks.sliding_window_view(y, frame_len)[::hop_len]
    frame_energy = np.sqrt(np.mean(frames ** 2, axis=1))

    peak_e = np.max(frame_energy) if np.max(frame_energy) > 0 else 1.0
    thresh = 0.05 * peak_e
    is_silent = frame_energy < thresh

    # Find pause segment durations
    pauses = []
    current_pause = 0
    for s in is_silent:
        if s:
            current_pause += 1
        else:
            if current_pause >= 4:  # At least 100ms
                pauses.append(current_pause * 0.025)
            current_pause = 0
    if current_pause >= 4:
        pauses.append(current_pause * 0.025)

    if len(pauses) >= 4:
        pause_std = float(np.std(pauses))
        if pause_std < 0.03:  # Metronomic, unnaturally regular pause pacing
            score = 0.28
            evidence = (
                f"Unusual audio characteristics were found: pause intervals between speech bursts "
                f"exhibit unusually regular pacing (pause duration std: {pause_std:.2f}s across {len(pauses)} pauses)."
            )
        else:
            score = 0.10
            evidence = (
                f"No indicators found by this check: pause and breath patterns exhibit variable, "
                f"spontaneous delivery (std: {pause_std:.2f}s)."
            )
    else:
        score = 0.10
        evidence = "No indicators found by this check: continuous speech without artificial pause discretization."

    return Signal(
        signal_id="aud_silence_001",
        modality="audio",
        name="Silence & Breath Regularity (Heuristic)",
        score=min(0.30, score),
        evidence=evidence,
        location=None,
        limitation=HEURISTIC_LIMITATION,
        source_file=filename,
    )
