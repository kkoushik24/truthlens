"""EXIF and container metadata forensics for images."""

from pathlib import Path
from typing import Optional, Dict, Any, List
from PIL import Image, ExifTags
from datetime import datetime

from core.schemas import Signal, create_fallback_signal


EDITING_SIGNATURES = [
    "photoshop", "adobe", "gimp", "canva", "lightroom", "midjourney",
    "stable diffusion", "dall-e", "paint.net", "procreate", "snapseed",
    "pixlr", "affinity", "coreldraw", "vsco"
]


def analyze_exif(image_path: Path) -> Signal:
    """Analyze EXIF metadata for tampering clues, software tags, and missing headers."""
    filename = image_path.name
    try:
        with Image.open(image_path) as img:
            exif_data = img.getexif()

        if not exif_data:
            return Signal(
                signal_id="img_exif_001",
                modality="image",
                name="EXIF Metadata Audit",
                score=0.35,
                evidence=(
                    "EXIF metadata is completely absent. While typical for web and messaging "
                    "platforms that strip metadata during upload, raw camera captures consistently retain EXIF tags."
                ),
                location=None,
                limitation="Social media platforms (WhatsApp, X, Instagram) strip EXIF by default. Absence alone does not prove malicious manipulation.",
                source_file=filename,
            )

        # Parse tags
        decoded_tags: Dict[str, Any] = {}
        for tag_id, value in exif_data.items():
            tag_name = ExifTags.TAGS.get(tag_id, str(tag_id))
            decoded_tags[tag_name] = value

        evidence_points: List[str] = []
        suspicion_score = 0.1

        # 1. Check for editing software tags
        raw_software = str(decoded_tags.get("Software", "")).strip()
        raw_processing = str(decoded_tags.get("ProcessingSoftware", "")).strip()
        combined_software_raw = f"{raw_software} {raw_processing}".strip()
        combined_software_lower = combined_software_raw.lower()

        found_editors = [ed for ed in EDITING_SIGNATURES if ed in combined_software_lower]
        if found_editors:
            suspicion_score = max(suspicion_score, 0.75)
            evidence_points.append(
                f"Image metadata explicitly records editing software tag: '{combined_software_raw}' (matched: {', '.join(found_editors)})."
            )

        # 2. Check camera make and model
        make = decoded_tags.get("Make")
        model = decoded_tags.get("Model")
        if make or model:
            evidence_points.append(f"Camera hardware identified: {make or ''} {model or ''}".strip() + ".")
        else:
            suspicion_score = max(suspicion_score, 0.3)
            evidence_points.append("Camera hardware tags (Make/Model) are missing despite other EXIF blocks being present.")

        # 3. Check timestamps
        date_time_str = decoded_tags.get("DateTime") or decoded_tags.get("DateTimeOriginal")
        if date_time_str:
            try:
                # Format typically 'YYYY:MM:DD HH:MM:SS'
                clean_date = str(date_time_str).strip()
                dt = datetime.strptime(clean_date, "%Y:%m:%d %H:%M:%S")
                if dt.year > datetime.now().year + 1:
                    suspicion_score = max(suspicion_score, 0.8)
                    evidence_points.append(f"Anomalous future timestamp found in EXIF: {clean_date}.")
                else:
                    evidence_points.append(f"Capture timestamp recorded: {clean_date}.")
            except Exception:
                evidence_points.append(f"Capture timestamp string present: '{date_time_str}'.")

        if not evidence_points:
            evidence_points.append("Standard EXIF metadata present without obvious manipulation signatures.")

        final_evidence = " ".join(evidence_points)

        return Signal(
            signal_id="img_exif_001",
            modality="image",
            name="EXIF Metadata Audit",
            score=round(suspicion_score, 2),
            evidence=final_evidence,
            location=None,
            limitation=(
                "EXIF metadata can be trivially edited, forged, or stripped using standard command-line tools. "
                "Presence of editing software can indicate harmless cropping or color correction rather than malicious forgery."
            ),
            source_file=filename,
        )

    except Exception as e:
        return create_fallback_signal(
            signal_id="img_exif_001",
            modality="image",
            name="EXIF Metadata Audit",
            source_file=filename,
            reason=f"Failed to read or parse EXIF metadata: {str(e)}",
            limitation="Corrupt or non-standard image headers prevented metadata extraction.",
        )
