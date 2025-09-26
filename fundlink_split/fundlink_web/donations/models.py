import uuid
from datetime import datetime
from decimal import Decimal

from django.db import models
from django.utils import timezone

from ngos.models import NGO
from campaigns.models import Campaign


def _default_reference() -> str:
    return uuid.uuid4().hex


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
    value_base_units = models.DecimalField(max_digits=78, decimal_places=0, null=True, blank=True)
    tx_hash = models.CharField(max_length=66, unique=True, null=True, blank=True)  # Ethereum transaction hash
    chain_id = models.IntegerField(default=43113)  # Avalanche Fuji
    sender_address = models.CharField(max_length=42, blank=True)
    recipient_address = models.CharField(max_length=42, blank=True)
    block_number = models.BigIntegerField(null=True, blank=True)
    tx_timestamp = models.DateTimeField(null=True, blank=True)
    donor_telegram_id = models.BigIntegerField(null=True, blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # Optional: link to BotUser if available
    bot_user = models.ForeignKey(BotUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='donations')
    intent = models.OneToOneField('DonationIntent', on_delete=models.SET_NULL, null=True, blank=True, related_name='donation')

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['ngo', 'created_at']),
            models.Index(fields=['campaign', 'created_at']),
            models.Index(fields=['donor_telegram_id', 'created_at']),
            models.Index(fields=['tx_hash']),
            models.Index(fields=['recipient_address', 'created_at']),
        ]

    def __str__(self):
        return f"{self.amount_decimal} {self.token} to {self.ngo.name}"

    @property
    def explorer_url(self):
        if not self.tx_hash:
            return ""
        return f"https://testnet.snowtrace.io/tx/{self.tx_hash}"

    @property
    def is_confirmed(self):
        return self.confirmed_at is not None

    def mark_confirmed(
        self,
        *,
        tx_hash: str,
        chain_id: int,
        sender: str | None = None,
        recipient: str | None = None,
        block_number: int | None = None,
        timestamp: datetime | None = None,
        value_base_units: Decimal | None = None,
    ):
        self.tx_hash = tx_hash
        self.chain_id = chain_id
        if sender:
            self.sender_address = sender.lower()
        if recipient:
            self.recipient_address = recipient.lower()
        if block_number is not None:
            self.block_number = block_number
        if timestamp:
            self.tx_timestamp = timestamp
        if value_base_units is not None:
            self.value_base_units = value_base_units
        self.confirmed_at = timezone.now()
        self.save(update_fields=[
            'tx_hash',
            'chain_id',
            'sender_address',
            'recipient_address',
            'block_number',
            'tx_timestamp',
            'value_base_units',
            'confirmed_at',
        ])


class DonationIntent(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_FULFILLED = 'fulfilled'
    STATUS_EXPIRED = 'expired'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_FULFILLED, 'Fulfilled'),
        (STATUS_EXPIRED, 'Expired'),
    ]

    reference = models.CharField(max_length=36, unique=True, default=_default_reference)
    ngo = models.ForeignKey(NGO, on_delete=models.CASCADE, related_name='donation_intents')
    campaign = models.ForeignKey(Campaign, on_delete=models.SET_NULL, null=True, blank=True, related_name='donation_intents')
    token = models.CharField(max_length=10, choices=Donation.TOKEN_CHOICES)
    token_decimals = models.PositiveSmallIntegerField(default=18)
    amount_decimal = models.DecimalField(max_digits=20, decimal_places=6)
    value_base_units = models.DecimalField(max_digits=78, decimal_places=0)
    wallet_address = models.CharField(max_length=42)
    donor_telegram_id = models.BigIntegerField(null=True, blank=True)
    bot_user = models.ForeignKey(BotUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='donation_intents')
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=STATUS_PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    fulfilled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['wallet_address', 'status', 'token']),
            models.Index(fields=['donor_telegram_id', 'status']),
        ]

    def __str__(self):
        return f"Intent {self.reference} ({self.amount_decimal} {self.token})"

    @property
    def is_active(self) -> bool:
        if self.status != self.STATUS_PENDING:
            return False
        if self.expires_at and timezone.now() > self.expires_at:
            return False
        return True

    def mark_fulfilled(self):
        self.status = self.STATUS_FULFILLED
        self.fulfilled_at = timezone.now()
        self.save(update_fields=['status', 'fulfilled_at'])

    def mark_expired(self):
        self.status = self.STATUS_EXPIRED
        self.save(update_fields=['status'])
