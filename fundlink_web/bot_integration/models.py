from django.db import models


class NotificationLog(models.Model):
    """Track notification attempts to Telegram users"""
    telegram_id = models.BigIntegerField()
    message_type = models.CharField(max_length=50)  # 'donation_receipt', 'impact_update', etc.
    message_data = models.JSONField()
    sent_successfully = models.BooleanField(default=False)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.message_type} to {self.telegram_id} - {'✓' if self.sent_successfully else '✗'}"
