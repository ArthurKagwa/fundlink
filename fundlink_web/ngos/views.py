from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from django.contrib.auth.models import User
from django.db import transaction
from .models import NGO
from .serializers import (
    NGOSerializer, NGOApplicationSerializer, NGOPublicSerializer, NGOApprovalSerializer, NGODashboardSerializer
)


class NGOViewSet(viewsets.ModelViewSet):
    queryset = NGO.objects.all()
    serializer_class = NGOSerializer
    
    def get_permissions(self):
        if self.action == 'apply':
            return [AllowAny()]
        if self.action in ['approve', 'reject', 'list_pending']:
            return [IsAdminUser()]
        return [IsAuthenticated()]
    
    def get_queryset(self):
        if self.action == 'list':
            # Only return approved NGOs for public list
            return NGO.objects.filter(status=NGO.STATUS_APPROVED)
        if self.action == 'list_pending':
            return NGO.objects.filter(status__in=[NGO.STATUS_SUBMITTED, NGO.STATUS_REJECTED])
        return super().get_queryset()
    
    def get_serializer_class(self):
        if self.action == 'apply':
            return NGOApplicationSerializer
        if self.action == 'list':
            return NGOPublicSerializer
        if self.action in ['approve', 'reject']:
            return NGOApprovalSerializer
        return super().get_serializer_class()
    
    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def apply(self, request):
        """NGO application endpoint"""
        serializer = NGOApplicationSerializer(data=request.data)
        if serializer.is_valid():
            # Create NGO record (not approved by default)
            ngo = serializer.save()
            return Response({
                'message': 'Application submitted successfully. Awaiting admin approval.',
                'ngo_id': ngo.id,
                'status': ngo.status
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        ngo = self.get_object()
        with transaction.atomic():
            ngo.approve(request.user)
            # Ensure a user exists
            if not ngo.user:
                temp_password = User.objects.make_random_password()
                user = User.objects.create_user(username=ngo.email, email=ngo.email, password=temp_password)
                ngo.user = user
                ngo.save()
        return Response(NGOApprovalSerializer(ngo).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        ngo = self.get_object()
        reason = request.data.get('reason', '')
        if not reason:
            return Response({'detail': 'Reason is required.'}, status=status.HTTP_400_BAD_REQUEST)
        ngo.reject(request.user, reason)
        return Response(NGOApprovalSerializer(ngo).data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def list_pending(self, request):
        qs = self.get_queryset()
        serializer = NGOSerializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def dashboard(self, request, pk=None):
        """Get comprehensive dashboard data for an NGO"""
        ngo = self.get_object()
        
        # Check if user has permission to view this NGO's dashboard
        if not request.user.is_staff and (
            not hasattr(request.user, 'ngo') or request.user.ngo != ngo
        ):
            return Response({'detail': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = NGODashboardSerializer(ngo)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def public_stats(self, request):
        """Get aggregated statistics for all approved NGOs (public endpoint)"""
        approved_ngos = NGO.objects.filter(status=NGO.STATUS_APPROVED)
        
        total_ngos = approved_ngos.count()
        total_campaigns = sum(ngo.total_campaigns for ngo in approved_ngos)
        active_campaigns = sum(ngo.active_campaigns for ngo in approved_ngos)
        total_raised = sum(ngo.total_donations_received for ngo in approved_ngos)
        total_donors = sum(ngo.total_donors for ngo in approved_ngos)
        
        # Get featured NGOs with their performance
        featured_ngos = []
        for ngo in approved_ngos.order_by('-created_at')[:5]:
            featured_ngos.append({
                'id': ngo.id,
                'name': ngo.name,
                'total_campaigns': ngo.total_campaigns,
                'total_raised': float(ngo.total_donations_received),
                'active_campaigns': ngo.active_campaigns,
            })
        
        return Response({
            'overview': {
                'total_ngos': total_ngos,
                'total_campaigns': total_campaigns,
                'active_campaigns': active_campaigns,
                'total_raised': float(total_raised),
                'total_donors': total_donors,
            },
            'featured_ngos': featured_ngos
        })
