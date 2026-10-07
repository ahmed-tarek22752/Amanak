import hashlib
import hmac
import os

from adapters.whatsapp_bot import _verify_signature


def test_verify_signature_accepts_valid_payload(monkeypatch):
    secret = "super-secret"
    monkeypatch.setenv("WHATSAPP_APP_SECRET", secret)
    payload = b'{"entry":[{"changes":[{"value":{"messages":[{"from":"15551234567","text":{"body":"hello"}}]}}]}]}'
    expected = "sha256=" + hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    assert _verify_signature(payload, expected) is True


def test_verify_signature_rejects_invalid_payload(monkeypatch):
    monkeypatch.setenv("WHATSAPP_APP_SECRET", "super-secret")
    payload = b'{"entry":[{"changes":[{"value":{"messages":[{"from":"15551234567"}]}}]}]}'
    assert _verify_signature(payload, "sha256=totallywrong") is False


def test_verify_signature_handles_missing_signature_when_secret_absent(monkeypatch):
    monkeypatch.delenv("WHATSAPP_APP_SECRET", raising=False)
    payload = b'{"ok": true}'
    assert _verify_signature(payload, None) is True
