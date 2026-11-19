from pathlib import Path
import librosa
from audio_forensics.voice_detector import get_voice_pipeline

pipe = get_voice_pipeline()

eval_files = sorted(list(Path("samples/audio_eval").glob("*.wav")))
for p in eval_files:
    y, sr = librosa.load(str(p), sr=16000, mono=True)
    res = pipe({"raw": y, "sampling_rate": 16000})
    formatted = " | ".join([f"{r['label']}: {r['score']:.6f}" for r in res])
    print(f"{p.name:<12} -> {formatted}")
