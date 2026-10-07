from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.analyzer import analyze

DATASET_PATH = ROOT / "data" / "test_messages.json"
REAL_PATH = ROOT / "data" / "real_messages_template.json"


def metrics_for(entries):
    total = len(entries)
    correct = 0
    false_positives = 0
    false_negatives = 0
    by_type = {}
    results = []
    for entry in entries:
        result = analyze(entry["text"], "accuracy")
        expected = entry["expected_verdict"]
        label = result.verdict
        results.append((entry, label))
        if label == expected:
            correct += 1
        else:
            if expected == "safe" and label != "safe":
                false_positives += 1
            if expected == "scam" and label != "scam":
                false_negatives += 1
        key = entry.get("type", "unknown")
        by_type.setdefault(key, {"total": 0, "correct": 0, "wrong": 0})
        by_type[key]["total"] += 1
        if label == expected:
            by_type[key]["correct"] += 1
        else:
            by_type[key]["wrong"] += 1
    accuracy = (correct / total * 100) if total else 0.0
    predicted_scams = sum(1 for _, label in results if label == "scam")
    true_positives = sum(
        1
        for entry, label in results
        if entry["expected_verdict"] == "scam"
        and label == "scam"
    )
    precision = (true_positives / predicted_scams * 100) if predicted_scams else 0.0
    scam_total = sum(1 for e in entries if e["expected_verdict"] == "scam")
    recall = (true_positives / scam_total * 100) if scam_total else 0.0
    return {
        "total": total,
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "false_positives": false_positives,
        "false_negatives": false_negatives,
        "by_type": by_type,
    }


def main() -> None:
    entries = json.loads(DATASET_PATH.read_text(encoding="utf-8")) if DATASET_PATH.exists() else []
    real_entries = json.loads(REAL_PATH.read_text(encoding="utf-8")) if REAL_PATH.exists() else []
    measured_real = [entry for entry in real_entries if not entry.get("fictional", False)]
    synthetic = metrics_for(entries)
    print("Synthetic set:")
    print(json.dumps({k: round(v, 2) if isinstance(v, float) else v for k, v in synthetic.items() if k != "by_type"}, ensure_ascii=False, indent=2))
    if measured_real:
        real = metrics_for(measured_real)
        print("\nMeasured real set:")
        print(json.dumps({k: round(v, 2) if isinstance(v, float) else v for k, v in real.items() if k != "by_type"}, ensure_ascii=False, indent=2))
    else:
        print(f"\nReal set: NOT MEASURED ({len(real_entries)} fictional template examples excluded).")
    print("\nSynthetic results by scam type:")
    print("type | total | correct | wrong | accuracy")
    for scam_type, counts in synthetic["by_type"].items():
        type_accuracy = counts["correct"] / counts["total"] * 100 if counts["total"] else 0.0
        print(f"{scam_type} | {counts['total']} | {counts['correct']} | {counts['wrong']} | {type_accuracy:.2f}%")


if __name__ == "__main__":
    main()
