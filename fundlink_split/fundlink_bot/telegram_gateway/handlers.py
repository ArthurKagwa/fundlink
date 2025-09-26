"""Application builder and Telegram update handlers for fundlink_bot."""

from __future__ import annotations

import logging
import os

from django.conf import settings
from telegram import Update
from telegram.ext import Application, ApplicationBuilder, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters

from fundlink_bot.bot_logic.handlers import handle_callback_query as llm_handle_callback_query
from fundlink_bot.bot_logic.handlers import handle_message as llm_handle_message

logger = logging.getLogger(__name__)


async def _start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    user_name = update.effective_user.first_name if update.effective_user else "there"
    await update.message.reply_text(
        (
            f"Welcome {user_name}! I'm the FundLink donation assistant.\n\n"
            "💝 Say 'campaigns' to see active humanitarian campaigns\n"
            "💰 Or try 'donate 0.001 to [campaign name]' for quick donations\n"
            "📊 Say 'my donations' to see your donation history"
        )
    )


async def _chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    await llm_handle_message(update, context)


async def _callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await llm_handle_callback_query(update, context)


def build_application() -> Application:
    """Construct the python-telegram-bot ``Application`` wired to bot_logic."""

    token = settings.TELEGRAM_BOT_TOKEN or os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is required to boot the bot service")

    logger.info("Building Telegram application for fundlink_bot")
    application = ApplicationBuilder().token(token).job_queue(None).build()
    application.add_handler(CommandHandler("start", _start))
    application.add_handler(CallbackQueryHandler(_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, _chat))
    return application
