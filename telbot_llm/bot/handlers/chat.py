from telegram import Update
from telegram.ext import ContextTypes

# Import the message handler from the parent package
from ...telbot_llm.handlers import handle_message

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for the /start command"""
    user_name = update.effective_user.first_name
    await update.message.reply_text(
        f"Welcome {user_name}! I'm the Fundlink donation assistant. "
        "Ask me about active campaigns or how to donate to humanitarian causes."
    )

async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for regular messages that processes them through LLM"""
    # Show typing indicator
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    # Use the main handler for processing messages
    await handle_message(update, context)