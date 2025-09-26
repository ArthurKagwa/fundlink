from __future__ import annotations

import logging
import os
import signal
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Run the FundLink Telegram bot with webhook or polling runtime"

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--mode",
            choices=["webhook", "polling"],
            default="webhook",
            help="Run mode for python-telegram-bot application",
        )
        parser.add_argument(
            "--webhook-url",
            dest="webhook_url",
            default=None,
            help="Override webhook URL (defaults to TELEGRAM_WEBHOOK_URL)",
        )
        parser.add_argument(
            "--listen",
            default="0.0.0.0",
            help="Webhook listener host",
        )
        parser.add_argument(
            "--port",
            type=int,
            default=8443,
            help="Webhook listener port",
        )
        parser.add_argument(
            "--drop-pending",
            action="store_true",
            help="Drop pending updates when starting polling",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        from telegram.error import InvalidToken

        mode = options["mode"]
        webhook_url = options["webhook_url"] or settings.TELEGRAM_WEBHOOK_URL
        listen = options["listen"]
        port = options["port"]
        drop_pending = bool(options.get("drop_pending"))

        from telegram_gateway.handlers import build_application

        application = build_application()
        self._register_signals(application)

        try:
            import asyncio

            asyncio.run(application.initialize())
        except InvalidToken as exc:
            raise SystemExit(f"Invalid Telegram token: {exc}")

        if mode == "polling":
            self.stdout.write(self.style.SUCCESS("Starting bot in polling mode"))
            application.run_polling(drop_pending_updates=drop_pending)
        else:
            if not webhook_url:
                raise SystemExit("TELEGRAM_WEBHOOK_URL must be configured for webhook mode")
            from urllib.parse import urlparse

            parsed = urlparse(webhook_url)
            url_path = parsed.path.lstrip("/")

            self.stdout.write(self.style.SUCCESS(f"Starting webhook at {webhook_url}"))
            application.run_webhook(
                listen=listen,
                port=port,
                url_path=url_path,
                webhook_url=webhook_url,
            )

    def _register_signals(self, application) -> None:
        def _shutdown(signum, frame):
            logger.info("Received shutdown signal %s", signum)
            application.stop()

        for sig in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sig, _shutdown)
