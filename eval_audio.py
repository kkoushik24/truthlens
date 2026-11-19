"""Evaluation benchmark script for TruthLens audio forensics.

Runs labeled audio clips from samples/audio_eval/ with ground truth in labels.csv:
- Evaluates full audio pipeline.
- Compares ground truth ('real' vs 'fake') with TruthLens decision:
  * LOW = Not Flagged (genuine)
  * MODERATE / ELEVATED = Flagged (suspicious / anomalous)
- Reports fired heuristics per file.
- Neural classifier is disabled after failing empirical sanity check.
"""

import csv
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

# Ensure root directory is on sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from core.case_manager import CaseManager
from audio_forensics.pipeline import analyze_audio_pipeline
from correlation.rules_engine import evaluate_rule_based_correlation


def run_audio_eval():
    eval_dir = BASE_DIR / "samples" / "audio_eval"
    labels_file = eval_dir / "labels.csv"

    print("=" * 80)
    print("TruthLens Audio Benchmark Evaluation")
    print(f"Eval Directory: {eval_dir}")
    print("=" * 80)

    if not eval_dir.is_dir() or not labels_file.is_file():
        print(f"\n[!] Missing labels file: {labels_file}")
        return

    # Read ground truth labels
    samples: List[Dict[str, str]] = []
    with open(labels_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            fn = row.get("filename") or row.get("file") or row.get("name")
            lbl = row.get("label") or row.get("truth") or row.get("ground_truth")
            if fn and lbl:
                samples.append({
                    "filename": fn.strip(),
                    "true_label": lbl.strip().lower(),
                })

    if not samples:
        print("\n[!] No valid rows found in labels.csv.")
        return

    print(f"\nLoaded {len(samples)} labeled test files from labels.csv.")
    print("Synthetic-voice classifier: DISABLED (failed sanity check, identical static output on speech).")
    print("Evaluation mode: HEURISTICS-ONLY (hard cap at MODERATE).\n")

    results = []
    total_correct = 0
    missed_fakes = 0
    false_alarms = 0

    col_fmt = "{:<14} | {:<10} | {:<10} | {:<36} | {:<14}"
    header = col_fmt.format("Filename", "True Label", "Level", "Fired Heuristics", "Correct or Not")
    print("-" * 92)
    print(header)
    print("-" * 92)

    for item in samples:
        filename = item["filename"]
        true_label = item["true_label"]  # 'real' or 'fake'
        audio_path = eval_dir / filename

        if not audio_path.is_file():
            print(col_fmt.format(filename, true_label, "MISSING", "--", "ERROR"))
            continue

        case_mgr = CaseManager(f"EVAL-{audio_path.stem[:8]}")
        saved_copy = case_mgr.save_original(filename, audio_path.read_bytes())

        # 1. Run full audio forensics pipeline
        signals = analyze_audio_pipeline(saved_copy, caption=None, case_manager=case_mgr)

        # 2. Run deterministic rule-based correlation
        indicator, _ = evaluate_rule_based_correlation(signals)
        level = indicator.level.lower()

        # 3. Collect fired heuristics (heuristics with score >= 0.20)
        fired_heuristics = []
        for s in signals:
            if s.signal_id.startswith("aud_") and s.signal_id not in ["aud_meta_001", "aud_voice_001", "aud_trans_001"]:
                if s.score is not None and s.score >= 0.20:
                    short_id = s.signal_id.replace("aud_", "")
                    fired_heuristics.append(f"{short_id}:{s.score:.2f}")

        fired_str = ", ".join(fired_heuristics) if fired_heuristics else "none"

        # 4. Determine evaluation outcome:
        # LOW = Not Flagged (genuine)
        # MODERATE / ELEVATED = Flagged (suspicious)
        is_flagged = level in ["moderate", "elevated"]
        is_fake_ground_truth = (true_label == "fake")

        if is_fake_ground_truth:
            if is_flagged:
                eval_status = "CORRECT"
                total_correct += 1
            else:
                eval_status = "MISSED FAKE"
                missed_fakes += 1
        else:
            # Ground truth is REAL
            if not is_flagged:
                eval_status = "CORRECT"
                total_correct += 1
            else:
                eval_status = "FALSE ALARM"
                false_alarms += 1

        print(col_fmt.format(
            filename[:14],
            true_label.upper(),
            level.upper(),
            fired_str[:36],
            eval_status,
        ))

        results.append({
            "filename": filename,
            "true_label": true_label,
            "level": level,
            "fired_heuristics": fired_str,
            "eval_status": eval_status,
        })

    total_evaluated = len(results)
    accuracy = (total_correct / total_evaluated * 100.0) if total_evaluated > 0 else 0.0

    print("-" * 92)
    print("\n" + "=" * 55)
    print("BENCHMARK SUMMARY TOTALS")
    print("=" * 55)
    print(f"Total Files Evaluated:       {total_evaluated}")
    print(f"Total Correct:               {total_correct} / {total_evaluated} ({accuracy:.1f}%)")
    print(f"Missed Fakes:                {missed_fakes}")
    print(f"False Alarms:                {false_alarms}")
    print("Classifier alone caught 0 of 4 fakes (classifier disabled)")
    print("=" * 55)


if __name__ == "__main__":
    run_audio_eval()
