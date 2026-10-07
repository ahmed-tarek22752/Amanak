from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import tldextract
from rapidfuzz import fuzz

from .rules import normalize_arabic_text

URL_RE = re.compile(r"(?:https?://|www\.)[^\s\)\]>\"']+|(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,}(?:/[^\s\)\]>\"']*)?", re.IGNORECASE)
SHORTENERS = {
    "bit.ly",
    "tinyurl.com",
    "t.co",
    "cutt.ly",
    "goo.gl",
    "ow.ly",
    "is.gd",
    "tiny.cc",
    "rb.gy",
    "s.id",
    "shorturl.at",
    "lnkd.in",
    "urlzs.com",
    "x.co",
    "u.to",
}


def _load_json(path: str | Path) -> list[str]:
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    if isinstance(data, dict):
        return list(data.keys())
    return [str(item) for item in data]


def extract_urls(text: str) -> list[str]:
    matches = URL_RE.findall(text or "")
    urls: list[str] = []
    for value in matches:
        cleaned = value.strip(".,;:!?)]}>")
        if cleaned:
            urls.append(cleaned)
    return urls


def _ensure_url_with_scheme(value: str) -> str:
    value = value.strip()
    if not value:
        return ""
    if value.startswith("http://") or value.startswith("https://"):
        return value
    return "https://" + value if not value.startswith("www.") else "https://" + value


def _is_ip_url(url: str) -> bool:
    try:
        hostname = urlsplit(url).hostname or ""
        return hostname.replace(".", "").isdigit() or hostname.count(".") >= 4
    except Exception:
        return False


def _looks_like_punycode(url: str) -> bool:
    return "xn--" in url.lower()


def _has_excessive_subdomains(url: str) -> bool:
    hostname = urlsplit(url).hostname or ""
    parts = hostname.split(".")
    return len(parts) > 4


def _suspicious_tld(url: str) -> bool:
    hostname = urlsplit(url).hostname or ""
    top = hostname.split(".")[-1].lower()
    suspicious = {"xyz", "top", "club", "online", "bid", "loan", "cf", "ga", "ml", "tk", "icu"}
    return top in suspicious and not hostname.endswith(".gov.eg")


def _lookalike_domains(url: str, trusted_domains: list[str]) -> bool:
    hostname = urlsplit(url).hostname or ""
    if not hostname:
        return False
    for trusted in trusted_domains:
        t = trusted.lower().replace("https://", "").replace("http://", "").strip("/")
        if hostname == t:
            continue
        if len(hostname) >= 5 and len(t) >= 5:
            score = fuzz.ratio(hostname, t)
            if score >= 80 and hostname != t:
                return True
    return False


def _suspicious_hostnames(hostname: str) -> bool:
    suspicious_tokens = [
        "prize", "lottery", "reward", "win", "bonus", "claim", "verify", "secure", "login", "update", "official-login",
        "banking", "payment", "activation", "fawry", "instapay", "vodafone-egypt", "cib-eg", "nbe-secure"
    ]
    lowered = hostname.lower()
    if any(token in lowered for token in suspicious_tokens):
        return True
    return False


def check_links(text: str) -> list[str]:
    urls = extract_urls(text)
    flagged: list[str] = []
    trusted_path = Path(__file__).resolve().parent.parent / "data" / "trusted_domains.json"
    trusted_domains = _load_json(trusted_path)

    for raw in urls:
        url = _ensure_url_with_scheme(raw)
        hostname = urlsplit(url).hostname or ""
        if not hostname:
            continue
        domain = hostname.lower().replace("www.", "")
        if any(short in domain for short in SHORTENERS):
            flagged.append(url)
            continue
        if _is_ip_url(url) or _looks_like_punycode(url) or _has_excessive_subdomains(url) or _suspicious_tld(url):
            flagged.append(url)
            continue
        if _suspicious_hostnames(domain):
            flagged.append(url)
            continue
        if _lookalike_domains(url, trusted_domains):
            flagged.append(url)
            continue
    return list(dict.fromkeys(flagged))


def check_link_text(text: str) -> dict[str, Any]:
    urls = extract_urls(text)
    flagged = []
    reasons = []
    trusted_path = Path(__file__).resolve().parent.parent / "data" / "trusted_domains.json"
    trusted_domains = _load_json(trusted_path)

    for raw in urls:
        url = _ensure_url_with_scheme(raw)
        hostname = urlsplit(url).hostname or ""
        if not hostname:
            continue
        domain = hostname.lower().replace("www.", "")
        details: list[str] = []
        if any(short in domain for short in SHORTENERS):
            details.append("رابط مختصر")
        if _is_ip_url(url):
            details.append("عنوان IP")
        if _looks_like_punycode(url):
            details.append("حروف شبه متشابهة")
        if _has_excessive_subdomains(url):
            details.append("تفرعات كثيرة")
        if _suspicious_tld(url):
            details.append("نهاية اسم مش مألوفة")
        if _lookalike_domains(url, trusted_domains):
            details.append("يشبه اسم موقع موثوق")
        if details:
            flagged.append(url)
            reasons.append(f"{url}: {'، '.join(details)}")

    return {"links_found": urls, "flagged": flagged, "reasons": reasons}


def get_lookalike_trust_matches(text: str) -> list[str]:
    urls = extract_urls(text)
    trusted_path = Path(__file__).resolve().parent.parent / "data" / "trusted_domains.json"
    trusted_domains = _load_json(trusted_path)
    matches: list[str] = []
    for raw in urls:
        url = _ensure_url_with_scheme(raw)
        hostname = urlsplit(url).hostname or ""
        if not hostname:
            continue
        for trusted in trusted_domains:
            t = trusted.lower().replace("https://", "").replace("http://", "").strip("/")
            if hostname != t and hostname.count(".") > 1 and fuzz.ratio(hostname, t) >= 80:
                matches.append(f"{hostname} -> {t}")
    return matches


__all__ = [
    "check_links",
    "check_link_text",
    "extract_urls",
    "get_lookalike_trust_matches",
    "normalize_arabic_text",
]
