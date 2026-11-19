"""Curated forensic limitations and human open-source intelligence verification checks."""

from typing import List
from core.schemas import Signal


def generate_system_limitations(signals: List[Signal]) -> List[str]:
    """Compile comprehensive system and operational caveats grounded in forensic best practices."""
    base_limitations = [
        "A detection score is an INDICATOR of possible modification, NEVER a definitive verdict of forgery or manipulation.",
        "Social media platforms, messaging applications, and Content Delivery Networks (CDNs) routinely strip EXIF metadata, re-compress images (JPEG quantization), and transcode video/audio (H.264/AAC), which can produce artificial tampering signals on unmodified footage.",
        "Pretrained neural network classifiers (AI image and synthetic voice detectors) exhibit high sensitivity to lossy compression, resizing filters, and acoustic reverb, which can inflate false positive rates.",
        "Vision-language models evaluating caption context can occasionally hallucinate visual facts or misread small multilingual signage.",
    ]

    # Add modality-specific limitations if signals of that modality are present
    modalities = set(s.modality for s in signals)
    if "image" in modalities:
        base_limitations.append(
            "Error Level Analysis (ELA) inherently registers higher error rates on high-frequency visual textures (e.g. hair, foliage, sharp text) than on smooth gradients (e.g. skies)."
        )
    if "video" in modalities:
        base_limitations.append(
            "Temporal consistency checks may flag legitimate hard scene cuts, rapid camera pans, strobe lighting, or zoom transitions as discontinuities."
        )
    if "audio" in modalities:
        base_limitations.append(
            "Spectral frequency cutoffs can occur due to smartphone microphone bandwidth restrictions or low-bitrate VoIP codecs without indicating synthetic speech."
        )
        base_limitations.append(
            "Compression, noise reduction, studio recording, phone microphones and text-to-speech readers can produce the same result."
        )

    return base_limitations


def generate_recommended_human_checks(signals: List[Signal]) -> List[str]:
    """Generate prioritized forensic and open-source intelligence (OSINT) checklist for human investigators."""
    modalities = set(s.modality for s in signals)

    # Modality-specific human checks
    if "video" in modalities:
        return [
            "Perform reverse video search on Google Lens / Yandex.",
            "Request original uncompressed recording directly from the source.",
            "Check posting account metadata and origin context.",
            "Verify geographic setting and event timing against verified news reporting.",
        ]

    # When audio is present without video, prioritize exact audio human checks (Task E)
    if "audio" in modalities:
        return [
            "Ask for the original recording directly from the primary source.",
            "Compare with a known genuine sample of the speaker.",
            "Check the source and context of the recording.",
            "Inspect background room tone and breathing cadence consistency in an audio workstation.",
        ]

    checks = [
        "Perform Reverse Image / Video Keyframe Search on Google Lens, TinEye, and Yandex to determine the earliest online timestamp and origin of the visual asset.",
        "Request the original, uncompressed camera file (RAW / DNG / initial camera container) directly from the primary source to inspect camera-firmware cryptographic signatures.",
        "Verify geographic setting and weather conditions using historical satellite imagery (e.g. Google Earth, Sentinel) and meteorological logs for the claimed date and location.",
        "Conduct open-source intelligence (OSINT) cross-verification against reputable local news outlets and eyewitness accounts corresponding to the claimed event.",
    ]

    if "image" in modalities:
        checks.append(
            "Inspect low-level hexadecimal and XMP editing history blocks using ExifTool to identify the exact application and operating system that generated the file."
        )

    return checks
