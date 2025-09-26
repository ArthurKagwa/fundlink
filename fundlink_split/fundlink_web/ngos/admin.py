from django.contrib import admin
from django.utils.html import format_html
from .models import NGO


@admin.register(NGO)
class NGOAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'wallet_address', 'status_badge', 'approved_at', 'created_at']
    list_filter = ['status', 'approved', 'created_at']
    search_fields = ['name', 'email', 'wallet_address']
    readonly_fields = ['created_at', 'updated_at', 'approved_at', 'reviewed_by']
    actions = ['action_approve', 'action_reject_reset']

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'email', 'description')
        }),
        ('Verification', {
            'fields': ('wallet_address', 'website', 'docs_url')
        }),
        ('Moderation', {
            'fields': ('status', 'approved', 'approved_at', 'reviewed_by', 'rejection_reason')
        }),
        ('System', {
            'fields': ('user', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def status_badge(self, obj):
        color_map = {
            'submitted': '#f0ad4e',
            'approved': '#5cb85c',
            'rejected': '#d9534f'
        }
        color = color_map.get(obj.status, '#999')
        return format_html('<span style="padding:2px 6px; border-radius:4px; background:{}; color:#fff; font-size:0.75rem;">{}</span>', color, obj.status.title())
    status_badge.short_description = 'Status'

    def action_approve(self, request, queryset):
        count = 0
        for ngo in queryset:
            if ngo.status != ngo.STATUS_APPROVED:
                ngo.approve(request.user)
                count += 1
        self.message_user(request, f'{count} NGO(s) approved.')
    action_approve.short_description = 'Approve selected NGOs'

    def action_reject_reset(self, request, queryset):
        updated = 0
        for ngo in queryset:
            if ngo.status != ngo.STATUS_REJECTED:
                ngo.reject(request.user, reason='Rejected in bulk action')
                updated += 1
        self.message_user(request, f'{updated} NGO(s) rejected.')
    action_reject_reset.short_description = 'Reject selected NGOs'
