from __future__ import annotations

import os
import tempfile
import time
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from PIL import Image
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, ApplicationBuilder, CallbackContext, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters

from core.analyzer import analyze
from core.ocr import image_to_text
from core.replies import build_reply
from db.database import get_stats, record_check, record_report

RATE_LIMITS: dict[int, deque[float]] = defaultdict(deque)


def _rate_limited(user_id: int) -> bool:
    limit = int(os.getenv("MAX_CHECKS_PER_USER_PER_HOUR", "20"))
    now = time.time()
    times = RATE_LIMITS.get(user_id, deque())
    while times and now - times[0] > 3600:
        times.popleft()
    if len(times) >= limit:
        return True
    times.append(now)
    RATE_LIMITS[user_id] = times
    return False


def _feedback_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("👍 مفيد", callback_data="feedback_good"),
                InlineKeyboardButton("👎 غلط", callback_data="feedback_bad"),
            ],
            [
                InlineKeyboardButton("📣 بلّغ عن النصب", callback_data="report_scam"),
            ],
        ]
    )


async def _send_analysis(update: Update, text: str) -> None:
    if update.effective_message is None:
        return
    result = analyze(text, "telegram")
    if update.effective_user is not None:
        record_check(
            "telegram",
            result.verdict,
            result.scam_type,
            result.score,
            update.effective_user.id,
            {"source": "telegram"},
        )
    reply = build_reply(result, "ar")
    await update.effective_message.reply_text(reply, reply_markup=_feedback_keyboard())


async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text(
        "أهلا بيك في أمانك 👋\nابعت لي نص، صورة، أو رسالة مرسلة من شخص، وأنا أقولك هل فيها نصب أو لا."
    )


async def help_command(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text(
        "💡 أوامر البوت:\n/start\n/help\n/privacy\n/report\n/stats\n/delete\n\nابعت أي رسالة أو صورة، وهنراجعها بسرعة."
    )


async def privacy_command(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text(
        "🔒 بنخزن بيانات محدودة فقط: وقت الفحص، نوع الرسالة، النتيجة، والمعدل. نص الرسالة الأصلي ما بيتحفظش إلا لو دخلت في بلاغ، وبنخفف البيانات الحساسة."
    )


async def stats_command(update: Update, context: CallbackContext) -> None:
    stats = get_stats()
    await update.message.reply_text(
        f"📊 إحصائيات أمانك:\nإجمالي الفحوصات: {stats.get('total_checks', 0)}\nمقاطع نُصب: {stats.get('scams_caught', 0)}\nتحذيرات: {stats.get('cautions', 0)}"
    )


async def delete_command(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text(
        "🗑️ تم حذف البيانات الخاصة بالجلسة الحالية من الذاكرة. نص الرسالة ما بيتحفظش عادة، وبيتم الاحتفاظ فقط ببيانات محدودة لأغراض الأمن."
    )


async def report_command(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text(
        "📣 لو عايز تبعت بلاغ، ابعت الرسالة أو الصورة في نفس المحادثة، وهنستلمها بشكل آمن وبدون رقم أو بيانات حساسة."
    )


async def handle_text_message(update: Update, context: CallbackContext) -> None:
    if update.effective_user is None or update.effective_message is None:
        return
    if _rate_limited(update.effective_user.id):
        await update.message.reply_text("وصلت لحد الفحوصات اليومية 🌙\nهتقدر تحاول مرة تانية بعد ساعة.")
        return

    text = update.effective_message.text or update.effective_message.caption or ""
    if not text.strip():
        await update.message.reply_text("ابعت نص أو صورة واضحة، وأنا أراجعها لك 🤝")
        return

    await update.message.chat.send_action(action="typing")
    await _send_analysis(update, text)


async def handle_photo_message(update: Update, context: CallbackContext) -> None:
    if update.effective_message is None or update.effective_user is None:
        return
    if _rate_limited(update.effective_user.id):
        await update.message.reply_text("وصلت لحد الفحوصات اليومية 🌙\nهتقدر تحاول مرة تانية بعد ساعة.")
        return

    await update.message.chat.send_action(action="typing")
    photo = update.message.photo[-1]
    file = await photo.get_file()
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        await file.download_to_drive(custom_path=tmp.name)
        tmp_path = Path(tmp.name)
    try:
        text = image_to_text(tmp_path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)

    if not text.strip():
        await update.message.reply_text("ما اتعرفتش اقرأ الصورة كويس. ابعت نص أو صورة أوضح من فضلك 📷")
        return

    await _send_analysis(update, text)


async def handle_forwarded_message(update: Update, context: CallbackContext) -> None:
    if update.effective_message is None:
        return
    text = update.effective_message.text or update.effective_message.caption or ""
    if not text.strip() and update.effective_message.forward_origin is not None:
        await update.message.reply_text("الرسالة المرسلة للأمام محتملة، ابعت نصها أو صورة واضحة لو عايز أراجعها.")
        return
    await handle_text_message(update, context)


async def callback_query(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    if query is None:
        return
    data = query.data or ""
    if data == "report_scam":
        await query.answer("تم تسجيل البلاغ بشكل آمن 🛡️")
        if update.effective_user is not None:
            record_report("telegram", "scam", "unknown", update.effective_user.id, "masked_message")
        return

    await query.answer("شكرًا لملاحظتك 🙏")


def build_telegram_application() -> Application:
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_TOKEN is not set")

    application = ApplicationBuilder().token(token).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("privacy", privacy_command))
    application.add_handler(CommandHandler("report", report_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("delete", delete_command))

    application.add_handler(MessageHandler(filters.FORWARDED & filters.TEXT, handle_forwarded_message))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo_message))
    application.add_handler(MessageHandler(filters.VOICE, handle_text_message))
    application.add_handler(CallbackQueryHandler(callback_query))
    return application


def register_telegram_routes(app: FastAPI) -> None:
    @app.get("/telegram/webhook")
    async def telegram_webhook() -> dict[str, str]:
        return {"status": "telegram webhook route ready"}


__all__ = ["build_telegram_application", "register_telegram_routes"]
