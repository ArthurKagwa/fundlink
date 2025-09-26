from telegram import Update
from telegram.ext import ContextTypes

# Import the message handler from the parent package
try:
    from telbot_llm.telbot_llm.handlers import handle_message, handle_callback_query
except ImportError:
    # Try alternate import paths
    try:
        from ...telbot_llm.handlers import handle_message, handle_callback_query
    except ImportError:
        # If all else fails, try directly importing from the module
        import sys
        import os
        sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
        from telbot_llm.handlers import handle_message, handle_callback_query

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for the /start command"""
    user_name = update.effective_user.first_name
    await update.message.reply_text(
        f"Welcome {user_name}! I'm the Fundlink donation assistant.\n\n"
        "💝 Say 'campaigns' to see active humanitarian campaigns\n"
        "💰 Or try 'donate 0.001 to [campaign name]' for quick donations\n"
        "📊 Say 'my donations' to see your donation history"
    )

async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for regular messages that processes them through LLM"""
    # Show typing indicator
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    # Use the main handler for processing messages
    await handle_message(update, context)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for inline keyboard button callbacks"""
    await handle_callback_query(update, context)