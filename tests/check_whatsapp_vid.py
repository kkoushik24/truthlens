import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from video_forensics.pipeline import analyze_video_pipeline
from correlation.rules_engine import evaluate_rule_based_correlation

def main():
    vid_path = BASE_DIR / "samples" / "whatsapp_ai_test_video.mp4"
    if not vid_path.exists():
        print(f"File not found: {vid_path}")
        return

    print("Running analyze_video_pipeline on whatsapp_ai_test_video.mp4...")
    signals, aud = analyze_video_pipeline(vid_path, caption="")
    
    print("\n--- Extracted Signals ---")
    sig_map = {}
    for s in signals:
        sig_map[s.signal_id] = s
        print(f"[{s.signal_id}] {s.name} | Score: {s.score} | Location: {s.location}")
        print(f"   Evidence: {s.evidence}")

    overall, findings = evaluate_rule_based_correlation(signals)

    print("\n--- Correlation Result ---")
    print(f"Level: {overall.level.value if hasattr(overall.level, 'value') else overall.level}")
    print(f"Confidence: {overall.confidence}")
    print(f"Warnings: {overall.warnings}")
    print(f"Primary Drivers: {overall.primary_drivers}")
    print("\n--- Top Drivers Detail ---")
    for pid in overall.primary_drivers:
        s = sig_map.get(pid)
        if s:
            print(f" * [{s.signal_id}] {s.name} (Score: {s.score}): {s.evidence}")

if __name__ == "__main__":
    main()
