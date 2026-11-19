"""Verification script for cached synthetic-voice classifier.
Prints id2label mapping and compares raw outputs on unlabeled test clip (samples/1.wav)
and DSP test chord (samples/synthetic_chord_test.wav).
"""

from pathlib import Path
from transformers import AutoFeatureExtractor, AutoModelForAudioClassification, pipeline
import librosa

MODEL_NAME = "MelodyMachine/Deepfake-audio-detection-V2"

def main():
    print("=" * 65)
    print(f"VERIFYING CACHED MODEL: {MODEL_NAME}")
    print("=" * 65)

    # 1. Print id2label mapping
    print("\n[Step 1] Loading model configuration...")
    feature_extractor = AutoFeatureExtractor.from_pretrained(MODEL_NAME)
    model = AutoModelForAudioClassification.from_pretrained(MODEL_NAME)
    
    print(f"id2label: {model.config.id2label}")
    print(f"label2id: {model.config.label2id}")
    
    # Identify which label corresponds to synthetic vs real
    print("\nLabel Semantics Analysis:")
    for label_id, label_name in model.config.id2label.items():
        lname = label_name.lower()
        if any(k in lname for k in ["fake", "synthetic", "spoof", "generated"]):
            meaning = "SYNTHETIC / AI-GENERATED SPEECH"
        elif any(k in lname for k in ["real", "bonafide", "human", "authentic"]):
            meaning = "GENUINE / HUMAN SPEECH"
        else:
            meaning = "UNKNOWN (Requires user clarification)"
        print(f"  * ID {label_id} -> '{label_name}' = {meaning}")

    pipe = pipeline("audio-classification", model=model, feature_extractor=feature_extractor)

    # 2. Raw output on samples/1.wav (Unlabeled Clip)
    print("\n" + "-" * 65)
    print("[Step 2] Raw per-label output for unlabeled test clip: samples/1.wav")
    print("-" * 65)
    y_test, sr_test = librosa.load("samples/1.wav", sr=16000, mono=True)
    res_test = pipe(y_test)
    for r in res_test:
        print(f"  - Label: {r['label']:<10} Score: {r['score']:.4f}")

    # 3. Raw output on real speech clip: samples/audio_eval/real_1.wav
    print("\n" + "-" * 65)
    print("[Step 3] Raw per-label output for REAL voice clip: samples/audio_eval/real_1.wav")
    print("-" * 65)
    y_real, sr_real = librosa.load("samples/audio_eval/real_1.wav", sr=16000, mono=True)
    res_real = pipe(y_real)
    for r in res_real:
        print(f"  - Label: {r['label']:<10} Score: {r['score']:.4f}")

    # 4. Raw output on fake speech clip: samples/audio_eval/fake_1.wav
    print("\n" + "-" * 65)
    print("[Step 4] Raw per-label output for FAKE voice clip: samples/audio_eval/fake_1.wav")
    print("-" * 65)
    y_fake, sr_fake = librosa.load("samples/audio_eval/fake_1.wav", sr=16000, mono=True)
    res_fake = pipe(y_fake)
    for r in res_fake:
        print(f"  - Label: {r['label']:<10} Score: {r['score']:.4f}")

    print("\n" + "=" * 65)

if __name__ == "__main__":
    main()
