from django.urls import path

from .views import health_check, telegram_webhook

app_name = "telegram_gateway"

urlpatterns = [
    path("healthz/", health_check, name="health"),
    path("telegram/webhook/", telegram_webhook, name="telegram-webhook"),
]
