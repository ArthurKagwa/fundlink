from rest_framework import serializers
from .models import Donation, DonationIntent, BotUser
from campaigns.serializers import CampaignProgressSerializer
from ngos.serializers import NGOPublicSerializer


class DonationSerializer(serializers.ModelSerializer):
    ngo = NGOPublicSerializer(read_only=True)
    campaign_title = serializers.CharField(source='campaign.title', read_only=True)
    explorer_url = serializers.ReadOnlyField()
    is_confirmed = serializers.ReadOnlyField()
    intent_reference = serializers.SerializerMethodField()
    
    class Meta:
        model = Donation
        fields = [
            'id',
            'ngo',
            'campaign',
            'campaign_title',
            'token',
            'amount_decimal',
            'value_base_units',
            'tx_hash',
            'chain_id',
            'sender_address',
            'recipient_address',
            'block_number',
            'tx_timestamp',
            'donor_telegram_id',
            'explorer_url',
            'is_confirmed',
            'confirmed_at',
            'created_at',
            'intent_reference',
        ]

    def get_intent_reference(self, obj):
        return obj.intent.reference if obj.intent else None


class DonationCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating donation records (used by verifier)"""
    
    class Meta:
        model = Donation
        fields = [
            'ngo',
            'campaign',
            'token',
            'amount_decimal',
            'value_base_units',
            'tx_hash',
            'chain_id',
            'donor_telegram_id',
            'confirmed_at',
        ]


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
        fields = [
            'id',
            'ngo_name',
            'campaign_title',
            'token',
            'amount_decimal',
            'explorer_url',
            'confirmed_at',
            'created_at',
        ]


class DonationIntentSerializer(serializers.ModelSerializer):
    ngo = NGOPublicSerializer(read_only=True)
    campaign_title = serializers.CharField(source='campaign.title', read_only=True)

    class Meta:
        model = DonationIntent
        fields = [
            'id',
            'reference',
            'ngo',
            'campaign',
            'campaign_title',
            'token',
            'token_decimals',
            'amount_decimal',
            'value_base_units',
            'wallet_address',
            'donor_telegram_id',
            'status',
            'created_at',
            'expires_at',
        ]
