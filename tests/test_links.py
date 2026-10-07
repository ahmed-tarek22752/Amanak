from core.links import check_links, extract_urls


def test_extract_urls_handles_plain_links():
    text = "للاستفسار: www.vodafone-egypt-prize.com/free"
    links = extract_urls(text)
    assert any("vodafone" in url.lower() for url in links)


def test_suspicious_link_is_flagged():
    text = "https://vodafone-egypt-prize.com/free"
    links = check_links(text)
    assert links
