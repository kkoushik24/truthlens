"""Video container and codec metadata forensics using ffmpeg / OpenCV (Task 4)."""

import subprocess
import re
from pathlib import Path
from typing import Dict, Any, List

import imageio_ffmpeg
from core.schemas import Signal, create_fallback_signal


RE_ENCODING_SIGNATURES = [
    "lavf", "handbrake", "capcut", "premiere", "davinci",
    "adobe", "inshot", "openshot", "filmora", "kinemaster",
    "final cut", "quicktime", "obs", "ffmpeg"
]

METADATA_LIMITATION = (
    "Videos shared via WhatsApp, Instagram or YouTube are re-compressed and lose metadata, "
    "so this is weak evidence."
)


def analyze_video_metadata(video_path: Path) -> Signal:
    """Audit video container format, encoder tags, and stream properties for tampering clues."""
    filename = video_path.name
    try:
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        # Run ffmpeg -i to dump stream headers and container metadata to stderr
        cmd = [ffmpeg_exe, "-i", str(video_path)]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5.0)
        output = proc.stderr or proc.stdout

        evidence_parts: List[str] = []
        # Missing metadata is a weak signal (max 0.35)
        suspicion_score = 0.15

        # 1. Search for encoder / writing application tags
        encoder_match = re.search(r"encoder\s*:\s*([^\r\n]+)", output, re.IGNORECASE)
        encoder_str = encoder_match.group(1).strip() if encoder_match else ""

        found_editors = [sig for sig in RE_ENCODING_SIGNATURES if sig in encoder_str.lower()]
        if found_editors:
            suspicion_score = 0.35  # Weak signal per Task 4
            evidence_parts.append(
                f"Container records re-encoding software signature: '{encoder_str}' (matched: {', '.join(found_editors)})."
            )
        elif encoder_str:
            evidence_parts.append(f"Encoder tag: '{encoder_str}'.")
        else:
            suspicion_score = 0.25  # Weak missing metadata signal
            evidence_parts.append("No explicit container encoder tag found (metadata stripped).")

        # 2. Extract Duration and Bitrate
        dur_match = re.search(r"Duration:\s*(\d+:\d+:\d+\.\d+)", output)
        if dur_match:
            evidence_parts.append(f"Duration: {dur_match.group(1)}.")

        bitrate_match = re.search(r"bitrate:\s*(\d+\s*kb/s)", output)
        if bitrate_match:
            evidence_parts.append(f"Bitrate: {bitrate_match.group(1)}.")

        # 3. Extract Video Stream Codec details
        video_stream_match = re.search(r"Stream #\d+:\d+.*Video:\s*([^\r\n,]+)", output)
        if video_stream_match:
            codec = video_stream_match.group(1).strip()
            evidence_parts.append(f"Video codec: {codec}.")

        # 4. Check for Audio Stream presence
        audio_stream_match = re.search(r"Stream #\d+:\d+.*Audio:\s*([^\r\n,]+)", output)
        if not audio_stream_match:
            evidence_parts.append("No embedded audio stream detected.")
        else:
            evidence_parts.append(f"Audio stream: {audio_stream_match.group(1).strip()}.")

        final_evidence = " ".join(evidence_parts)

        return Signal(
            signal_id="vid_meta_001",
            modality="video",
            name="Video Container & Codec Metadata",
            score=min(0.35, round(suspicion_score, 2)),
            evidence=final_evidence,
            location=None,
            limitation=METADATA_LIMITATION,
            source_file=filename,
        )

    except Exception as e:
        return create_fallback_signal(
            signal_id="vid_meta_001",
            modality="video",
            name="Video Container & Codec Metadata",
            source_file=filename,
            reason=f"FFmpeg metadata inspection failed: {str(e)}",
            limitation=METADATA_LIMITATION,
        )
