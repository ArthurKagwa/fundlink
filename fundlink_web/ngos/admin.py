from django.contrib import admin
from .models import NGO


@admin.register(NGO)
class NGOAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'wallet_address', 'approved', 'created_at']
    list_filter = ['approved', 'created_at']
    search_fields = ['name', 'email', 'wallet_address']
    readonly_fields = ['created_at', 'updated_at']
    actions = ['approve_ngos', 'unapprove_ngos']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'email', 'description')
        }),
        ('Verification', {
            'fields': ('wallet_address', 'website', 'docs_url', 'approved')
        }),
        ('System', {
            'fields': ('user', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def approve_ngos(self, request, queryset):
        updated = queryset.update(approved=True)
        self.message_user(request, f'{updated} NGOs approved.')
    approve_ngos.short_description = "Approve selected NGOs"
    
    def unapprove_ngos(self, request, queryset):
        updated = queryset.update(approved=False)
        self.message_user(request, f'{updated} NGOs unapproved.')
    unapprove_ngos.short_description = "Unapprove selected NGOs"
