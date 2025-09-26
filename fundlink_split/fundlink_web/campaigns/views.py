from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from django.db import transaction
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
        if self.action in ['approve', 'reject']:
            return [IsAdminUser()]
        return [IsAuthenticated()]
    
    def get_queryset(self):
        if self.action in ['list', 'retrieve']:
            # Only return live campaigns for public access
            return Campaign.objects.filter(status=Campaign.STATUS_APPROVED, ngo__status='approved')
        if hasattr(self.request.user, 'ngo'):
            return Campaign.objects.filter(ngo=self.request.user.ngo)
        return Campaign.objects.all()
    
    def get_serializer_class(self):
        if self.action == 'create':
            return CampaignCreateSerializer
        return super().get_serializer_class()
    
    def perform_create(self, serializer):
        # Associate campaign with the logged-in NGO
        ngo = getattr(self.request.user, 'ngo', None)
        if not ngo or ngo.status != 'approved':
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('NGO must be approved to create campaigns.')
        serializer.save(ngo=ngo)

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        campaign = self.get_object()
        if not hasattr(request.user, 'ngo') or campaign.ngo != request.user.ngo:
            return Response({'detail': 'Not allowed.'}, status=status.HTTP_403_FORBIDDEN)
        campaign.submit_for_review()
        return Response({'id': campaign.id, 'status': campaign.status})

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        campaign = self.get_object()
        with transaction.atomic():
            campaign.approve(request.user)
        return Response({'id': campaign.id, 'status': campaign.status, 'is_live': campaign.is_live})

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        campaign = self.get_object()
        reason = request.data.get('reason', '')
        if not reason:
            return Response({'detail': 'Reason required.'}, status=status.HTTP_400_BAD_REQUEST)
        campaign.reject(request.user, reason)
        return Response({'id': campaign.id, 'status': campaign.status, 'rejection_reason': campaign.rejection_reason})


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
