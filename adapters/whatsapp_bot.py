from __future__ import annotations

import hashlib
import hmac
import os
from typing import Any

import httpx
from fastapi import FastAPI, Header, HTTPException, Request

from core.analyzer import analyze
from core.replies import build_reply


def _verify_signature(payload: bytes, signature: str | None) -> bool:
    secret = os.getenv("WHATSAPP_APP_SECRET", "")
    if not secret or not signature:
        return True
    expected = "sha256=" + hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def register_whatsapp_routes(app: FastAPI) -> None:
    @app.get("/webhook/whatsapp")
    async def verify_whatsapp(request: Request) -> str:
        params = request.query_params
        if params.get("hub.mode") == "subscribe" and params.get("hub.verify_token") == os.getenv("WHATSAPP_VERIFY_TOKEN"):
            return params.get("hub.challenge", "")
        raise HTTPException(status_code=403, detail="verification failed")

    @app.post("/webhook/whatsapp")
    async def whatsapp_webhook(request: Request, x_hub_signature_256: str | None = Header(default=None, alias="X-Hub-Signature-256")) -> dict[str, str]:
        payload = await request.body()
        if not _verify_signature(payload, x_hub_signature_256):
            raise HTTPException(status_code=401, detail="invalid signature")

        data = await request.json()
        messages = data.get("entry", [{}])[0].get("changes", [{}])[0].get("value", {}).get("messages", [])
        if not messages:
            return {"status": "no messages"}

        for message in messages:
            text = message.get("text", {}).get("body") or message.get("caption") or ""
            if text:
                result = analyze(text, "whatsapp")
                reply = build_reply(result, "ar")
                token = os.getenv("WHATSAPP_TOKEN")
                phone_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
                if token and phone_id:
                    httpx.post(
                        f"https://graph.facebook.com/v18.0/{phone_id}/messages",
                        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                        json={
                            "messaging_product": "whatsapp",
                            "to": message["from"],
                            "type": "text",
                            "text": {"body": reply},
                        },
                        timeout=10,
                    )
        return {"status": "ok"}


__all__ = ["register_whatsapp_routes"]
