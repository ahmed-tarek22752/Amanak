from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from core.analyzer import analyze
from core.replies import build_reply
from db.database import ensure_db, get_stats

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_db()
    telegram_app = None
    try:
        if os.getenv("TELEGRAM_TOKEN"):
            from adapters.telegram_bot import build_telegram_application

            telegram_app = build_telegram_application()
            app.telegram_app = telegram_app
            await telegram_app.initialize()
            await telegram_app.start()
            if telegram_app.updater is None:
                raise RuntimeError("Telegram application has no updater")
            await telegram_app.updater.start_polling()
        yield
    finally:
        if telegram_app is not None:
            if telegram_app.updater is not None and telegram_app.updater.running:
                await telegram_app.updater.stop()
            if telegram_app.running:
                await telegram_app.stop()
            await telegram_app.shutdown()


app = FastAPI(title="Amanak", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root() -> dict[str, Any]:
    return {
        "name": "Amanak",
        "tagline": "Your family's second opinion on suspicious messages.",
        "status": "ok",
        "disclaimer": "Amanak gives guidance, not a guarantee.",
    }


@app.get("/health")
async def health() -> dict[str, Any]:
    return {"status": "ok"}


@app.post("/api/check")
async def check_message(payload: dict[str, Any]) -> dict[str, Any]:
    text = str(payload.get("text", "")).strip()
    source = str(payload.get("source", "web")).strip() or "web"

    if not text:
        raise HTTPException(status_code=400, detail="Text is required.")

    result = analyze(text, source)
    response = {
        "verdict": result.verdict,
        "score": result.score,
        "scam_type": result.scam_type,
        "reasons": result.reasons,
        "advice": result.advice,
        "links_found": result.links_found,
        "reply": build_reply(result, "en" if payload.get("lang") == "en" else "ar"),
    }
    return response


@app.get("/api/stats")
async def stats() -> dict[str, Any]:
    return get_stats()


@app.get("/privacy")
async def privacy_page() -> JSONResponse:
    return JSONResponse(
        {
            "message": "Amanak stores only limited metadata to protect privacy. Raw message text is kept only after a user confirms a report and only after masking sensitive data.",
            "disclaimer": "Amanak gives guidance, not a guarantee.",
        }
    )


if os.getenv("TELEGRAM_TOKEN"):
    from adapters.telegram_bot import register_telegram_routes

    register_telegram_routes(app)

if os.getenv("ENABLE_WHATSAPP", "false").lower() == "true":
    from adapters.whatsapp_bot import register_whatsapp_routes

    register_whatsapp_routes(app)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
    )
