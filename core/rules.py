from __future__ import annotations

import json
import re
from pathlib import Path

ARABIC_PATTERNS = {
    "urgency": ["حالا", "خلال 24 ساعة", "آخر فرصة", "لآخر", "act now", "today only", "limited time", "urgent", "فوراً", "فورا"],
    "otp": ["otp", "pin", "password", "كود", "cvv", "card number", "رقم البطاقة", "الرقم السري", "الرقم الخاص", "national id", "بطاقة الرقم القومي"],
    "fake_prize": ["ربحت", "فوز", "جايز", "prize", "lottery", "vodafone", "orange", "etisalat", "we", "e&", "مبروك"],
    "delivery": ["شحنة", "توصيل", "customs", "delivery", "aramex", "dhl", "bosta", "egypt post", "posta"],
    "bank": ["حسابك موقوف", "تم تعليق بطاقتك", "تعليق بطاقة", "تم تعليق حسابك", "تم تجميد حسابك", "حسابك تم اختراقه", "bank", "cib", "nbe", "banque misr", "qnb", "alex bank", "الأهلي", "مصرف"],
    "govt": ["بدعم", "مستحق", "ضريبة", "فاتورة", "كهرباء", "غاز", "مكتب الضرائب", "الضرائب", "التضامن", "subsidy", "tax", "electricity", "gas bill", "مزايدة", "تأكيد الملف"],
    "jobs": ["وظيفة", "job", "فرصة", "توظيف", "تدريب", "تحتاج مبلغ", "مطلوب دفع", "مشاركة 500", "مبلغ أولي", "قرض", "تشتري", "اشتري", "مصروفات أولية", "ضمان أولي"],
    "investment": ["استثمار", "استثمر", "تضاعف", "ضاعف", "double your money", "crypto", "bitcoin", "investment", "profit", "returns", "عملة رقمية"],
    "family": ["غيرت رقمي", "تغير رقمي", "غير الرقم", "من رقم جديد", "أنا في مشكلة", "family emergency", "urgent call", "I changed my number", "أخوك", "أمي", "سيغلق الحساب"],
    "wallet": ["vodafone cash", "instapay", "fawry", "تحويل", "wallet", "إيداع", "طلب تحويل", "مبلغ مستحق"],
    "romance": ["حب", "عشق", "romance", "love", "charity", "donation", "مؤسسة خيرية", "صدقة", "جمعيات الخير", "تبرع", "تبرع", "خيرية", "جمعية خيرية", "مساعدة"],
}

SAFE_PATTERNS = [
    "لا تشارك هذا الكود",
    "لا تشارك هذا الرقم",
    "never share this code",
    "never share this otp",
    "do not share this code",
    "do not share this otp",
    "لا تشارك هذا الكود مع احد",
    "لا تشارك الرقم مع أحد",
    "لا تشارك هذا الرقم مع أحد",
]


def normalize_arabic_text(text: str) -> str:
    normalized = text or ""
    replacements = {
        "\u0640": "",
        "\u0622": "ا",
        "\u0623": "ا",
        "\u0625": "ا",
        "\u0671": "ا",
        "\u064A": "ي",
        "\u064E": "",
        "\u064F": "",
        "\u0650": "",
        "\u0651": "",
        "\u0652": "",
        "\u0670": "",
        "\u0629": "ة",
        "\u0643": "ك",
    }
    for src, dst in replacements.items():
        normalized = normalized.replace(src, dst)
    normalized = normalized.replace("٠", "0").replace("١", "1").replace("٢", "2").replace("٣", "3").replace("٤", "4").replace("٥", "5").replace("٦", "6").replace("٧", "7").replace("٨", "8").replace("٩", "9")
    normalized = normalized.replace("ـ", "")
    normalized = normalized.lower()
    return normalized


def _contains_any(text: str, needles: list[str]) -> bool:
    text_norm = normalize_arabic_text(text)
    for needle in needles:
        n = normalize_arabic_text(needle)
        if n and n in text_norm:
            return True
    return False


def _match_count(text: str, keys: list[str]) -> int:
    count = 0
    for key in keys:
        if _contains_any(text, [key]):
            count += 1
    return count


def evaluate_rules(text: str) -> tuple[str, int, str, list[str]]:
    cleaned = text or ""
    text_norm = normalize_arabic_text(cleaned)
    reason_strings: list[str] = []
    score = 0
    scam_type = "unknown"

    if any(pattern in text_norm for pattern in [normalize_arabic_text(p) for p in SAFE_PATTERNS]):
        return "safe", 5, "safe", ["الرسالة بتخوف من مشاركة الكود، لكن الأرقام واضحة أنها رسالة أمنية وليس نصب."]

    if ("لا نطلب" in text_norm or "لا يطلب" in text_norm or "لن نطلب" in text_norm or "لا تحتاج" in text_norm) and (
        "كلمة السر" in text_norm or "cvv" in text_norm or "otp" in text_norm or "الكود" in text_norm or "رقم البطاقة" in text_norm or "الرقم السري" in text_norm or "تحويل" in text_norm or "دفع" in text_norm or "مبلغ" in text_norm
    ):
        return "safe", 4, "safe", ["الرسالة تقول صراحة إن البنك أو الخدمة لا تطلب بياناتك، وده مؤشر على سلامة الرسالة."]

    if ("لا توجد" in text_norm or "لا يوجد" in text_norm or "لا داعي" in text_norm) and (
        "رسوم" in text_norm or "مبلغ" in text_norm or "خصومات" in text_norm or "دفع" in text_norm or "فلوس" in text_norm or "طلب" in text_norm or "دعم" in text_norm or "مستحق" in text_norm or "فاتورة" in text_norm
    ):
        return "safe", 3, "safe", ["الرسالة توضح بوضوح إن لا توجد أي رسوم أو طلبات مالية، أو لا يوجد دعم مستحق، وده يخفف الشكوك."]

    if "التطبيق الرسمي" in text_norm and ("الشحنة" in text_norm or "الطلب" in text_norm or "الفاتورة" in text_norm or "التحديث" in text_norm) and not ("رسوم" in text_norm or "ادفع" in text_norm or "أرسل" in text_norm or "ارسل" in text_norm or "مستحق" in text_norm or "الآن" in text_norm or "فورا" in text_norm):
        return "safe", 3, "safe", ["الرسالة متاحة عبر التطبيق الرسمي فقط، وبدون طلب للأموال أو البيانات، فهي غالباً مية مأمونة."]

    if (
        ("لا داعي" in text_norm or "لا توجد" in text_norm or "لا يوجد" in text_norm or "لا نطلب" in text_norm or "لا يطلب" in text_norm or "لا تطلب" in text_norm or "لن نطلب" in text_norm or "لا تحتاج" in text_norm or "لا يتم طلب" in text_norm or "لا يتم الدفع" in text_norm)
        and ("تحويل" in text_norm or "رسوم" in text_norm or "مبلغ" in text_norm or "دفع" in text_norm or "فلوس" in text_norm or "مستحق" in text_norm or "تجديد" in text_norm or "الفاتورة" in text_norm or "دفع مقدم" in text_norm or "مقدم قبل" in text_norm)
    ):
        return "safe", 4, "safe", ["الرسالة تقول صراحة إنه لا داعي لأي تحويل أو رسوم، وده يثبت أنها رسالة رسمية أو إعلامية موثوقه."]

    if (
        ("رسمي" in text_norm or "التطبيق الرسمي" in text_norm or "البريد الإلكتروني الرسمي" in text_norm or "الموقع الرسمي" in text_norm or "المنصة الرسمية" in text_norm)
        and ("فاتورة" in text_norm or "الشحنة" in text_norm or "الطلب" in text_norm or "التحديث" in text_norm or "إشعار" in text_norm or "اعلان" in text_norm)
        and not ("طلب تحويل" in text_norm or "أرسل" in text_norm or "ارسل" in text_norm or "دفع الآن" in text_norm or "ادفع" in text_norm or "تحويل فوري" in text_norm or "مبلغ مستحق" in text_norm or "مستحق الآن" in text_norm)
    ):
        return "safe", 4, "safe", ["الرسالة رسمية ومشفرة عبر قناة موثوقة، وبدون طلب لأموال أو بيانات، فحالتها آمنة."]

    if ("الرسالة الرسمية" in text_norm or "رسالة رسمية" in text_norm) and (
        "أرسل" in text_norm or "ارسل" in text_norm or "اكتب" in text_norm or "ادخل" in text_norm or "مطلوب" in text_norm
    ) and (
        "رقم البطاقة" in text_norm or "بطاقة" in text_norm or "الرقم القومي" in text_norm or "بطاقتك" in text_norm or "بياناتك" in text_norm
    ) and (
        "إيقاف" in text_norm or "ايقاف" in text_norm or "سيتم إيقاف" in text_norm or "الحساب" in text_norm or "الخدمة" in text_norm
    ):
        return "scam", 70, "government", ["الرسالة تبدو رسمية لكنها تطلب بيانات أو رقم بطاقة، وده نمط شائع في النصب."]

    if (
        ("غير الرقم" in text_norm or "رقم جديد" in text_norm or "أخوك" in text_norm or "اخوك" in text_norm or "أنا في المستشفى" in text_norm)
        and ("سيغلق" in text_norm or "الحساب" in text_norm or "المستشفى" in text_norm or "لم ترد" in text_norm)
        and ("الان" in text_norm or "الآن" in text_norm or "فورا" in text_norm or "فور" in text_norm)
    ):
        return "scam", 68, "family_impersonation", ["الرسالة تمثل حالة طارئة عائلية وتطلب فلوس فورًا، وده بناء شائع للنصب."]

    if (
        ("استثمر" in text_norm or "تضاعف" in text_norm or "ضاعف" in text_norm or "استثمار" in text_norm or "عملة رقمية" in text_norm or "btc" in text_norm)
        and ("مبلغ" in text_norm or "جنيه" in text_norm or "فلوس" in text_norm or "مضاعف" in text_norm)
        and ("خلال" in text_norm or "الان" in text_norm or "الآن" in text_norm or "أرباح" in text_norm or "ربح" in text_norm)
    ):
        return "scam", 72, "investment", ["الرسالة تعد بربح سريع على استثمار أو عملة رقمية، وده مؤشر واضح على النصب."]

    if (
        ("قرض" in text_norm or "تشتري" in text_norm or "اشتري" in text_norm or "مبلغ" in text_norm or "مصروفات" in text_norm)
        and ("تودع" in text_norm or "دفع" in text_norm or "مقدم" in text_norm or "ضمان" in text_norm or "دفع مقدم" in text_norm)
        and ("بدون فوائد" in text_norm or "قرض" in text_norm or "توظيف" in text_norm or "منتج" in text_norm)
    ):
        return "scam", 70, "job_offer", ["الرسالة تطلب دفعة أو ضمان مقابل فرصة أو منتج، وده نمط معروف في الاحتيال."]

    if (
        ("جمعيات الخير" in text_norm or "جمعية خيرية" in text_norm or "تبرع" in text_norm or "خيرية" in text_norm or "مؤسسة خيرية" in text_norm)
        and ("مبلغ" in text_norm or "جنيه" in text_norm or "دفع" in text_norm or "مقدم" in text_norm)
    ):
        return "scam", 66, "romance", ["الرسالة تدفعك للتبرع أو الدفع مقابل قصة خيرية أو داعية، وده غالباً نصب."]

    generic_money_request = any(phrase in text_norm for phrase in ["أرسل", "ارسل", "اكتب", "ادخل", "اضغط", "تدفع", "دفع", "تودع", "تحويل", "تحديث بيانات", "تفعيل"])
    generic_data_request = any(phrase in text_norm for phrase in ["كلمة السر", "الكود", "otp", "رقم البطاقة", "الرقم السري", "الرقم القومي", "بياناتك", "بطاقتك", "الرابط", "البيانات"])
    generic_urgency = any(phrase in text_norm for phrase in ["الآن", "الان", "فور", "فورا", "فوراً", "قبل", "خلال", "حال", "حالاً", "فوري", "يوميا"])
    generic_account_threat = any(phrase in text_norm for phrase in ["تم تعليق", "تم تجميد", "تم اختراق", "سيغلق", "موقوف", "معلق", "حسابك", "مستحق", "خصم"])
    generic_prize = any(phrase in text_norm for phrase in ["أنت من الفائزين", "ربحت", "فزت", "جائزة", "مبروك", "سحب", "مكافأة"])
    generic_family = any(phrase in text_norm for phrase in ["أنا في المستشفى", "رقم جديد", "غيرت رقمي", "أنا في مشكلة", "عايز", "عايز فلوس", "احتاج", "أحتاج", "محتاج", "لو سمحت", "أحتاج 700", "أحتاج 300"]) 
    generic_job = any(phrase in text_norm for phrase in ["مطلوب", "وظيفة", "توظيف", "مصروفات أولية", "دفع مقدم", "ضمان أولي", "تودع", "قرض", "بداية"])

    if (generic_money_request and generic_data_request and generic_urgency) or (
        generic_account_threat and generic_data_request and generic_urgency
    ) or (
        generic_prize and generic_data_request and generic_urgency
    ) or (
        generic_family and generic_urgency and ("فلوس" in text_norm or "جنيه" in text_norm or "مبلغ" in text_norm or "تحويل" in text_norm)
    ) or (
        generic_job and ("دفع" in text_norm or "تودع" in text_norm or "مصروفات" in text_norm or "ضمان" in text_norm or "دفع مقدم" in text_norm) and generic_urgency
    ):
        verdict = "scam"
        scam_type = "generalized_scam_request"
        return verdict, 62, scam_type, ["الرسالة تطلب بيانات أو فلوس أو رابطًا في وضع فشار ووقت سريع، وده نمط شائع في النصب."]

    if "لا تشارك" in text_norm and ("كلمة السر" in text_norm or "الكود" in text_norm or "otp" in text_norm or "cvv" in text_norm or "الرقم" in text_norm):
        return "caution", 22, "warning", ["الرسالة تعمل تنبيه، وده لازم يتعامل معه بحذر حتى لو مش نصباً بالضرورة."]

    if _contains_any(cleaned, ARABIC_PATTERNS["urgency"]):
        score += 35
        reason_strings.append("الرسالة بتضغط عليك بسرعة وبتطلب قرار فوري.")
    if _contains_any(cleaned, ARABIC_PATTERNS["otp"]):
        score += 30
        reason_strings.append("الرسالة بتطلب كود أو كلمة سر أو بيانات بطاقة.")
    if _contains_any(cleaned, ARABIC_PATTERNS["fake_prize"]):
        score += 35
        reason_strings.append("الرسالة بتقول إنك ربحت جايزة أو مكافأة.")
        scam_type = "fake_prize"
    if _contains_any(cleaned, ARABIC_PATTERNS["delivery"]):
        score += 22
        reason_strings.append("المتحدث بيطلب رسوم توصيل أو جمرك بشكل غير واضح.")
        scam_type = "delivery"
    if _contains_any(cleaned, ARABIC_PATTERNS["bank"]):
        score += 30
        reason_strings.append("بيتم التهديد بموقف الحساب أو البطاقة بشكل غير موثوق.")
        scam_type = "bank"
    if _contains_any(cleaned, ARABIC_PATTERNS["govt"]):
        score += 24
        reason_strings.append("الرسالة بتتقمص هيئة حكومية أو بتطلب بيانات رسمية.")
        scam_type = "government"
    if _contains_any(cleaned, ARABIC_PATTERNS["jobs"]):
        score += 20
        reason_strings.append("عرض شغل بيطلب منك فلوس أو دفع مقدم.")
        scam_type = "job_offer"
    if _contains_any(cleaned, ARABIC_PATTERNS["investment"]):
        score += 22
        reason_strings.append("الرسالة بتعدك بربح سريع أو استثمار كبير.")
        scam_type = "investment"
    if _contains_any(cleaned, ARABIC_PATTERNS["family"]):
        score += 24
        reason_strings.append("بتتم محاكاة حالة عائلية أو تغيير رقم.")
        scam_type = "family_impersonation"
    if _contains_any(cleaned, ARABIC_PATTERNS["wallet"]):
        score += 26
        reason_strings.append("الرسالة بتطلب تحويل فلوس أو طلب فورى عبر محافظ إلكترونية.")
        scam_type = "wallet"
    if _contains_any(cleaned, ARABIC_PATTERNS["romance"]):
        score += 18
        reason_strings.append("الرسالة بتدور على مشاعر أو خيرية بشكل مبالغ فيه.")
        scam_type = "romance"

    if not reason_strings:
        score = 4
        scam_type = "safe"
        return "safe", score, scam_type, ["مفيش إشارات واضحة للنصب في الرسالة الحالية."]

    if score >= 55 or scam_type in {"fake_prize", "bank", "wallet", "delivery", "government", "job_offer", "investment", "family_impersonation", "romance"}:
        verdict = "scam"
    elif score >= 35:
        verdict = "caution"
    else:
        verdict = "safe"

    return verdict, min(score, 100), scam_type, reason_strings


def is_safe_legitimate_message(text: str) -> bool:
    suspicious_keywords = [
        "ربحت", "كود", "otp", "فوز", "تفعيل", "موقوف", "بطاقتك", "حسابك", "شحنة", "رسوم", "استثمار"
    ]
    if any(keyword in normalize_arabic_text(text) for keyword in suspicious_keywords):
        return False
    if "do not share" in (text or "").lower() and "code" in (text or "").lower():
        return True
    if "never share this code" in (text or "").lower():
        return True
    return True


__all__ = ["evaluate_rules", "normalize_arabic_text", "is_safe_legitimate_message"]
