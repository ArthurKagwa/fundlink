from rest_framework import serializers
from .models import NGO


class NGOSerializer(serializers.ModelSerializer):
    is_active = serializers.ReadOnlyField()
    
    class Meta:
        model = NGO
        fields = ['id', 'name', 'email', 'wallet_address', 'website', 
                 'description', 'approved', 'is_active', 'created_at']
        read_only_fields = ['approved', 'created_at']


class NGOApplicationSerializer(serializers.ModelSerializer):
    """Serializer for NGO application form"""
    
    class Meta:
        model = NGO
        fields = ['name', 'email', 'wallet_address', 'website', 'docs_url', 'description']
    
    def validate_wallet_address(self, value):
        from web3 import Web3
        if not Web3.is_address(value):
            raise serializers.ValidationError("Invalid Ethereum address format.")
        return Web3.to_checksum_address(value.lower())


class NGOPublicSerializer(serializers.ModelSerializer):
    """Public serializer for approved NGOs (used by bot)"""
    
    class Meta:
        model = NGO
        fields = ['id', 'name', 'wallet_address', 'website', 'description']