"""HTTP entrypoints for the Telegram-facing Django service."""

from __future__ import annotations

import asyncio
import json
import logging

from django.conf import settings
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

try:  # local dependency; fallback stub during initial scaffolding
    from telegram import Update
    from telegram.ext import Application
except Exception:  # pragma: no cover - optional until dependencies installed
    Update = None  # type: ignore
    Application = None  # type: ignore

logger = logging.getLogger(__name__)


def health_check(request: HttpRequest) -> JsonResponse:
    return JsonResponse({
        "status": "ok",
        "service": "fundlink_bot",
    })


@csrf_exempt
def telegram_webhook(request: HttpRequest) -> HttpResponse:
    if request.method != "POST":
        return JsonResponse({"error": "method_not_allowed"}, status=405)

    if Application is None or Update is None:
        logger.warning("telegram.ext not available; ignoring update")
        return JsonResponse({"ok": False, "error": "telegram_lib_missing"}, status=503)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "error": "invalid_json"}, status=400)

    application: Application | None = getattr(settings, "TELEGRAM_APPLICATION", None)  # type: ignore[attr-defined]
    if application is None:
        from .handlers import build_application

        try:
            application = build_application()
            asyncio.run(application.initialize())
        except Exception as exc:
            logger.exception("Unable to build telegram application", exc_info=exc)
            return JsonResponse({"ok": False, "error": "bot_unavailable"}, status=503)
        else:
            settings.TELEGRAM_APPLICATION = application

    update = Update.de_json(payload, application.bot)
    asyncio.run(application.process_update(update))
    return JsonResponse({"ok": True})
