"""OpenCV uniform frame sampling with strict capping, trimming, and blank-frame filtering."""

from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import cv2
import numpy as np


def is_blank_or_black_frame(
    frame: Optional[np.ndarray],
    black_thresh: float = 2.0,
) -> bool:
    """Detect if frame is completely black or blank (e.g. solid fade-to-black or unrendered frame)."""
    if frame is None or frame.size == 0:
        return True
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    mean_val = float(np.mean(gray))
    max_val = float(np.max(gray))
    min_val = float(np.min(gray))
    # Fully black: mean < 2.0 and max < 10
    if mean_val < black_thresh and max_val < 10.0:
        return True
    # Fully white blank frame: min > 250
    if min_val > 250.0 and mean_val > 253.0:
        return True
    return False


def sample_video_frames(
    video_path: Path,
    output_dir: Optional[Path] = None,
    max_frames: int = 12,
    max_duration_sec: float = 60.0,
    min_duration_sec: float = 2.0,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Sample up to 12 evenly spaced frames (hard cap 15) including first and last frame.

    Task 2 rules:
    - Never process all frames. Hard cap 15.
    - Includes first and last frame.
    - Skips fully black or blank frames.
    - If shorter than 2s or unopenable, records clear error and skips without crashing.
    - Analyzes at most first 60 seconds; sets is_trimmed flag if trimmed.
    """
    video_info: Dict[str, Any] = {
        "filename": video_path.name,
        "total_frames": 0,
        "fps": 0.0,
        "width": 0,
        "height": 0,
        "duration_seconds": 0.0,
        "is_trimmed": False,
        "trimmed_duration": 0.0,
        "trim_note": "",
        "error": None,
    }

    if not video_path.is_file():
        video_info["error"] = f"Video file not found: {video_path}"
        return video_info, []

    try:
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            video_info["error"] = f"OpenCV failed to open video container: {video_path.name}"
            return video_info, []

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = float(cap.get(cv2.CAP_PROP_FPS)) or 25.0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        duration = total_frames / fps if fps > 0 else 0.0

        video_info.update({
            "total_frames": total_frames,
            "fps": round(fps, 2),
            "width": width,
            "height": height,
            "duration_seconds": round(duration, 2),
        })

        # Duration validation (< 2 seconds)
        if duration < min_duration_sec:
            cap.release()
            video_info["error"] = (
                f"Video duration ({duration:.2f}s) is shorter than minimum required "
                f"{min_duration_sec:.1f} seconds."
            )
            return video_info, []

        if total_frames <= 0:
            cap.release()
            video_info["error"] = "Video container reports 0 readable frames."
            return video_info, []

        # Analyze at most first 60 seconds
        is_trimmed = duration > max_duration_sec
        if is_trimmed:
            effective_frames = int(max_duration_sec * fps)
            effective_frames = min(effective_frames, total_frames)
            video_info["is_trimmed"] = True
            video_info["trimmed_duration"] = max_duration_sec
            video_info["trim_note"] = f"Video ({duration:.1f}s) exceeded 60s; trimmed to first 60.0s for analysis."
        else:
            effective_frames = total_frames
            video_info["is_trimmed"] = False
            video_info["trimmed_duration"] = round(duration, 2)

        # Enforce hard cap: min(max_frames, 15) and at most 12 by default
        effective_max = min(max_frames, 15)
        num_samples = min(effective_max, effective_frames)

        # Generate candidate target indices: strictly include index 0 (first) and effective_frames - 1 (last)
        last_idx = effective_frames - 1
        target_indices = np.linspace(0, last_idx, num_samples, dtype=int)
        target_indices = sorted(list(set(target_indices.tolist())))

        sampled_frames: List[Dict[str, Any]] = []

        if output_dir:
            output_dir.mkdir(parents=True, exist_ok=True)

        for raw_idx in target_indices:
            idx = int(raw_idx)
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = cap.read()

            if not ret or frame is None:
                continue

            # Check for black or blank frame; attempt minor seek nudge if black
            if is_blank_or_black_frame(frame):
                # Try seeking up to 5 frames ahead
                found_valid = False
                for offset in [1, 2, 3, 5, -1, -2]:
                    candidate_idx = idx + offset
                    if 0 <= candidate_idx < effective_frames:
                        cap.set(cv2.CAP_PROP_POS_FRAMES, candidate_idx)
                        r_cand, f_cand = cap.read()
                        if r_cand and f_cand is not None and not is_blank_or_black_frame(f_cand):
                            frame = f_cand
                            idx = candidate_idx
                            found_valid = True
                            break
                if not found_valid:
                    # Still completely black/blank: skip this frame
                    continue

            timestamp = round(float(idx / fps), 3) if fps > 0 else 0.0
            frame_dict = {
                "index": int(idx),
                "timestamp": timestamp,
                "bgr": frame,
                "path": None,
            }

            if output_dir:
                frame_filename = f"frame_{idx:04d}_{timestamp:.2f}s.jpg"
                frame_path = output_dir / frame_filename
                cv2.imwrite(str(frame_path), frame)
                frame_dict["path"] = frame_path

            sampled_frames.append(frame_dict)

        cap.release()

        # Final check: enforce hard cap of 15 frames
        if len(sampled_frames) > 15:
            sampled_frames = sampled_frames[:15]

        return video_info, sampled_frames

    except Exception as e:
        video_info["error"] = f"Frame sampling exception: {str(e)}"
        return video_info, []
