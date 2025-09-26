from rest_framework import serializers
from django.contrib.auth.models import User
from .models import NGO


class NGOSerializer(serializers.ModelSerializer):
    is_active = serializers.ReadOnlyField()
    status = serializers.CharField(read_only=True)
    rejection_reason = serializers.CharField(read_only=True)
    
    class Meta:
        model = NGO
    fields = ['id', 'name', 'email', 'wallet_address', 'website', 'docs_url',
          'description', 'approved', 'status', 'rejection_reason', 'is_active', 'created_at']
    read_only_fields = ['approved', 'status', 'rejection_reason', 'created_at']


class NGOApplicationSerializer(serializers.ModelSerializer):
    """Serializer for NGO application form with optional password creation"""
    password = serializers.CharField(write_only=True, required=False, min_length=8)
    password_confirm = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = NGO
        fields = ['name', 'email', 'wallet_address', 'website', 'docs_url', 'description', 'password', 'password_confirm']

    def validate_description(self, value):
        if len(value) < 100:
            raise serializers.ValidationError('Description must be at least 100 characters.')
        if len(value) > 500:
            raise serializers.ValidationError('Description must not exceed 500 characters.')
        return value

    def validate(self, attrs):
        pw = attrs.get('password')
        pwc = attrs.get('password_confirm')
        if pw or pwc:
            if pw != pwc:
                raise serializers.ValidationError({'password_confirm': 'Passwords do not match.'})
        return attrs

    def validate_wallet_address(self, value):
        # Lightweight format validation; full checksum later
        if not value.startswith('0x') or len(value) != 42:
            raise serializers.ValidationError('Invalid Ethereum/Avalanche address format.')
        return value.lower()

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        validated_data.pop('password_confirm', None)
        ngo = super().create(validated_data)
        if password:
            user = User.objects.create_user(username=ngo.email, email=ngo.email, password=password)
            ngo.user = user
            ngo.save()
        return ngo


class NGOPublicSerializer(serializers.ModelSerializer):
    """Public serializer for approved NGOs (used by bot)"""
    class Meta:
        model = NGO
        fields = ['id', 'name', 'wallet_address', 'website', 'description']

class NGOApprovalSerializer(serializers.ModelSerializer):
    class Meta:
        model = NGO
        fields = ['id', 'status', 'approved_at', 'rejection_reason']
        read_only_fields = ['approved_at']
