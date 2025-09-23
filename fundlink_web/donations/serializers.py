from rest_framework import serializers
from .models import Donation, BotUser
from campaigns.serializers import CampaignSerializer
from ngos.serializers import NGOPublicSerializer


class DonationSerializer(serializers.ModelSerializer):
    ngo = NGOPublicSerializer(read_only=True)
    campaign = CampaignSerializer(read_only=True)
    explorer_url = serializers.ReadOnlyField()
    is_confirmed = serializers.ReadOnlyField()
    
    class Meta:
        model = Donation
        fields = ['id', 'ngo', 'campaign', 'token', 'amount_decimal', 
                 'tx_hash', 'explorer_url', 'is_confirmed', 'confirmed_at', 'created_at']


class DonationCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating donation records (used by verifier)"""
    
    class Meta:
        model = Donation
        fields = ['ngo', 'campaign', 'token', 'amount_decimal', 'tx_hash', 
                 'chain_id', 'donor_telegram_id', 'confirmed_at']


class BotUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = BotUser
        fields = ['telegram_id', 'username', 'first_name', 'last_name', 'last_seen_at', 'created_at']


class DonorHistorySerializer(serializers.ModelSerializer):
    """Simplified serializer for donor history in Telegram bot"""
    ngo_name = serializers.CharField(source='ngo.name', read_only=True)
    campaign_title = serializers.CharField(source='campaign.title', read_only=True)
    explorer_url = serializers.ReadOnlyField()
    
    class Meta:
        model = Donation
        fields = ['id', 'ngo_name', 'campaign_title', 'token', 'amount_decimal', 
                 'explorer_url', 'confirmed_at', 'created_at']