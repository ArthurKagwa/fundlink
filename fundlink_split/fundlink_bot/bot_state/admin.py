from django.contrib import admin

from .models import BotUser, IntentLog, ConversationState, MessageDelivery


@admin.register(BotUser)
class BotUserAdmin(admin.ModelAdmin):
    list_display = ("telegram_id", "username", "first_name", "last_name", "created_at")
    search_fields = ("telegram_id", "username", "first_name", "last_name")


@admin.register(IntentLog)
class IntentLogAdmin(admin.ModelAdmin):
    list_display = ("telegram_user", "intent", "confidence", "handled", "created_at")
    list_filter = ("intent", "handled")
    search_fields = ("telegram_user__telegram_id", "intent")


@admin.register(ConversationState)
class ConversationStateAdmin(admin.ModelAdmin):
    list_display = ("telegram_user", "updated_at")
    search_fields = ("telegram_user__telegram_id",)


@admin.register(MessageDelivery)
class MessageDeliveryAdmin(admin.ModelAdmin):
    list_display = ("telegram_user", "message_type", "status", "created_at", "delivered_at")
    list_filter = ("status", "message_type")
    search_fields = ("telegram_user__telegram_id", "message_type")
