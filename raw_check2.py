import csv, hashlib, numpy as np, librosa
from transformers import pipeline

d = 'samples/audio_eval'
p = pipeline('audio-classification', model='MelodyMachine/Deepfake-audio-detection-V2')

def fake(y):
    return round({r['label']: r['score'] for r in p(y, top_k=None)}['fake'], 6)

for row in csv.DictReader(open(f'{d}/labels.csv')):
    y, sr = librosa.load(f"{d}/{row['filename']}", sr=16000, mono=True)
    h = hashlib.md5(y.tobytes()).hexdigest()[:8]
    rms = round(float(np.sqrt((y**2).mean())), 4)
    print(row['filename'], row['label'], 'hash', h, 'rms', rms,
          '| fake@orig', fake(y),
          '| fake@0.3x', fake(y*0.3),
          '| fake@+noise', fake((y + np.random.randn(len(y)).astype(np.float32)*0.02).astype(np.float32)),
          '| fake@first1s', fake(y[:16000]))