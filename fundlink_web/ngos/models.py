from django.db import models
from django.contrib.auth.models import User
from django.core.validators import URLValidator
# from web3 import Web3  # Temporarily commented out until web3 is installed


class NGO(models.Model):
    name = models.CharField(max_length=200)
    email = models.EmailField(unique=True)
    wallet_address = models.CharField(max_length=42, unique=True)  # Ethereum address
    website = models.URLField(blank=True)
    docs_url = models.URLField(blank=True, help_text="Documentation or verification URL")
    description = models.TextField(blank=True)
    approved = models.BooleanField(default=False)
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
        # Ensure wallet address is checksummed
        if self.wallet_address:
            # TODO: Re-enable when web3 is installed
            # self.wallet_address = Web3.to_checksum_address(self.wallet_address.lower())
            self.wallet_address = self.wallet_address.lower()  # Temporary fix
        super().save(*args, **kwargs)
    
    @property
    def is_active(self):
        return self.approved and self.wallet_address
