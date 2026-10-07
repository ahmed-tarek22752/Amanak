from __future__ import annotations

from typing import Any

from .models import AnalysisResult


def _english_text(analysis: AnalysisResult) -> str:
    if analysis.verdict == "scam":
        verdict = "🔴 Likely scam"
        intro = "This message looks suspicious."
    elif analysis.verdict == "caution":
        verdict = "🟡 Be careful"
        intro = "This message has warning signs."
    else:
        verdict = "🟢 Looks okay"
        intro = "There are no strong scam signs here."

    lines = [
        f"{verdict}: {intro}",
        "It may ask for urgent action, personal data, money, or a link that looks fake.",
        f"Next step: {analysis.advice}",
        "Amanak gives guidance, not a guarantee, and can make mistakes.",
    ]
    return "\n".join(lines)


def build_reply(analysis: AnalysisResult, language: str = "ar") -> str:
    if language.lower() == "en":
        return _english_text(analysis)

    if analysis.verdict == "scam":
        verdict = "🔴 غالبًا نصب"
        intro = "الرسالة فيها مؤشرات قوية على النصب."
    elif analysis.verdict == "caution":
        verdict = "🟡 خلي بالك"
        intro = "فيها علامات تحذير، لكن مش لازم تكون نصب."
    else:
        verdict = "🟢 يبدو سليم"
        intro = "مافيش مؤشرات قوية للنصب في الرسالة الحالية."

    lines = [
        f"{verdict}",
        f"{intro} {analysis.reasons[0] if analysis.reasons else 'لو فيها طلب سريع أو رابط مش واضح، خليك بعيد عنه.'}",
        f"{analysis.advice}",
        "بيعتمد على رأيك، وده برضه ممكن يخطئ."
    ]
    return "\n".join(lines)


__all__ = ["build_reply"]
