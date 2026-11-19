import csv, librosa
from transformers import pipeline

d = 'samples/audio_eval'
p = pipeline('audio-classification', model='MelodyMachine/Deepfake-audio-detection-V2')
for row in csv.DictReader(open(f'{d}/labels.csv')):
    y, sr = librosa.load(f"{d}/{row['filename']}", sr=16000, mono=True)
    out = {r['label']: round(r['score'], 6) for r in p(y, top_k=None)}
    print(row['filename'], row['label'], 'sec:', round(len(y)/sr, 1), 'peak:', round(float(abs(y).max()), 3), out)