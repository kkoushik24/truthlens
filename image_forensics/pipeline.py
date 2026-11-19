"""Image forensics orchestration pipeline."""

from pathlib import Path
from typing import List, Optional

from core.schemas import Signal
from core.case_manager import CaseManager
from .exif_analyzer import analyze_exif
from .ela_analyzer import perform_ela
from .ai_detector import detect_ai_generated_image


def analyze_image_pipeline(
    image_path: Path,
    case_manager: Optional[CaseManager] = None,
) -> List[Signal]:
    """Execute all image forensic modules and return aggregated signals."""
    signals: List[Signal] = []

    # 1. EXIF and Metadata Analysis
    exif_signal = analyze_exif(image_path)
    signals.append(exif_signal)
    if case_manager:
        case_manager.log_action(
            f"Image EXIF analysis completed for {image_path.name} (score: {exif_signal.score})."
        )

    # 2. Error Level Analysis & Heatmap Artifact
    artifact_path = None
    if case_manager:
        artifact_path = case_manager.get_artifact_path(f"ela_heatmap_{image_path.stem}.png")

    ela_signal, saved_artifact = perform_ela(image_path, artifact_output_path=artifact_path)
    signals.append(ela_signal)
    if case_manager:
        case_manager.log_action(
            f"Image ELA analysis completed for {image_path.name} (score: {ela_signal.score}, bbox: {ela_signal.location})."
        )

    # 3. AI-Generated Image Classification
    ai_signal = detect_ai_generated_image(image_path)
    signals.append(ai_signal)
    if case_manager:
        case_manager.log_action(
            f"Image AI detector completed for {image_path.name} (score: {ai_signal.score})."
        )

    return signals
