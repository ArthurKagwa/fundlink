from django.db import models
from django.utils import timezone
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
    published = models.BooleanField(default=False)  # Legacy booleans kept for compatibility
    STATUS_DRAFT = 'draft'
    STATUS_SUBMITTED = 'submitted'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'
    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Draft'),
        (STATUS_SUBMITTED, 'Submitted'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_REJECTED, 'Rejected'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    submitted_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey('auth.User', null=True, blank=True, on_delete=models.SET_NULL, related_name='reviewed_campaigns')
    rejection_reason = models.TextField(blank=True)
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
        # Derive from status + NGO
        return self.status == self.STATUS_APPROVED and self.ngo.approved
    
    @property
    def total_donations(self):
        return self.donations.filter(confirmed_at__isnull=False).aggregate(
            total=models.Sum('amount_decimal')
        )['total'] or 0

    # Moderation helpers
    def submit_for_review(self):
        if self.status != self.STATUS_DRAFT and self.status != self.STATUS_REJECTED:
            return
        self.status = self.STATUS_SUBMITTED
        self.submitted_at = timezone.now()
        self.save()

    def approve(self, reviewer):
        self.status = self.STATUS_APPROVED
        self.published = True
        self.active = True
        self.approved_at = timezone.now()
        self.reviewed_by = reviewer
        self.rejection_reason = ''
        self.save()

    def reject(self, reviewer, reason: str):
        self.status = self.STATUS_REJECTED
        self.published = False
        self.active = False
        self.reviewed_by = reviewer
        self.rejection_reason = reason
        self.save()


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
