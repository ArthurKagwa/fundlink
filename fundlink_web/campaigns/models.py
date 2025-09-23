from django.db import models
from ngos.models import NGO


class Campaign(models.Model):
    TOKEN_CHOICES = [
        ('AVAX', 'AVAX'),
        ('USDT', 'USDT'),
    ]
    
    ngo = models.ForeignKey(NGO, on_delete=models.CASCADE, related_name='campaigns')
    title = models.CharField(max_length=200)
    description = models.TextField()
    active = models.BooleanField(default=False)
    published = models.BooleanField(default=False)  # Admin approval required
    token_options = models.JSONField(default=list, help_text="List of accepted tokens: ['AVAX', 'USDT']")
    min_amount = models.DecimalField(max_digits=20, decimal_places=6, default=0.01, help_text="Minimum donation amount")
    target_amount = models.DecimalField(max_digits=20, decimal_places=6, null=True, blank=True, help_text="Optional funding target")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.ngo.name}"
    
    @property
    def is_live(self):
        return self.active and self.published and self.ngo.approved
    
    @property
    def total_donations(self):
        return self.donations.filter(confirmed_at__isnull=False).aggregate(
            total=models.Sum('amount_decimal')
        )['total'] or 0


class ImpactPost(models.Model):
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='impact_posts')
    title = models.CharField(max_length=200)
    body = models.TextField()
    media_url = models.URLField(blank=True, help_text="Optional image or video URL")
    published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.campaign.title}"
