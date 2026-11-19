"""Generate DSP benchmark test audio files.

NOTE: These are mathematical signal-processing tests only, NOT speech.
They must NEVER appear in demos, the eval set, or any accuracy claim.
"""

from pathlib import Path
import numpy as np
import scipy.io.wavfile as wavfile
import scipy.signal as signal

samples_dir = Path(__file__).resolve().parent
samples_dir.mkdir(parents=True, exist_ok=True)

sr = 16000
duration = 2.0  # 2 seconds
t = np.linspace(0, duration, int(sr * duration), endpoint=False)

# 1. Multi-harmonic DSP frequency test (mathematical sine waves, NOT speech)
freqs = [220, 440, 880, 1760, 3520, 5000, 7000]
signal_chord = np.zeros_like(t)
for f in freqs:
    signal_chord += np.sin(2 * np.pi * f * t) * (1.0 / (f ** 0.5))
# Add subtle white noise across spectrum
noise = np.random.normal(0, 0.02, len(t))
signal_chord += noise
signal_chord = (signal_chord / np.max(np.abs(signal_chord)) * 32767).astype(np.int16)

synthetic_chord_wav_path = samples_dir / "synthetic_chord_test.wav"
wavfile.write(str(synthetic_chord_wav_path), sr, signal_chord)

# 2. Synthetic cutoff audio simulation (brickwall lowpass at 3 kHz + localized amplitude surge at t=1.0s)
sos = signal.butter(10, 3000, btype="lowpass", fs=sr, output="sos")
signal_cutoff = signal.sosfilt(sos, signal_chord.astype(np.float32))

# Inject localized energy surge at t=1.0s (index ~16000)
surge_start = int(0.9 * sr)
surge_end = int(1.1 * sr)
signal_cutoff[surge_start:surge_end] *= 4.0

signal_cutoff = (signal_cutoff / np.max(np.abs(signal_cutoff)) * 32767).astype(np.int16)
cutoff_wav_path = samples_dir / "synthetic_cutoff_audio.wav"
wavfile.write(str(cutoff_wav_path), sr, signal_cutoff)

print("DSP benchmark audio files generated successfully (signal-processing test only, not speech).")
