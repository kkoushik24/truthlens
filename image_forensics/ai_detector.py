"""AI-generated image detector using Hugging Face transformers pipeline."""

import os
import socket
from pathlib import Path
from typing import Optional, Dict, Any
from PIL import Image

from core.schemas import Signal, create_fallback_signal
from core.config import settings

# Global cached pipeline to avoid redundant reloads across calls
_AI_DETECTOR_PIPELINE = None


def is_internet_available(timeout: float = 0.5) -> bool:
    """Fast non-blocking connectivity check via raw IP probe.
    
    Bypasses OS DNS resolution to prevent getaddrinfo hangs in offline environments.
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        # Probe Cloudflare public DNS IP on port 80 without DNS lookup
        res = sock.connect_ex(("1.1.1.1", 80))
        sock.close()
        return res == 0
    except Exception:
        return False


def is_model_cached(model_name: str) -> bool:
    """Check if model weights are actually stored in local Hugging Face cache."""
    try:
        from huggingface_hub import try_to_load_from_cache
        for weight_file in ["pytorch_model.bin", "model.safetensors"]:
            res = try_to_load_from_cache(model_name, weight_file)
            if isinstance(res, str) and Path(res).is_file() and Path(res).stat().st_size > 1000:
                return True
        return False
    except Exception:
        return False


def get_detector_pipeline(model_name: Optional[str] = None):
    """Lazily load and cache the Hugging Face image classification pipeline.
    
    Checks local HF cache first; loads with local_files_only to guarantee zero network lag.
    """
    global _AI_DETECTOR_PIPELINE
    if _AI_DETECTOR_PIPELINE is None:
        target_model = model_name or settings.IMAGE_AI_DETECTOR_MODEL

        cached = is_model_cached(target_model)
        if not cached:
            raise FileNotFoundError(
                f"Model '{target_model}' weights are not pre-cached. Run: python setup_models.py"
            )

        from transformers import AutoImageProcessor, AutoModelForImageClassification, pipeline
        processor = AutoImageProcessor.from_pretrained(target_model, local_files_only=True)
        model = AutoModelForImageClassification.from_pretrained(target_model, local_files_only=True)
        _AI_DETECTOR_PIPELINE = pipeline(
            "image-classification",
            model=model,
            image_processor=processor,
            device=-1,  # CPU strictly
        )
    return _AI_DETECTOR_PIPELINE


def detect_ai_generated_image(
    image_input: Any,
    model_name: Optional[str] = None,
) -> Signal:
    """Classify an image as human-captured vs. AI-generated using a pretrained vision model.
    
    Accepts a Path, PIL.Image, or BGR numpy array.
    Treated strictly as a WEAK signal with comprehensive caveats.
    """
    if isinstance(image_input, (str, Path)):
        image_path = Path(image_input)
        filename = image_path.name
    else:
        filename = "image_frame.jpg"

    selected_model = model_name or settings.IMAGE_AI_DETECTOR_MODEL

    # If model weights are not in local cache, show visible failure instruction
    if not is_model_cached(selected_model):
        return Signal(
            signal_id="img_ai_001",
            modality="image",
            name="AI Image Generator Detection",
            score=None,
            evidence="FAILED: Model not downloaded. Run: python setup_models.py",
            location=None,
            limitation="Model not downloaded. Run: python setup_models.py",
            source_file=filename,
        )

    try:
        classifier = get_detector_pipeline(selected_model)

        if isinstance(image_input, (str, Path)):
            with Image.open(image_input) as img:
                rgb_img = img.convert("RGB")
        elif isinstance(image_input, Image.Image):
            rgb_img = image_input.convert("RGB")
        elif hasattr(image_input, "ndim"):  # numpy array
            import cv2
            rgb = cv2.cvtColor(image_input, cv2.COLOR_BGR2RGB)
            rgb_img = Image.fromarray(rgb)
        else:
            raise TypeError(f"Unsupported image input type: {type(image_input)}")

        # Downscale if image is exceptionally large to prevent CPU bottleneck
        if max(rgb_img.size) > 1024:
            rgb_img.thumbnail((1024, 1024), Image.Resampling.BILINEAR)
        predictions = classifier(rgb_img)

        # Structure of predictions: [{'label': 'artificial', 'score': 0.94}, {'label': 'human', 'score': 0.06}]
        ai_score = 0.0
        label_details = []

        for p in predictions:
            label = str(p.get("label", "")).lower()
            sc = float(p.get("score", 0.0))
            label_details.append(f"{label}: {sc:.2f}")

            # Typical model label names for synthetic: 'artificial', 'fake', 'ai', 'generated'
            if any(k in label for k in ["artificial", "fake", "ai", "synthetic", "generated"]):
                ai_score = max(ai_score, sc)
            # If label is 'real' or 'human', opposite applies
            elif any(k in label for k in ["human", "real", "authentic"]):
                ai_score = max(ai_score, 1.0 - sc)

        # Plain-English non-technical evidence format
        if ai_score >= 0.65:
            evidence_str = (
                f"The image shows visual textures commonly produced by generative AI systems. "
                f"This pattern suggests synthetic generation rather than a photograph captured by a physical camera. "
                f"Model score: {ai_score:.0%} AI probability."
            )
        elif ai_score <= 0.35:
            evidence_str = (
                f"No indicators found by this check: image texture and pixel distribution show standard camera capture patterns. "
                f"Model score: {ai_score:.0%} AI probability."
            )
        else:
            evidence_str = (
                f"The detector found ambiguous image characteristics that could indicate light filtering or subtle AI synthesis. "
                f"Inconclusive without corroborating evidence. "
                f"Model score: {ai_score:.0%} AI probability."
            )

        return Signal(
            signal_id="img_ai_001",
            modality="image",
            name="AI Image Generator Detection",
            score=ai_score,
            evidence=evidence_str,
            location=None,
            limitation="Pretrained synthetic vision detectors may produce false positives on stylized or heavily compressed photos.",
            source_file=filename,
        )

    except Exception as e:
        return create_fallback_signal(
            signal_id="img_ai_001",
            modality="image",
            name="AI Image Generator Detection",
            reason=f"Model inference failed: {str(e)}",
            source_file=filename,
        )
