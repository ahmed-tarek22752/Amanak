from __future__ import annotations

import os
from typing import Any

from .ai import generate_ai_explanation
from .links import check_links
from .models import AnalysisResult
from .rules import evaluate_rules


def analyze(text: str, source: str = "web") -> AnalysisResult:
    verdict, score, scam_type, reasons = evaluate_rules(text)
    links_found = check_links(text)

    advice = "تأكد من مصدر الرسالة، وعايز كمان سؤال شخص موثوق قبل أي تحويل أو مشاركة بيانات."
    if verdict == "scam":
        advice = "ما تعملش أي تحويل ولا تشارك كود أو كلمة سر. اتصل بالشخص الحقيقي من رقم معروف، أو ابعت له رسالة في واتساب بدل ما تتعامل مع الرابط."
    elif verdict == "caution":
        advice = "خليك حذر وراجع التفاصيل. لو فيه طلب فورى أو رابط غريب، اسأل شريك أو صديق موثوق قبل ما ترد."

    if links_found:
        score = min(100, score + 15)
        if verdict != "scam":
            verdict = "scam" if score >= 55 else "caution"
        if not reasons:
            reasons = ["في رابط أو اسم موقع مش واضح أو شبيه بموقع حقيقي."]

    ai_enabled = os.getenv("ENABLE_AI", "false").lower() == "true" and bool(os.getenv("ANTHROPIC_API_KEY"))
    if ai_enabled:
        ai_text = generate_ai_explanation(text)
        if ai_text:
            ai_score = 0
            if "نصب" in ai_text.lower() or "scam" in ai_text.lower():
                ai_score = 1
            elif "حذر" in ai_text.lower() or "caution" in ai_text.lower():
                ai_score = 0
            else:
                ai_score = -1

            if ai_score == 1 and verdict != "scam":
                verdict = "caution"
            elif ai_score == -1 and verdict == "scam":
                verdict = "caution"
            if ai_score in {1, -1}:
                reasons.append("تقييم AI خفف أو شدد النتيجة بشكل محدود.")

    if verdict == "safe":
        scam_type = "safe"

    return AnalysisResult(
        verdict=verdict,
        score=min(max(score, 0), 100),
        scam_type=scam_type,
        reasons=reasons,
        advice=advice,
        links_found=links_found,
        metadata={"source": source},
    )


__all__ = ["analyze"]
