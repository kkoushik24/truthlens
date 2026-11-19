"""Audio track extraction from video containers using bundled ffmpeg."""

import subprocess
from pathlib import Path
from typing import Optional
import imageio_ffmpeg


def extract_audio_from_video(
    video_path: Path,
    output_wav_path: Path,
    sample_rate: int = 16000,
) -> Optional[Path]:
    """Extract audio track from video file as 16kHz mono 16-bit PCM WAV.
    
    Returns path to extracted WAV file, or None if video has no audio or fails.
    """
    try:
        if not video_path.is_file():
            return None

        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        output_wav_path.parent.mkdir(parents=True, exist_ok=True)

        # Command extracts audio track, converts to mono 16kHz WAV
        cmd = [
            ffmpeg_exe,
            "-y",  # overwrite
            "-i", str(video_path),
            "-vn",  # no video
            "-acodec", "pcm_s16le",
            "-ar", str(sample_rate),
            "-ac", "1",  # mono
            str(output_wav_path),
        ]

        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15.0)

        if proc.returncode == 0 and output_wav_path.is_file() and output_wav_path.stat().st_size > 44:
            return output_wav_path
        return None

    except Exception:
        # Failsafe: app must never crash if audio extraction is unsupported or unavailable
        return None
