"""Audio forensics pipeline orchestration for TruthLens."""

from pathlib import Path
from typing import List, Optional

from core.schemas import Signal, create_fallback_signal
from core.case_manager import CaseManager
from .audio_loader import load_and_preprocess_audio, create_audio_metadata_signal
from .heuristics import (
    analyze_high_frequency_cutoff,
    analyze_spectral_flatness_and_noise_floor,
    analyze_pitch_and_prosody,
    analyze_silence_and_breath_patterns,
)
from .spectral_analyzer import generate_audio_spectrogram_plot, generate_audio_waveform_plot
from .voice_detector import classify_synthetic_voice
from .transcriber import compare_transcript_to_caption


def analyze_audio_pipeline(
    audio_path: Path,
    caption: Optional[str] = None,
    case_manager: Optional[CaseManager] = None,
) -> List[Signal]:
    """Execute all audio forensics modules and return aggregated signals."""
    signals: List[Signal] = []
    filename = audio_path.name

    try:
        # 1. Load and Preprocess Audio (strictly immutable, validated, 16 kHz resampled)
        loaded, err_sig = load_and_preprocess_audio(audio_path)
        if err_sig:
            signals.append(err_sig)
            if case_manager:
                case_manager.log_action(f"Audio loading failed for {filename}: {err_sig.evidence}")
            return signals

        # 2. Audio Container & Metadata Signal
        meta_sig = create_audio_metadata_signal(loaded, filename)
        signals.append(meta_sig)

        # 3. Deterministic Heuristics (Task B)
        # 3a. High-Frequency Cutoff (Heuristic)
        cutoff_sig = analyze_high_frequency_cutoff(loaded, filename)
        signals.append(cutoff_sig)

        # 3b. Noise Floor & Spectral Flatness (Heuristic)
        noise_sig = analyze_spectral_flatness_and_noise_floor(loaded, filename)
        signals.append(noise_sig)

        # 3c. Pitch Variation & Prosody (Heuristic)
        prosody_sig = analyze_pitch_and_prosody(loaded, filename)
        signals.append(prosody_sig)

        # 3d. Silence & Breath Regularity (Heuristic)
        silence_sig = analyze_silence_and_breath_patterns(loaded, filename)
        signals.append(silence_sig)

        # 4. Waveform & Spectrogram Plot Artifacts
        if case_manager:
            spec_path = case_manager.get_artifact_path(f"spectrogram_{audio_path.stem}.png")
            wave_path = case_manager.get_artifact_path(f"waveform_{audio_path.stem}.png")
            generate_audio_spectrogram_plot(loaded, spec_path)
            generate_audio_waveform_plot(loaded, wave_path)
            case_manager.log_action(f"Acoustic spectrogram and waveform plots generated for {filename}.")

        # 5. Synthetic Voice / Deepfake Detection (Task A: Disabled with Sanity Check reason)
        voice_sig = classify_synthetic_voice(audio_path)
        signals.append(voice_sig)
        if case_manager:
            case_manager.log_action(f"Voice classifier check recorded for {filename}: {voice_sig.evidence}")

        # 6. Speech-to-Text Transcription & Caption Alignment (Task D)
        trans_sig = compare_transcript_to_caption(audio_path=audio_path, caption=caption)
        signals.append(trans_sig)
        if case_manager:
            case_manager.log_action(f"Speech transcript alignment evaluated for {filename} (score: {trans_sig.score}).")

        return signals

    except Exception as e:
        signals.append(
            create_fallback_signal(
                signal_id="aud_pipe_001",
                modality="audio",
                name="Audio Forensics Pipeline",
                source_file=filename,
                reason=f"Pipeline exception: {str(e)}",
                limitation="Unhandled exception in audio decoding or pipeline execution.",
            )
        )
        return signals
