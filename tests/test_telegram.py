from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock

import pytest

import main


@pytest.mark.asyncio
async def test_fastapi_lifespan_starts_and_stops_telegram(monkeypatch):
    updater = type("Updater", (), {"running": True, "start_polling": AsyncMock(), "stop": AsyncMock()})()
    telegram_app = type(
        "TelegramApp",
        (),
        {
            "updater": updater,
            "running": True,
            "initialize": AsyncMock(),
            "start": AsyncMock(),
            "stop": AsyncMock(),
            "shutdown": AsyncMock(),
        },
    )()
    build_application = AsyncMock(return_value=telegram_app)

    monkeypatch.setenv("TELEGRAM_TOKEN", "unit-test-token")
    monkeypatch.setattr(main, "ensure_db", lambda: None)
    monkeypatch.setattr("adapters.telegram_bot.build_telegram_application", lambda: telegram_app)

    async with main.lifespan(main.app):
        assert main.app.telegram_app is telegram_app
        telegram_app.initialize.assert_awaited_once()
        telegram_app.start.assert_awaited_once()
        updater.start_polling.assert_awaited_once()

    updater.stop.assert_awaited_once()
    telegram_app.stop.assert_awaited_once()
    telegram_app.shutdown.assert_awaited_once()