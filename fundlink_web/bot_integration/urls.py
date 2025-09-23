from django.urls import path
from .views import bot_notify, webhook_telegram, health_check, register_user

urlpatterns = [
    path('notify/', bot_notify, name='bot-notify'),
    path('register-user/', register_user, name='bot-register-user'),
    path('webhook/telegram/', webhook_telegram, name='webhook-telegram'),
    path('health/', health_check, name='health-check'),
]