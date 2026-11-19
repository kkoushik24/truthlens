"""Per-frame AI image detection and multi-frame aggregation for video forensics (Task 3)."""

from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import cv2
import numpy as np

from core.schemas import Signal, FrameLocation
from core.config import settings
from image_forensics.ai_detector import detect_ai_generated_image


def detect_face_crop(bgr: np.ndarray) -> Optional[np.ndarray]:
    """Detect the largest frontal face in frame and return cropped region with margin."""
    if bgr is None or bgr.size == 0:
        return None
    try:
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        face_cascade = cv2.CascadeClassifier(cascade_path)
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(60, 60))
        if len(faces) == 0:
            return None
        # Pick largest face
        x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
        # Add 15% margin
        h_pad = int(h * 0.15)
        w_pad = int(w * 0.15)
        H, W = bgr.shape[:2]
        y1, y2 = max(0, y - h_pad), min(H, y + h + h_pad)
        x1, x2 = max(0, x - w_pad), min(W, x + w + w_pad)
        crop = bgr[y1:y2, x1:x2]
        return crop if crop.size > 0 else None
    except Exception:
        return None


def compute_keyframe_aggregate(scores: List[float]) -> Tuple[float, float, float]:
    """Compute (aggregate_score, top_3_mean, max_score) from list of frame scores (Task 3)."""
    if not scores:
        return 0.0, 0.0, 0.0
    sorted_scores = sorted(scores, reverse=True)
    max_score = float(sorted_scores[0])
    top_k = min(3, len(sorted_scores))
    top_3_mean = float(np.mean(sorted_scores[:top_k]))
    agg_score = max(top_3_mean, max_score)
    return round(agg_score, 4), round(top_3_mean, 4), round(max_score, 4)


def analyze_video_frames_ai(
    sampled_frames: List[Dict[str, Any]],
    source_file: str,
    detector_models: Optional[List[str]] = None,
) -> Tuple[Signal, List[Dict[str, Any]]]:
    """Evaluate each sampled keyframe with configured AI image detector models (Task 3).

    Rules:
    - Runs every configured AI detector in config.py on each frame.
    - If OpenCV detects a face, runs detector on face crop and takes the higher score.
    - Aggregates using higher of: (a) mean of top-3 frame scores, (b) max frame score.
    - Never plain-averages all frames.
    - Records per-frame scores and timestamps.
    """
    models_to_run = detector_models or getattr(settings, "IMAGE_AI_DETECTOR_MODELS", [settings.IMAGE_AI_DETECTOR_MODEL])

    if not sampled_frames:
        return Signal(
            signal_id="vid_ai_001",
            modality="video",
            name="Video Keyframe AI Detection",
            score=None,
            evidence="SKIPPED: No sampled frames available for AI detection.",
            location=None,
            limitation="Frame extraction required for per-frame AI evaluation.",
            source_file=source_file,
        ), []

    per_frame_records: List[Dict[str, Any]] = []

    for item in sampled_frames:
        idx = int(item["index"])
        ts = float(item["timestamp"])
        bgr = item.get("bgr")
        frame_path = item.get("path")

        # Highest score across all configured models for this frame
        frame_best_score = 0.0
        face_flag = False

        for model_name in models_to_run:
            # 1. Evaluate full frame
            if bgr is not None:
                sig_full = detect_ai_generated_image(bgr, model_name=model_name)
            elif frame_path and Path(frame_path).is_file():
                sig_full = detect_ai_generated_image(frame_path, model_name=model_name)
            else:
                continue

            full_score = sig_full.score if sig_full.score is not None else 0.0
            frame_best_score = max(frame_best_score, full_score)

            # 2. Face crop evaluation (if face present)
            if bgr is not None:
                face_crop = detect_face_crop(bgr)
                if face_crop is not None:
                    face_flag = True
                    sig_face = detect_ai_generated_image(face_crop, model_name=model_name)
                    if sig_face.score is not None:
                        frame_best_score = max(frame_best_score, sig_face.score)

        per_frame_records.append({
            "index": idx,
            "timestamp": ts,
            "score": round(frame_best_score, 4),
            "has_face": face_flag,
            "path": str(frame_path) if frame_path else None,
        })

    # Sort descending by score
    sorted_records = sorted(per_frame_records, key=lambda r: r["score"], reverse=True)
    top_record = sorted_records[0]
    max_frame_score = float(top_record["score"])

    # Compute top-3 mean and aggregation
    all_scores = [float(r["score"]) for r in sorted_records]
    agg_score, top_3_mean, max_frame_score = compute_keyframe_aggregate(all_scores)

    # Build evidence text naming top frame number and timestamp
    if agg_score >= 0.50:
        evidence = (
            f"Keyframe #{top_record['index']} at timestamp {top_record['timestamp']:.2f}s "
            f"shows visual textures commonly produced by generative AI systems (score: {top_record['score']:.0%}). "
            f"Top-3 frame average: {top_3_mean:.0%}, peak frame score: {max_frame_score:.0%} across {len(sampled_frames)} frames."
        )
    else:
        evidence = (
            f"No indicators found by this check across {len(sampled_frames)} sampled keyframes. "
            f"Peak frame score: {max_frame_score:.0%} (Frame #{top_record['index']} at {top_record['timestamp']:.2f}s), "
            f"top-3 frame average: {top_3_mean:.0%}."
        )

    signal = Signal(
        signal_id="vid_ai_001",
        modality="video",
        name="Video Keyframe AI Detection",
        score=round(agg_score, 4),
        evidence=evidence,
        location=FrameLocation(index=int(top_record["index"])),
        limitation=(
            "AI image detectors evaluate static texture artifacts. Heavy video compression, "
            "motion blur, or low resolution can mask synthetic patterns or cause false alarms."
        ),
        source_file=source_file,
    )

    return signal, per_frame_records


def generate_per_frame_score_chart(
    per_frame_records: List[Dict[str, Any]],
    output_path: Path,
) -> Optional[Path]:
    """Generate line chart of AI detector score per sampled frame (Task 6)."""
    if not per_frame_records:
        return None
    try:
        import os, tempfile
        if "MPLCONFIGDIR" not in os.environ:
            os.environ["MPLCONFIGDIR"] = tempfile.gettempdir()
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        output_path.parent.mkdir(parents=True, exist_ok=True)
        timestamps = [r["timestamp"] for r in per_frame_records]
        scores = [r["score"] for r in per_frame_records]
        indices = [r["index"] for r in per_frame_records]

        fig, ax = plt.subplots(figsize=(8, 3.5), dpi=100)
        ax.plot(timestamps, scores, marker="o", color="#e63946", linewidth=2.0, label="AI Detector Score")
        ax.axhline(0.50, color="#f4a261", linestyle="--", alpha=0.7, label="Moderate Threshold (0.50)")
        ax.axhline(0.65, color="#d62828", linestyle=":", alpha=0.7, label="Elevated Threshold (0.65)")

        # Mark peak frame
        max_idx = int(np.argmax(scores))
        ax.scatter([timestamps[max_idx]], [scores[max_idx]], color="#d62828", s=100, zorder=5)
        ax.annotate(
            f"Peak: Frame #{indices[max_idx]} ({scores[max_idx]:.0%})",
            (timestamps[max_idx], scores[max_idx]),
            textcoords="offset points",
            xytext=(0, 10),
            ha="center",
            fontsize=9,
            weight="bold",
        )

        ax.set_title("AI Detector Suspicion Score Per Sampled Keyframe", fontsize=11, weight="bold")
        ax.set_xlabel("Video Timestamp (seconds)")
        ax.set_ylabel("AI Probability Score")
        ax.set_ylim(-0.05, 1.05)
        ax.grid(True, linestyle=":", alpha=0.6)
        ax.legend(loc="lower right", fontsize=8)
        plt.tight_layout()
        plt.savefig(str(output_path))
        plt.close(fig)
        return output_path
    except Exception:
        return None
