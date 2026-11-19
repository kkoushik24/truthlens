import numpy as np
from transformers import pipeline

p = pipeline('audio-classification', model='MelodyMachine/Deepfake-audio-detection-V2')
tests = {
    'silence': np.zeros(32000, dtype=np.float32),
    'white noise': np.random.randn(32000).astype(np.float32) * 0.1,
    'sine 440Hz': np.sin(2*np.pi*440*np.arange(32000)/16000).astype(np.float32),
}
for name, y in tests.items():
    print(name, {r['label']: round(r['score'], 6) for r in p(y, top_k=None)})