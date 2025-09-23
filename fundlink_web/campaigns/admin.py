from django.contrib import admin
from .models import Campaign, ImpactPost


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ['title', 'ngo', 'active', 'published', 'created_at']
    list_filter = ['active', 'published', 'created_at', 'ngo']
    search_fields = ['title', 'description', 'ngo__name']
    readonly_fields = ['created_at', 'updated_at', 'total_donations']
    actions = ['publish_campaigns', 'unpublish_campaigns', 'activate_campaigns', 'deactivate_campaigns']
    
    fieldsets = (
        ('Campaign Details', {
            'fields': ('ngo', 'title', 'description', 'target_amount')
        }),
        ('Settings', {
            'fields': ('token_options', 'min_amount', 'active', 'published')
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
    
    def publish_campaigns(self, request, queryset):
        updated = queryset.update(published=True)
        self.message_user(request, f'{updated} campaigns published.')
    publish_campaigns.short_description = "Publish selected campaigns"
    
    def unpublish_campaigns(self, request, queryset):
        updated = queryset.update(published=False)
        self.message_user(request, f'{updated} campaigns unpublished.')
    unpublish_campaigns.short_description = "Unpublish selected campaigns"
    
    def activate_campaigns(self, request, queryset):
        updated = queryset.update(active=True)
        self.message_user(request, f'{updated} campaigns activated.')
    activate_campaigns.short_description = "Activate selected campaigns"
    
    def deactivate_campaigns(self, request, queryset):
        updated = queryset.update(active=False)
        self.message_user(request, f'{updated} campaigns deactivated.')
    deactivate_campaigns.short_description = "Deactivate selected campaigns"


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
