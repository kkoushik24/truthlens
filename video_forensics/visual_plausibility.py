"""Video visual plausibility and caption alignment using Groq Vision API (Task 4)."""

import base64
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import cv2
import numpy as np
from PIL import Image
import io

from core.schemas import Signal, FrameLocation, create_fallback_signal
from core.config import settings


def _frame_to_b64(bgr_or_path: Any, max_dim: int = 768, quality: int = 80) -> str:
    """Encode image to base64 JPEG (< 200 KB) for Groq Vision."""
    if isinstance(bgr_or_path, (str, Path)):
        img = Image.open(str(bgr_or_path)).convert("RGB")
    elif hasattr(bgr_or_path, "ndim"):
        rgb = cv2.cvtColor(bgr_or_path, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(rgb)
    else:
        raise TypeError("Invalid image input")

    if max(img.size) > max_dim:
        img.thumbnail((max_dim, max_dim), Image.Resampling.BILINEAR)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality, optimize=True)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def select_five_candidate_frames(
    sampled_frames: List[Dict[str, Any]],
    per_frame_ai_records: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """Select 5 keyframes: first, last, middle, and 2 highest-detector-score frames."""
    if not sampled_frames:
        return []

    candidates_by_index: Dict[int, Dict[str, Any]] = {}

    # 1. First frame
    candidates_by_index[sampled_frames[0]["index"]] = sampled_frames[0]

    # 2. Last frame
    candidates_by_index[sampled_frames[-1]["index"]] = sampled_frames[-1]

    # 3. Middle frame
    mid_idx = len(sampled_frames) // 2
    candidates_by_index[sampled_frames[mid_idx]["index"]] = sampled_frames[mid_idx]

    # 4. Two highest detector score frames
    if per_frame_ai_records:
        sorted_ai = sorted(per_frame_ai_records, key=lambda r: r.get("score", 0.0), reverse=True)
        for r in sorted_ai[:2]:
            idx = r.get("index")
            match = next((f for f in sampled_frames if f["index"] == idx), None)
            if match:
                candidates_by_index[idx] = match

    # If still fewer than 5 and more sampled frames exist, fill in
    for f in sampled_frames:
        if len(candidates_by_index) >= 5:
            break
        candidates_by_index[f["index"]] = f

    return sorted(list(candidates_by_index.values()), key=lambda f: f["index"])


def check_video_visual_plausibility(
    sampled_frames: List[Dict[str, Any]],
    per_frame_ai_records: Optional[List[Dict[str, Any]]],
    source_file: str,
) -> Signal:
    """Send 5 frames to Groq vision model for physical plausibility and AI anatomy artifacts (Task 4)."""
    selected_frames = select_five_candidate_frames(sampled_frames, per_frame_ai_records)
    if not selected_frames:
        return Signal(
            signal_id="vid_plaus_001",
            modality="video",
            name="Video Visual Plausibility & Physics Audit",
            score=None,
            evidence="SKIPPED: No frames available for visual plausibility audit.",
            location=None,
            limitation="Plausibility audit requires sampled keyframes.",
            source_file=source_file,
        )

    if not settings.GROQ_API_KEY or len(settings.GROQ_API_KEY.strip()) < 5:
        return Signal(
            signal_id="vid_plaus_001",
            modality="video",
            name="Video Visual Plausibility & Physics Audit",
            score=None,
            evidence="SKIPPED: GROQ_API_KEY not configured in .env file.",
            location=None,
            limitation="Vision-language model inspection requires an active LLM API key.",
            source_file=source_file,
        )

    model_name = settings.GROQ_VISION_MODEL

    try:
        from groq import Groq
        client = Groq(api_key=settings.GROQ_API_KEY)

        # Build multimodal message with selected frames (send 2-3 frames per request if needed)
        content_parts: List[Dict[str, Any]] = [
            {
                "type": "text",
                "text": (
                    "You are a forensic video auditor evaluating sampled keyframes from a video for generative AI synthesis artifacts.\n"
                    "Inspect the sequence for: warped fingers/hands/faces, inconsistent objects across frames, floating elements, surreal lighting, and impossible physical motion.\n"
                    "Respond ONLY with a valid JSON object strictly matching this schema:\n"
                    "{\n"
                    '  "physically_plausible": true,\n'
                    '  "impossible_elements": [],\n'
                    '  "ai_generated_look": 0.15,\n'
                    '  "reason": "one plain-English sentence describing your observations"\n'
                    "}"
                ),
            }
        ]

        for f in selected_frames[:5]:
            frame_input = f.get("bgr") if f.get("bgr") is not None else f.get("path")
            b64_str = _frame_to_b64(frame_input)
            content_parts.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{b64_str}"},
            })

        # Safe execution with short timeout
        response_text = None
        for attempt in range(1):
            try:
                chat_resp = client.chat.completions.create(
                    model=model_name,
                    messages=[{"role": "user", "content": content_parts}],
                    response_format={"type": "json_object"},
                    timeout=5.0,
                )
                response_text = chat_resp.choices[0].message.content
                break
            except Exception as call_err:
                err_str = str(call_err).lower()
                if "model_not_found" in err_str or "not found" in err_str or "deprecated" in err_str:
                    return Signal(
                        signal_id="vid_plaus_001",
                        modality="video",
                        name="Video Visual Plausibility & Physics Audit",
                        score=None,
                        evidence=f"FAILED: Groq vision model '{model_name}' not found or deprecated. Please update GROQ_VISION_MODEL in core/config.py or .env.",
                        location=None,
                        limitation="Model deprecation prevents vision inspection.",
                        source_file=source_file,
                    )
                raise call_err

        if not response_text:
            raise RuntimeError("Empty response received from Groq vision API.")

        # Strip code fences and parse JSON
        clean_json = re.sub(r"^```(?:json)?\s*", "", response_text.strip(), flags=re.IGNORECASE)
        clean_json = re.sub(r"\s*```$", "", clean_json)
        parsed = json.loads(clean_json)

        plausible = bool(parsed.get("physically_plausible", True))
        impossible = list(parsed.get("impossible_elements", []))
        ai_look = float(parsed.get("ai_generated_look", 0.20))
        reason = str(parsed.get("reason", "Visual plausibility check completed."))

        if not plausible or len(impossible) > 0:
            score = max(ai_look, 0.75)
            evidence = (
                f"Unusual visual characteristics were found: impossible physical or anatomical elements detected "
                f"({', '.join(impossible) if impossible else 'inconsistent motion/textures'}). {reason}"
            )
        elif ai_look >= 0.50:
            score = ai_look
            evidence = f"Unusual visual characteristics were found: {reason}"
        else:
            score = ai_look
            evidence = f"No indicators found by this check: {reason}"

        return Signal(
            signal_id="vid_plaus_001",
            modality="video",
            name="Video Visual Plausibility & Physics Audit",
            score=round(min(1.0, max(0.0, score)), 2),
            evidence=evidence,
            location=None,
            limitation=(
                "Vision-language models evaluating physical plausibility can occasionally misinterpret "
                "surreal art, deliberate editing, or low-light motion blur as generative synthesis."
            ),
            source_file=source_file,
        )

    except json.JSONDecodeError as jerr:
        return Signal(
            signal_id="vid_plaus_001",
            modality="video",
            name="Video Visual Plausibility & Physics Audit",
            score=None,
            evidence=f"FAILED: Invalid JSON from vision model: {str(jerr)}",
            location=None,
            limitation="Vision model returned malformed output.",
            source_file=source_file,
        )
    except Exception as e:
        err_msg = str(e)
        if "model_not_found" in err_msg.lower() or "deprecated" in err_msg.lower():
            reason_txt = f"FAILED: Groq vision model '{model_name}' not found or deprecated. Please update GROQ_VISION_MODEL in core/config.py."
        else:
            reason_txt = f"FAILED: Groq vision API error: {err_msg}"
        return Signal(
            signal_id="vid_plaus_001",
            modality="video",
            name="Video Visual Plausibility & Physics Audit",
            score=None,
            evidence=reason_txt,
            location=None,
            limitation="Vision API network or inference error.",
            source_file=source_file,
        )


def check_video_caption_alignment(
    sampled_frames: List[Dict[str, Any]],
    caption: Optional[str],
    source_file: str,
) -> Signal:
    """Compare video frames against submitted text caption using Groq Vision (Task 4)."""
    # Rule: If no caption: "SKIPPED: no caption provided", excluded from scoring
    if not caption or not caption.strip():
        return Signal(
            signal_id="vid_cap_001",
            modality="video",
            name="Video vs Caption Claim Alignment",
            score=None,
            evidence="SKIPPED: no caption provided",
            location=None,
            limitation="Caption verification requires both a video file and an external claim.",
            source_file=source_file,
        )

    if not settings.GROQ_API_KEY or len(settings.GROQ_API_KEY.strip()) < 5:
        return Signal(
            signal_id="vid_cap_001",
            modality="video",
            name="Video vs Caption Claim Alignment",
            score=None,
            evidence="SKIPPED: GROQ_API_KEY not configured in .env file.",
            location=None,
            limitation="Vision API required for cross-modal caption alignment.",
            source_file=source_file,
        )

    model_name = settings.GROQ_VISION_MODEL
    try:
        from groq import Groq
        client = Groq(api_key=settings.GROQ_API_KEY)

        # Select up to 3 evenly spaced frames for caption cross-check
        indices = np.linspace(0, len(sampled_frames) - 1, min(3, len(sampled_frames)), dtype=int)
        sub_frames = [sampled_frames[i] for i in indices]

        content_parts: List[Dict[str, Any]] = [
            {
                "type": "text",
                "text": (
                    f"Evaluate if these video keyframes match or contradict the external claim: \"{caption}\".\n"
                    "Respond ONLY with a JSON object: {\"matches\": true, \"suspicion_score\": <0.1 to 0.8>, \"reason\": \"one sentence\"}."
                ),
            }
        ]

        for f in sub_frames:
            frame_input = f.get("bgr") if f.get("bgr") is not None else f.get("path")
            b64_str = _frame_to_b64(frame_input)
            content_parts.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{b64_str}"},
            })

        resp = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": content_parts}],
            response_format={"type": "json_object"},
            timeout=15.0,
        )
        parsed = json.loads(resp.choices[0].message.content)
        suspicion = float(parsed.get("suspicion_score", 0.20))
        reason = str(parsed.get("reason", "Caption evaluated against keyframes."))

        return Signal(
            signal_id="vid_cap_001",
            modality="video",
            name="Video vs Caption Claim Alignment",
            score=round(min(1.0, max(0.0, suspicion)), 2),
            evidence=reason,
            location=None,
            limitation="Lexical and visual caption alignment cannot detect nuanced satire or parody context.",
            source_file=source_file,
        )

    except Exception as e:
        return Signal(
            signal_id="vid_cap_001",
            modality="video",
            name="Video vs Caption Claim Alignment",
            score=None,
            evidence=f"FAILED: Caption comparison failed: {str(e)}",
            location=None,
            limitation="Vision model error during caption verification.",
            source_file=source_file,
        )
