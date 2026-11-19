"""Text and caption forensics pipeline orchestration (Tasks 1 - 4)."""

import json
from pathlib import Path
from typing import List, Optional, Dict, Any

from core.schemas import Signal
from core.case_manager import CaseManager
from .text_heuristics import analyze_caption_heuristics
from .caption_checker import check_caption_vs_media, check_caption_vs_image
from .visual_plausibility import check_visual_plausibility
from .llm_provider import LLMProvider, get_llm_provider


def analyze_text_pipeline(
    caption: str,
    image_path: Optional[Path] = None,
    media_path: Optional[Path] = None,
    media_type: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    case_manager: Optional[CaseManager] = None,
    llm_provider: Optional[LLMProvider] = None,
    sampled_frames: Optional[List[Dict[str, Any]]] = None,
    per_frame_records: Optional[List[Dict[str, Any]]] = None,
    transcript: Optional[str] = None,
) -> List[Signal]:
    """Execute text forensics, claim extraction, evidence bundle audit, and cross-modal comparison."""
    signals: List[Signal] = []
    clean_caption = (caption or "").strip()
    target_media = media_path or image_path

    # 1. Linguistic and Chronological Heuristic Checks
    heur_signal = analyze_caption_heuristics(clean_caption, metadata=metadata)
    signals.append(heur_signal)
    if case_manager:
        case_manager.log_action(
            f"Caption linguistic audit completed (score: {heur_signal.score})."
        )

    # 2. Visual Plausibility Signal (if image asset provided)
    if target_media and target_media.is_file():
        suf = target_media.suffix.lower()
        is_img = suf in [".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"]
        if is_img:
            plaus_signal = check_visual_plausibility(target_media)
            signals.append(plaus_signal)
            if case_manager:
                case_manager.log_action(
                    f"Visual plausibility audit completed for {target_media.name} (score: {plaus_signal.score})."
                )

        # 3. Caption vs Media Alignment ('Possible out-of-context use' signal - Task 4)
        vis_signal, full_analysis = check_caption_vs_media(
            media_path=target_media,
            caption=clean_caption,
            media_type=media_type,
            sampled_frames=sampled_frames,
            per_frame_records=per_frame_records,
            transcript=transcript,
            llm_provider=llm_provider,
        )
        signals.append(vis_signal)

        if case_manager:
            case_manager.log_action(
                f"Caption-vs-media alignment evaluated for {target_media.name} (score: {vis_signal.score})."
            )
            # Save structured analysis artifact for Text & Context Tab (Task 5)
            try:
                # Remove non-serializable objects before saving
                serializable_analysis = dict(full_analysis)
                if "signal" in serializable_analysis:
                    serializable_analysis.pop("signal")
                art_path = case_manager.get_artifact_path("text_context_analysis.json")
                art_path.write_text(json.dumps(serializable_analysis, indent=2), encoding="utf-8")
            except Exception:
                pass

    return signals
