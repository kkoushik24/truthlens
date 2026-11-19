"""Error Level Analysis (ELA) and Compression Heatmap Generation."""

import io
from pathlib import Path
from typing import Optional, Tuple, List
import numpy as np
import cv2
from PIL import Image, ImageChops, ImageEnhance

from core.schemas import Signal, RegionLocation, create_fallback_signal
from core.config import settings


def perform_ela(
    image_path: Path,
    artifact_output_path: Optional[Path] = None,
    quality: int = settings.DEFAULT_ELA_QUALITY,
    scale: int = 15,
) -> Tuple[Signal, Optional[Path]]:
    """Perform Error Level Analysis by recompressing at a fixed JPEG quality,
    
    generating a heatmap artifact, and identifying the highest-error anomaly bounding box.
    If the input is PNG or another lossless format, it is converted to JPEG first.
    """
    filename = image_path.name
    try:
        # 1. Load original image and convert to RGB
        with Image.open(image_path) as original_img:
            original_rgb = original_img.convert("RGB")
            orig_w, orig_h = original_rgb.size

            # Constrain high-resolution phone photos to MAX_IMAGE_PROCESS_DIM
            max_dim = getattr(settings, "MAX_IMAGE_PROCESS_DIM", 1600)
            scale_ratio = 1.0
            if max(orig_w, orig_h) > max_dim:
                scale_ratio = max_dim / float(max(orig_w, orig_h))
                new_w = max(100, int(orig_w * scale_ratio))
                new_h = max(100, int(orig_h * scale_ratio))
                original_rgb = original_rgb.resize((new_w, new_h), Image.Resampling.BILINEAR)

            width, height = original_rgb.size

        # If the input is PNG or another lossless format, convert to JPEG first, then run ELA.
        is_lossless = image_path.suffix.lower() in [".png", ".bmp", ".tiff", ".webp"]
        if is_lossless:
            jpeg_buf = io.BytesIO()
            original_rgb.save(jpeg_buf, format="JPEG", quality=95)
            jpeg_buf.seek(0)
            original_rgb = Image.open(jpeg_buf).convert("RGB")

        # 2. Recompress at target quality in memory
        buffer = io.BytesIO()
        original_rgb.save(buffer, format="JPEG", quality=quality)
        buffer.seek(0)
        recompressed_rgb = Image.open(buffer)

        # 3. Compute absolute difference and scale
        diff = ImageChops.difference(original_rgb, recompressed_rgb)
        extrema = diff.getextrema()
        max_diff = max([ex[1] for ex in extrema]) if extrema else 0
        if max_diff == 0:
            scale_factor = 1.0
        else:
            scale_factor = 255.0 / max_diff

        # Scale difference for human and statistical inspection
        enhanced_diff = ImageEnhance.Brightness(diff).enhance(scale_factor)
        diff_np = np.array(diff)  # (H, W, 3)

        # 4. Calculate error density and detect highest-error region
        gray_diff = cv2.cvtColor(diff_np, cv2.COLOR_RGB2GRAY)
        
        mean_error = float(np.mean(gray_diff))
        std_error = float(np.std(gray_diff))

        # Find the highest error patch
        blurred = cv2.GaussianBlur(gray_diff, (21, 21), 0)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(blurred)

        # Bounding box around peak anomaly
        box_size_w = max(40, int(width * 0.18))
        box_size_h = max(40, int(height * 0.18))

        x_center, y_center = max_loc
        x1 = max(0, x_center - box_size_w // 2)
        y1 = max(0, y_center - box_size_h // 2)
        x2 = min(width, x1 + box_size_w)
        y2 = min(height, y1 + box_size_h)

        if scale_ratio < 1.0:
            inv_scale = 1.0 / scale_ratio
            bbox = [
                min(orig_w, int(x1 * inv_scale)),
                min(orig_h, int(y1 * inv_scale)),
                min(orig_w, int(x2 * inv_scale)),
                min(orig_h, int(y2 * inv_scale)),
            ]
        else:
            bbox = [int(x1), int(y1), int(x2), int(y2)]

        # Error in bbox vs background
        roi = gray_diff[y1:y2, x1:x2]
        roi_mean = float(np.mean(roi)) if roi.size > 0 else mean_error

        # Compute normalized suspicion score [0.0 - 1.0]
        if mean_error > 0:
            divergence_ratio = roi_mean / (mean_error + 1e-5)
        else:
            divergence_ratio = 1.0

        # Plain-English evidence format (Task 8: What we saw / Why it matters / How sure we are)
        if divergence_ratio <= 1.3:
            score = 0.15
            evidence = (
                "Compression looks uniform across the entire image. "
                "There are no obvious signs of pasted or edited sections. "
                "Consistent with an unedited original."
            )
        elif divergence_ratio <= 2.2:
            score = 0.40
            evidence = (
                "Mild compression differences were detected across the image. "
                "This can happen naturally on detailed textures or edges, but can sometimes reflect minor adjustments. "
                "Weak evidence on its own."
            )
        else:
            score = min(0.85, 0.45 + (divergence_ratio - 2.2) * 0.15)
            evidence = (
                "One area of the image compresses differently from the rest. "
                "This can happen when something is edited in, but it also happens naturally on detailed textures. "
                "Weak evidence on its own."
            )

        # 5. Generate and save heatmap overlay artifact
        saved_artifact_path = None
        if artifact_output_path:
            # Create a colored heatmap using OpenCV colormap
            norm_diff = cv2.normalize(gray_diff, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_8U)
            heatmap = cv2.applyColorMap(norm_diff, cv2.COLORMAP_JET)
            heatmap_rgb = cv2.cvtColor(heatmap, cv2.COLOR_BGR2RGB)

            # Draw bounding box on heatmap
            cv2.rectangle(heatmap_rgb, (x1, y1), (x2, y2), (255, 255, 0), 2)
            cv2.putText(
                heatmap_rgb,
                f"Peak Anomaly: {divergence_ratio:.2f}x",
                (x1, max(15, y1 - 6)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (255, 255, 0),
                1,
                cv2.LINE_AA,
            )

            # Blend with original
            orig_np = np.array(original_rgb)
            overlay = cv2.addWeighted(orig_np, 0.55, heatmap_rgb, 0.45, 0)

            # Save overlay artifact
            artifact_output_path.parent.mkdir(parents=True, exist_ok=True)
            overlay_pil = Image.fromarray(overlay)
            overlay_pil.save(artifact_output_path, format="PNG")
            saved_artifact_path = artifact_output_path

        # Mandatory ELA limitation (Task 4)
        ela_limitation = (
            "ELA is unreliable on lossless/PNG files and on fully AI-generated images, which are often uniformly compressed."
        )

        signal = Signal(
            signal_id="img_ela_001",
            modality="image",
            name="Error Level Analysis (ELA) Compression Divergence",
            score=score,
            evidence=evidence,
            location=RegionLocation(bbox=bbox),
            limitation=ela_limitation,
            source_file=filename,
        )

        return signal, saved_artifact_path

    except Exception as e:
        fallback = create_fallback_signal(
            signal_id="img_ela_001",
            modality="image",
            name="Error Level Analysis (ELA) Compression Divergence",
            reason=f"ELA execution failed: {str(e)}",
            source_file=filename,
        )
        return fallback, None
