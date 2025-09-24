from django.contrib import admin
from django.utils.html import format_html
from .models import Campaign, ImpactPost


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ['title', 'ngo', 'status_badge', 'is_live', 'created_at']
    list_filter = ['status', 'ngo', 'created_at']
    search_fields = ['title', 'description', 'ngo__name']
    readonly_fields = ['created_at', 'updated_at', 'total_donations', 'submitted_at', 'approved_at', 'reviewed_by']
    actions = ['action_submit', 'action_approve', 'action_reject']

    fieldsets = (
        ('Campaign Details', {
            'fields': ('ngo', 'title', 'description', 'target_amount')
        }),
        ('Settings', {
            'fields': ('token_options', 'min_amount')
        }),
        ('Moderation', {
            'fields': ('status', 'submitted_at', 'approved_at', 'reviewed_by', 'rejection_reason', 'active', 'published')
        }),
        ('Stats', {
            'fields': ('total_donations',),
            'classes': ('collapse',)
        }),
        ('System', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def status_badge(self, obj):
        color_map = {
            'draft': '#999',
            'submitted': '#f0ad4e',
            'approved': '#5cb85c',
            'rejected': '#d9534f'
        }
        color = color_map.get(obj.status, '#999')
        return format_html('<span style="padding:2px 6px; border-radius:4px; background:{}; color:#fff; font-size:0.75rem;">{}</span>', color, obj.status.title())
    status_badge.short_description = 'Status'

    def action_submit(self, request, queryset):
        count = 0
        for c in queryset:
            if c.status in [c.STATUS_DRAFT, c.STATUS_REJECTED]:
                c.submit_for_review()
                count += 1
        self.message_user(request, f'{count} campaign(s) submitted.')
    action_submit.short_description = 'Submit selected (draft/rejected)'

    def action_approve(self, request, queryset):
        count = 0
        for c in queryset:
            if c.status != c.STATUS_APPROVED:
                c.approve(request.user)
                count += 1
        self.message_user(request, f'{count} campaign(s) approved.')
    action_approve.short_description = 'Approve selected campaigns'

    def action_reject(self, request, queryset):
        count = 0
        for c in queryset:
            if c.status != c.STATUS_REJECTED:
                c.reject(request.user, 'Rejected in bulk action')
                count += 1
        self.message_user(request, f'{count} campaign(s) rejected.')
    action_reject.short_description = 'Reject selected campaigns'


@admin.register(ImpactPost)
class ImpactPostAdmin(admin.ModelAdmin):
    list_display = ['title', 'campaign', 'published', 'created_at']
    list_filter = ['published', 'created_at', 'campaign__ngo']
    search_fields = ['title', 'body', 'campaign__title']
    readonly_fields = ['created_at', 'updated_at']
    actions = ['publish_posts', 'unpublish_posts']
    
    def publish_posts(self, request, queryset):
        updated = queryset.update(published=True)
        self.message_user(request, f'{updated} impact posts published.')
    publish_posts.short_description = "Publish selected impact posts"
    
    def unpublish_posts(self, request, queryset):
        updated = queryset.update(published=False)
        self.message_user(request, f'{updated} impact posts unpublished.')
    unpublish_posts.short_description = "Unpublish selected impact posts"
