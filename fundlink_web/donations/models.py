from django.db import models
from ngos.models import NGO
from campaigns.models import Campaign


class BotUser(models.Model):
    telegram_id = models.BigIntegerField(unique=True)
    username = models.CharField(max_length=100, blank=True)
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    last_seen_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"@{self.username}" if self.username else f"User {self.telegram_id}"


class Donation(models.Model):
    TOKEN_CHOICES = [
        ('AVAX', 'AVAX'),
        ('USDT', 'USDT'),
    ]
    
    ngo = models.ForeignKey(NGO, on_delete=models.CASCADE, related_name='received_donations')
    campaign = models.ForeignKey(Campaign, on_delete=models.SET_NULL, null=True, blank=True, related_name='donations')
    token = models.CharField(max_length=10, choices=TOKEN_CHOICES)
    amount_decimal = models.DecimalField(max_digits=20, decimal_places=6)
    tx_hash = models.CharField(max_length=66, unique=True)  # Ethereum transaction hash
    chain_id = models.IntegerField(default=43113)  # Avalanche Fuji
    donor_telegram_id = models.BigIntegerField(null=True, blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Optional: link to BotUser if available
    bot_user = models.ForeignKey(BotUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='donations')
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['ngo', 'created_at']),
            models.Index(fields=['campaign', 'created_at']),
            models.Index(fields=['donor_telegram_id', 'created_at']),
            models.Index(fields=['tx_hash']),
        ]
    
    def __str__(self):
        return f"{self.amount_decimal} {self.token} to {self.ngo.name}"
    
    @property
    def explorer_url(self):
        return f"https://testnet.snowtrace.io/tx/{self.tx_hash}"
    
    @property
    def is_confirmed(self):
        return self.confirmed_at is not None
