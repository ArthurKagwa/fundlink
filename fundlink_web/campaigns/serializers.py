from rest_framework import serializers
from .models import Campaign, ImpactPost
from ngos.serializers import NGOPublicSerializer


class CampaignSerializer(serializers.ModelSerializer):
    ngo = NGOPublicSerializer(read_only=True)
    ngo_name = serializers.CharField(source='ngo.name', read_only=True)
    is_live = serializers.ReadOnlyField()
    total_donations = serializers.ReadOnlyField()
    status = serializers.CharField(read_only=True)
    rejection_reason = serializers.CharField(read_only=True)
    funding_progress = serializers.ReadOnlyField()

    class Meta:
        model = Campaign
        fields = [
            'id', 'ngo', 'ngo_name', 'title', 'description', 'token_options',
            'min_amount', 'target_amount', 'status', 'rejection_reason',
            'is_live', 'total_donations', 'funding_progress', 'created_at'
        ]


class CampaignProgressSerializer(serializers.ModelSerializer):
    """Detailed progress tracking serializer for dashboard"""
    ngo_name = serializers.CharField(source='ngo.name', read_only=True)
    funding_progress = serializers.ReadOnlyField()
    total_intents = serializers.ReadOnlyField()
    total_confirmations = serializers.ReadOnlyField()
    intent_to_confirmation_ratio = serializers.ReadOnlyField()
    progress_percentage = serializers.ReadOnlyField()

    class Meta:
        model = Campaign
        fields = [
            'id', 'ngo_name', 'title', 'description', 'target_amount', 
            'funding_progress', 'total_intents', 'total_confirmations',
            'intent_to_confirmation_ratio', 'progress_percentage',
            'status', 'created_at'
        ]


class CampaignCreateSerializer(serializers.ModelSerializer):
    """Serializer for NGOs to create campaigns"""
    class Meta:
        model = Campaign
        fields = ['title', 'description', 'token_options', 'min_amount', 'target_amount']

    def validate_description(self, value):
        if len(value) < 50:
            raise serializers.ValidationError('Description must be at least 50 characters.')
        return value

    def validate_token_options(self, value):
        valid_tokens = ['AVAX', 'USDT']
        if not isinstance(value, list):
            raise serializers.ValidationError("Token options must be a list.")
        if not all(token in valid_tokens for token in value):
            raise serializers.ValidationError(f"Invalid token. Valid options: {valid_tokens}")
        return value


class ImpactPostSerializer(serializers.ModelSerializer):
    campaign_title = serializers.CharField(source='campaign.title', read_only=True)
    ngo_name = serializers.CharField(source='campaign.ngo.name', read_only=True)
    
    class Meta:
        model = ImpactPost
        fields = ['id', 'campaign', 'campaign_title', 'ngo_name', 'title', 
                 'body', 'media_url', 'published', 'created_at']
        read_only_fields = ['published', 'created_at']


class ImpactPostPublicSerializer(serializers.ModelSerializer):
    """Public serializer for published impact posts"""
    campaign_title = serializers.CharField(source='campaign.title', read_only=True)
    ngo_name = serializers.CharField(source='campaign.ngo.name', read_only=True)
    
    class Meta:
        model = ImpactPost
        fields = ['id', 'campaign_title', 'ngo_name', 'title', 'body', 'media_url', 'created_at']