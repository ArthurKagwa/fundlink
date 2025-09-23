import os
import sys
import logging
import signal
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import connection

# Add telbot_llm to path if needed
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
telbot_llm_path = os.path.join(project_root, 'telbot_llm')
if telbot_llm_path not in sys.path:
    sys.path.append(telbot_llm_path)
    
# Print paths for debugging
print(f"Project root: {project_root}")
print(f"telbot_llm path: {telbot_llm_path}")
print(f"Current working directory: {os.getcwd()}")
print(f"Python path: {sys.path}")

# Check if the directory exists
if not os.path.isdir(telbot_llm_path):
    print(f"ERROR: {telbot_llm_path} directory does not exist!")
elif not os.path.isdir(os.path.join(telbot_llm_path, 'bot')):
    print(f"ERROR: {telbot_llm_path}/bot directory does not exist!")

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Run the LLM-powered Telegram bot with Django integration'

    def add_arguments(self, parser):
        parser.add_argument(
            '--polling',
            action='store_true',
            help='Run in polling mode instead of webhook',
        )
        parser.add_argument(
            '--drop-pending',
            action='store_true',
            help='Drop pending updates when starting in polling mode',
        )
        parser.add_argument(
            '--webhook-url',
            type=str,
            help='Override webhook URL (defaults to PUBLIC_WEBHOOK_BASE/bot_integration/webhook/telegram/)',
        )

    def handle(self, *args, **options):
        # Validate required environment variables
        token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not token:
            self.stderr.write(self.style.ERROR('TELEGRAM_BOT_TOKEN not set in environment'))
            return
            
        # Check for Together API key if using LLM features
        together_key = os.getenv('TOGETHER_API_KEY')
        if not together_key:
            self.stdout.write(self.style.WARNING('TOGETHER_API_KEY not set - LLM features will be disabled'))

        # Import bot after environment validation
        try:
            # Try different import methods
            try:
                # Try direct import first
                from telbot_llm.bot.main import build, run_polling, run_webhook
            except ImportError:
                # If that doesn't work, try explicit import
                import importlib.util
                spec = importlib.util.spec_from_file_location(
                    "main", 
                    os.path.join(telbot_llm_path, "bot", "main.py")
                )
                if spec is None:
                    raise ImportError(f"Could not find main.py in {telbot_llm_path}/bot/")
                    
                main_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(main_module)
                build = main_module.build
                run_polling = main_module.run_polling
                run_webhook = main_module.run_webhook
        except ImportError as e:
            self.stderr.write(self.style.ERROR(f"Failed to import bot module: {e}"))
            self.stderr.write(self.style.ERROR("Ensure telbot_llm package is installed and accessible"))
            return

        # Signal handlers for graceful shutdown
        def signal_handler(sig, frame):
            self.stdout.write(self.style.WARNING('Received shutdown signal, stopping bot...'))
            if connection.connection:
                connection.close()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Run bot in specified mode
        if options['polling']:
            self.stdout.write(self.style.SUCCESS('Starting Telegram bot in polling mode'))
            run_polling(drop_pending=options['drop_pending'])
        else:
            # Get webhook URL
            webhook_url = options['webhook_url']
            if not webhook_url:
                base_url = os.getenv('PUBLIC_WEBHOOK_BASE')
                if not base_url:
                    self.stderr.write(self.style.ERROR('PUBLIC_WEBHOOK_BASE not set and no webhook URL provided'))
                    return
                webhook_url = f"{base_url.rstrip('/')}/bot_integration/webhook/telegram/"
            
            self.stdout.write(self.style.SUCCESS(f'Starting Telegram bot in webhook mode: {webhook_url}'))
            run_webhook(webhook_url=webhook_url)