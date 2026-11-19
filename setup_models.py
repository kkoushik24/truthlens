"""TruthLens Pretrained Models Setup & Cache Script.

Downloads and caches models used across TruthLens:
1. umm-maybe/AI-image-detector (Hugging Face Vision Transformer)
2. MelodyMachine/Deepfake-audio-detection-V2 (Synthetic Voice / Deepfake Classifier)
"""

import os
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import requests


def download_file_parallel(url: str, dest_path: Path, expected_size: int, num_chunks: int = 8) -> bool:
    """Download a large file with parallel byte ranges for fast, reliable transfer."""
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    dest_str = str(dest_path)

    # First resolve redirect to get direct CDN url
    s = requests.Session()
    r = s.head(url, allow_redirects=True, timeout=25)
    direct_url = r.url
    chunk_size = (expected_size + num_chunks - 1) // num_chunks

    def _worker(idx):
        start = idx * chunk_size
        end = min(start + chunk_size - 1, expected_size - 1)
        headers = {"Range": f"bytes={start}-{end}"}
        part_path = f"{dest_str}.part{idx}"
        resp = requests.get(direct_url, headers=headers, stream=True, timeout=90)
        with open(part_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=131072):
                if chunk:
                    f.write(chunk)

    print(f"  Downloading in {num_chunks} parallel streams ({expected_size / (1024*1024):.1f} MB)...")
    with ThreadPoolExecutor(max_workers=num_chunks) as executor:
        list(executor.map(_worker, range(num_chunks)))

    # Combine parts into final file
    with open(dest_str, "wb") as outfile:
        for idx in range(num_chunks):
            part_path = f"{dest_str}.part{idx}"
            if os.path.exists(part_path):
                with open(part_path, "rb") as infile:
                    outfile.write(infile.read())
                try:
                    os.remove(part_path)
                except Exception:
                    pass

    return os.path.exists(dest_str) and os.path.getsize(dest_str) == expected_size


def download_image_detector():
    print("[1/2] Checking AI Image Detector (umm-maybe/AI-image-detector)...")
    try:
        from transformers import AutoImageProcessor, AutoModelForImageClassification
        model_name = "umm-maybe/AI-image-detector"
        AutoImageProcessor.from_pretrained(model_name)

        # Check if pytorch_model.bin is already cached
        cache_dir = Path.home() / ".cache" / "huggingface" / "hub" / "models--umm-maybe--AI-image-detector" / "snapshots" / "c7e223baf11bc40528af364ba7bdea030ef42f9e"
        weight_file = cache_dir / "pytorch_model.bin"
        expected_size = 347596479

        if not weight_file.is_file() or weight_file.stat().st_size != expected_size:
            download_url = f"https://huggingface.co/{model_name}/resolve/main/pytorch_model.bin"
            ok = download_file_parallel(download_url, weight_file, expected_size)
            if not ok:
                raise IOError("Failed to download pytorch_model.bin to expected size")

        # Verify model loads
        AutoModelForImageClassification.from_pretrained(model_name)
        print("  --> OK: umm-maybe/AI-image-detector cached and verified.")
        return True, "OK"
    except Exception as e:
        print(f"  --> FAILED: {e}")
        return False, str(e)


def download_audio_model():
    print("[2/2] Downloading Synthetic-Voice Classifier (MelodyMachine/Deepfake-audio-detection-V2)...")
    try:
        from transformers import AutoFeatureExtractor, AutoModelForAudioClassification
        model_name = "MelodyMachine/Deepfake-audio-detection-V2"
        print("  Downloading feature extractor and weights via Hugging Face Hub...")
        AutoFeatureExtractor.from_pretrained(model_name)
        AutoModelForAudioClassification.from_pretrained(model_name)
        print("  --> OK: MelodyMachine/Deepfake-audio-detection-V2 cached and verified.")
        return True, "OK"
    except Exception as e:
        print(f"  --> FAILED: {e}")
        return False, str(e)


def main():
    print("=" * 60)
    print("TruthLens Pretrained Model Cache Setup")
    print("=" * 60)

    results = {}
    ok_img, msg_img = download_image_detector()
    results["umm-maybe/AI-image-detector"] = "OK" if ok_img else f"FAILED: {msg_img}"

    ok_aud, msg_aud = download_audio_model()
    results["MelodyMachine/Deepfake-audio-detection-V2"] = "OK" if ok_aud else f"FAILED: {msg_aud}"

    print("\n" + "=" * 60)
    print("Model Setup Summary:")
    print("=" * 60)
    for model, status in results.items():
        print(f" - {model}: {status}")


if __name__ == "__main__":
    main()
