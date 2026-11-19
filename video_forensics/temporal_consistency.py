"""Temporal consistency and inter-frame anomaly detection for video sequences (Task 4)."""

from pathlib import Path
from typing import List, Dict, Any, Optional
import cv2
import numpy as np

from core.schemas import Signal, FrameLocation, create_fallback_signal


TEMPORAL_LIMITATION = (
    "Modern AI video generators produce smooth frames, so a clean result here proves nothing. "
    "Fast camera pans, zooms, or cinematic hard scene cuts can also cause metric jumps without indicating video tampering."
)


def check_temporal_consistency(
    sampled_frames: List[Dict[str, Any]],
    source_file: str = "video.mp4",
) -> Signal:
    """Analyze consecutive sampled frames for abrupt jumps in brightness, sharpness, and color histograms."""
    try:
        if len(sampled_frames) < 2:
            return Signal(
                signal_id="vid_temp_001",
                modality="video",
                name="Video Temporal Consistency",
                score=0.10,
                evidence="No indicators found by this check: insufficient frames to perform temporal continuity comparison.",
                location=None,
                limitation=TEMPORAL_LIMITATION,
                source_file=source_file,
            )

        metrics: List[Dict[str, Any]] = []

        # 1. Compute per-frame photometric and spatial metrics
        for item in sampled_frames:
            bgr = item.get("bgr")
            if bgr is None and item.get("path") and Path(item["path"]).is_file():
                bgr = cv2.imread(str(item["path"]))

            if bgr is None:
                continue

            gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
            brightness = float(np.mean(gray))
            laplacian_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())

            hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
            hist = cv2.calcHist([hsv], [0, 1], None, [16, 16], [0, 180, 0, 256])
            cv2.normalize(hist, hist, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)

            metrics.append({
                "brightness": brightness,
                "sharpness": laplacian_var,
                "hist": hist,
                "index": item["index"],
                "timestamp": item["timestamp"],
            })

        if len(metrics) < 2:
            return Signal(
                signal_id="vid_temp_001",
                modality="video",
                name="Video Temporal Consistency",
                score=0.10,
                evidence="No indicators found by this check: fewer than 2 decodable frames available.",
                location=None,
                limitation=TEMPORAL_LIMITATION,
                source_file=source_file,
            )

        # 2. Compute step-to-step deltas
        max_color_divergence = 0.0
        max_sharpness_ratio = 1.0
        flagged_frame_idx: Optional[int] = None
        flagged_timestamp: Optional[float] = None

        for i in range(len(metrics) - 1):
            curr = metrics[i]
            nxt = metrics[i + 1]

            hist_corr = float(cv2.compareHist(curr["hist"], nxt["hist"], cv2.HISTCMP_CORREL))
            color_divergence = max(0.0, 1.0 - hist_corr)

            sharp1 = max(curr["sharpness"], 1.0)
            sharp2 = max(nxt["sharpness"], 1.0)
            sharp_ratio = max(sharp1 / sharp2, sharp2 / sharp1)

            if color_divergence > max_color_divergence:
                max_color_divergence = color_divergence
                if color_divergence > 0.55:
                    flagged_frame_idx = nxt["index"]
                    flagged_timestamp = nxt["timestamp"]

            if sharp_ratio > max_sharpness_ratio:
                max_sharpness_ratio = sharp_ratio
                if sharp_ratio > 4.5 and flagged_frame_idx is None:
                    flagged_frame_idx = nxt["index"]
                    flagged_timestamp = nxt["timestamp"]

        # 3. Calculate suspicion score (0.0 to 1.0)
        if max_color_divergence > 0.65 or max_sharpness_ratio > 5.0:
            suspicion_score = min(0.85, 0.45 + (max_color_divergence * 0.35))
            evidence = (
                f"Unusual visual characteristics were found: abrupt inter-frame discontinuity detected between "
                f"sampled frames at timestamp {flagged_timestamp:.2f}s (Frame #{flagged_frame_idx}). "
                f"Color divergence: {max_color_divergence:.2f}, sharpness jump ratio: {max_sharpness_ratio:.2f}."
            )
            location = FrameLocation(index=int(flagged_frame_idx)) if flagged_frame_idx is not None else None
        elif max_color_divergence > 0.40 or max_sharpness_ratio > 3.0:
            suspicion_score = 0.35
            evidence = (
                f"Unusual visual characteristics were found: moderate inter-frame variance detected "
                f"(color divergence: {max_color_divergence:.2f}, sharpness ratio: {max_sharpness_ratio:.2f}), "
                "consistent with rapid camera motion, pans, or illumination shifts."
            )
            location = None
        else:
            suspicion_score = 0.10
            evidence = (
                f"No indicators found by this check: temporal transitions across {len(sampled_frames)} sampled frames "
                f"are continuous (color divergence: {max_color_divergence:.2f}, sharpness ratio: {max_sharpness_ratio:.2f})."
            )
            location = None

        return Signal(
            signal_id="vid_temp_001",
            modality="video",
            name="Video Temporal Consistency",
            score=round(suspicion_score, 2),
            evidence=evidence,
            location=location,
            limitation=TEMPORAL_LIMITATION,
            source_file=source_file,
        )

    except Exception as e:
        return create_fallback_signal(
            signal_id="vid_temp_001",
            modality="video",
            name="Video Temporal Consistency",
            source_file=source_file,
            reason=f"Temporal consistency check failed: {str(e)}",
            limitation=TEMPORAL_LIMITATION,
        )
