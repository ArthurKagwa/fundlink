from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.shortcuts import get_object_or_404
from .models import Donation, BotUser
from .serializers import DonationSerializer, DonorHistorySerializer, BotUserSerializer


class DonationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DonationSerializer
    permission_classes = [AllowAny]  # Public read access for donor history
    
    def get_queryset(self):
        queryset = Donation.objects.filter(confirmed_at__isnull=False)  # Only confirmed donations
        
        # Filter by telegram_id if provided (for donor history)
        telegram_id = self.request.query_params.get('telegram_id')
        if telegram_id:
            queryset = queryset.filter(donor_telegram_id=telegram_id)
        
        # Filter by NGO if provided
        ngo_id = self.request.query_params.get('ngo_id')
        if ngo_id:
            queryset = queryset.filter(ngo_id=ngo_id)
        
        return queryset.order_by('-created_at')
    
    def get_serializer_class(self):
        telegram_id = self.request.query_params.get('telegram_id')
        if telegram_id:
            # Use simplified serializer for donor history
            return DonorHistorySerializer
        return super().get_serializer_class()


@api_view(['GET'])
@permission_classes([AllowAny])
def donor_history(request):
    """Get donation history for a specific Telegram user"""
    telegram_id = request.query_params.get('telegram_id')
    if not telegram_id:
        return Response({'error': 'telegram_id parameter is required'}, 
                       status=status.HTTP_400_BAD_REQUEST)
    
    donations = Donation.objects.filter(
        donor_telegram_id=telegram_id,
        confirmed_at__isnull=False
    ).order_by('-created_at')
    
    serializer = DonorHistorySerializer(donations, many=True)
    return Response({
        'donations': serializer.data,
        'total_donations': donations.count(),
        'total_amount_avax': sum(d.amount_decimal for d in donations if d.token == 'AVAX'),
        'total_amount_usdt': sum(d.amount_decimal for d in donations if d.token == 'USDT'),
    })
