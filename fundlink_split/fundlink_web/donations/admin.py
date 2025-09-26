from django.contrib import admin
from .models import Donation, BotUser


@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = ['amount_decimal', 'token', 'ngo', 'campaign', 'is_confirmed', 'created_at']
    list_filter = ['token', 'confirmed_at', 'created_at', 'ngo', 'chain_id']
    search_fields = ['tx_hash', 'ngo__name', 'campaign__title', 'donor_telegram_id']
    readonly_fields = ['tx_hash', 'chain_id', 'confirmed_at', 'created_at', 'explorer_url']
    
    fieldsets = (
        ('Donation Details', {
            'fields': ('ngo', 'campaign', 'token', 'amount_decimal')
        }),
        ('Blockchain', {
            'fields': ('tx_hash', 'chain_id', 'confirmed_at', 'explorer_url')
        }),
        ('Donor', {
            'fields': ('donor_telegram_id', 'bot_user')
        }),
        ('System', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        })
    )
    
    def is_confirmed(self, obj):
        return obj.is_confirmed
    is_confirmed.boolean = True
    is_confirmed.short_description = 'Confirmed'


@admin.register(BotUser)
class BotUserAdmin(admin.ModelAdmin):
    list_display = ['telegram_id', 'username', 'first_name', 'last_name', 'last_seen_at']
    search_fields = ['telegram_id', 'username', 'first_name', 'last_name']
    readonly_fields = ['telegram_id', 'last_seen_at', 'created_at']
