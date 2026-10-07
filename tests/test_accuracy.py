import json
from pathlib import Path

from core.analyzer import analyze

DATASET_PATH = Path(__file__).resolve().parent.parent / "data" / "test_messages.json"


def test_synthetic_dataset_has_required_size_and_labels():
    if not DATASET_PATH.exists():
        raise FileNotFoundError("Synthetic dataset not found.")
    messages = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    assert len(messages) >= 120
    scam_total = sum(1 for item in messages if item["expected_verdict"] == "scam")
    safe_total = sum(1 for item in messages if item["expected_verdict"] == "safe")
    assert scam_total >= 60
    assert safe_total >= 50

    for item in messages:
        verdict = analyze(item["text"], "test_accuracy").verdict
        if item["expected_verdict"] == "safe":
            assert verdict != "scam", f"False positive on {item['text']}"


def test_generalized_scam_patterns_are_detected():
    checks = [
        ("من البنك: تم تعليق حسابك، اضغط الرابط وخلّي الكود في الحقل فورًا.", "scam"),
        ("أنت من الفائزين في السحب، ابعت رقم البطاقة الآن لتفعيل الجائزة قبل 6 مساءً.", "scam"),
        ("أنا في المستشفى، رقم جديد وعايز 700 جنيه الآن لو سمحت.", "scam"),
        ("معلومة عاجلة: فاتورتك متأخرة، اكتب بياناتك الآن لتجنب القطع.", "scam"),
        ("بنود التوظيف: لازم تدفع 300 جنيه مصروفات أولية قبل التوظيف.", "scam"),
        ("شركة العمل لا تطلب أي دفع مقدم قبل التوظيف.", "safe"),
    ]

    for text, expected in checks:
        verdict = analyze(text, "generalization").verdict
        assert verdict == expected, f"expected {expected} for: {text!r}; got {verdict}"
