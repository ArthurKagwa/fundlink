from django.apps import AppConfig
from django.conf import settings


class TelegramGatewayConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "telegram_gateway"
    verbose_name = "Telegram Gateway"

    def ready(self) -> None:  # pragma: no cover - requires Django runtime
        if getattr(settings, "TELEGRAM_APPLICATION", None) is None:
            from .handlers import build_application
            import asyncio
            import logging

            logger = logging.getLogger(__name__)
            try:
                application = build_application()
                asyncio.run(application.initialize())
            except RuntimeError as exc:
                logger.warning("Telegram application not initialised: %s", exc)
            except Exception as exc:  # pragma: no cover - defensive
                logger.exception("Failed to initialise Telegram application", exc_info=exc)
            else:
                settings.TELEGRAM_APPLICATION = application
