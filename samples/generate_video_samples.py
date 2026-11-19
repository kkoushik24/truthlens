"""Generate sample test videos for video forensics testing."""

from pathlib import Path
import numpy as np
import cv2
import subprocess
import imageio_ffmpeg

samples_dir = Path(__file__).resolve().parent
samples_dir.mkdir(parents=True, exist_ok=True)

raw_video_path = samples_dir / "temp_raw_video.mp4"
final_video_path = samples_dir / "sample_video.mp4"

# 1. Create 24 frames of video (2 seconds at 12 fps)
width, height = 160, 120
fps = 12.0
fourcc = cv2.VideoWriter_fourcc(*"mp4v")
out = cv2.VideoWriter(str(raw_video_path), fourcc, fps, (width, height))

for i in range(24):
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    if i == 18:
        # Injected temporal jump: bright red noisy flash
        frame[:, :] = (0, 0, 255)
        noise = np.random.randint(0, 50, (height, width, 3), dtype=np.uint8)
        frame = cv2.add(frame, noise)
    else:
        # Normal gradual gradient
        val = int((i / 24.0) * 180)
        frame[:, :] = (val, 120, 200 - val)

    out.write(frame)

out.release()

# 2. Generate a 2-second sine wave audio track and mux with imageio_ffmpeg
audio_raw_path = samples_dir / "temp_audio.wav"
sr = 16000
t = np.linspace(0, 2.0, int(sr * 2.0), endpoint=False)
audio_sine = (np.sin(2 * np.pi * 440 * t) * 32767).astype(np.int16)

# Write raw WAV manually or using wave
import wave
with wave.open(str(audio_raw_path), "w") as wf:
    wf.setnchannels(1)
    wf.setsampwidth(2)
    wf.setframerate(sr)
    wf.writeframes(audio_sine.tobytes())

# Mux audio and video using imageio_ffmpeg
ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
cmd = [
    ffmpeg_exe, "-y",
    "-i", str(raw_video_path),
    "-i", str(audio_raw_path),
    "-c:v", "libx264",
    "-pix_fmt", "yuv420p",
    "-c:a", "aac",
    str(final_video_path)
]
subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

# Clean up temps
if raw_video_path.exists():
    raw_video_path.unlink()
if audio_raw_path.exists():
    audio_raw_path.unlink()

print(f"Sample video generated successfully at: {final_video_path}")
