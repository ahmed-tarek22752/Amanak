from core.analyzer import analyze


def test_analyze_generates_summary_fields():
    result = analyze("حسابك موقوف، لازم تكتب كلمة السر فوراً", "test")
    assert result.verdict in {"scam", "caution"}
    assert isinstance(result.reasons, list)
    assert isinstance(result.links_found, list)
    assert result.advice
