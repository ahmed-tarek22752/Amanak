from core.analyzer import analyze


def test_fake_prize_is_scam():
    text = "مبروك! ربحت جايزة من Vodafone، ادفع 250 جنيه كرسوم التسجيل حالا."
    result = analyze(text, "test")
    assert result.verdict == "scam"
    assert result.score >= 55


def test_bank_otp_notice_is_safe():
    text = "كود التفعيل الخاص بك: 1842. لا تشارك هذا الكود مع أحد. البنك يطلب منك عدم مشاركة الرقم." 
    result = analyze(text, "test")
    assert result.verdict in {"safe", "caution"}
    assert result.verdict != "scam"


def test_high_pressure_warning():
    text = "خلال 24 ساعة فقط سيُغلق حسابك، لازم ترد فوراً على هذا الرقم." 
    result = analyze(text, "test")
    assert result.verdict in {"scam", "caution"}
