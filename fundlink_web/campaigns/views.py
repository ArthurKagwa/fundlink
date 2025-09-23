from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import Campaign, ImpactPost
from .serializers import (
    CampaignSerializer, CampaignCreateSerializer, 
    ImpactPostSerializer, ImpactPostPublicSerializer
)


class CampaignViewSet(viewsets.ModelViewSet):
    serializer_class = CampaignSerializer
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsAuthenticated()]
    
    def get_queryset(self):
        if self.action in ['list', 'retrieve']:
            # Only return live campaigns for public access
            return Campaign.objects.filter(active=True, published=True, ngo__approved=True)
        elif hasattr(self.request.user, 'ngo'):
            # NGO users only see their own campaigns
            return Campaign.objects.filter(ngo=self.request.user.ngo)
        return Campaign.objects.none()
    
    def get_serializer_class(self):
        if self.action == 'create':
            return CampaignCreateSerializer
        return super().get_serializer_class()
    
    def perform_create(self, serializer):
        # Associate campaign with the logged-in NGO
        serializer.save(ngo=self.request.user.ngo)


class ImpactPostViewSet(viewsets.ModelViewSet):
    serializer_class = ImpactPostSerializer
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsAuthenticated()]
    
    def get_queryset(self):
        if self.action in ['list', 'retrieve']:
            # Only return published impact posts
            return ImpactPost.objects.filter(published=True, campaign__ngo__approved=True)
        elif hasattr(self.request.user, 'ngo'):
            # NGO users only see their own impact posts
            return ImpactPost.objects.filter(campaign__ngo=self.request.user.ngo)
        return ImpactPost.objects.none()
    
    def get_serializer_class(self):
        if self.action in ['list', 'retrieve'] and not self.request.user.is_authenticated:
            return ImpactPostPublicSerializer
        return super().get_serializer_class()
    
    def perform_create(self, serializer):
        # Ensure the campaign belongs to the logged-in NGO
        campaign = serializer.validated_data['campaign']
        if campaign.ngo != self.request.user.ngo:
            raise PermissionError("You can only create impact posts for your own campaigns.")
        serializer.save()
