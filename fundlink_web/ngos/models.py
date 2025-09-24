from django.db import models
from django.contrib.auth.models import User
from django.core.validators import URLValidator
from django.utils import timezone
from django.db.models import Q
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models.functions import Lower
from django.core.exceptions import ValidationError
from django.db import transaction
# from web3 import Web3  # Re-enable when needed


class NGO(models.Model):
    name = models.CharField(max_length=200)
    email = models.EmailField(unique=True)
    wallet_address = models.CharField(max_length=42, unique=True)  # Ethereum address
    website = models.URLField(blank=True)
    docs_url = models.URLField(blank=True, help_text="Documentation or verification URL")
    description = models.TextField(blank=True)
    approved = models.BooleanField(default=False)
    # Moderation workflow fields
    STATUS_SUBMITTED = 'submitted'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'
    STATUS_CHOICES = [
        (STATUS_SUBMITTED, 'Submitted'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_REJECTED, 'Rejected'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_SUBMITTED)
    approved_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='reviewed_ngos')
    rejection_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Link to Django User for authentication
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    
    class Meta:
        verbose_name = "NGO"
        verbose_name_plural = "NGOs"
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        # Normalize wallet address to lowercase (checksum to be added later)
        if self.wallet_address:
            self.wallet_address = self.wallet_address.lower()
        # Keep legacy approved boolean in sync with status
        if self.status == self.STATUS_APPROVED and not self.approved:
            self.approved = True
        elif self.status != self.STATUS_APPROVED and self.approved:
            # Only unset if explicitly moved out of approved
            if self.status in (self.STATUS_SUBMITTED, self.STATUS_REJECTED):
                self.approved = False
        super().save(*args, **kwargs)
    
    @property
    def is_active(self):
        return self.approved and self.wallet_address

    @property
    def is_rejected(self):
        return self.status == self.STATUS_REJECTED

    def approve(self, reviewer: User):
        self.status = self.STATUS_APPROVED
        self.approved = True
        self.approved_at = timezone.now()
        self.reviewed_by = reviewer
        self.rejection_reason = ''
        self.save()

    def reject(self, reviewer: User, reason: str):
        if not reason:
            raise ValidationError('Rejection reason required')
        self.status = self.STATUS_REJECTED
        self.approved = False
        self.reviewed_by = reviewer
        self.rejection_reason = reason
        self.save()

