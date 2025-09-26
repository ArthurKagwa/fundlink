import hmac
import logging
from datetime import timedelta, datetime
from decimal import Decimal

from django.conf import settings
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from campaigns.models import Campaign
from ngos.models import NGO

from .models import Donation, DonationIntent, BotUser
from .serializers import (
    DonationSerializer,
    DonorHistorySerializer,
    BotUserSerializer,
    DonationIntentSerializer,
)

logger = logging.getLogger(__name__)


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


def _is_internal_request(request) -> bool:
    internal_key = getattr(settings, 'INTERNAL_API_KEY', '')
    if not internal_key:
        return False
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    candidate = None
    if isinstance(auth_header, str) and auth_header.startswith('Bearer '):
        candidate = auth_header.split(' ', 1)[1].strip()
    if not candidate:
        header = request.META.get('HTTP_X_INTERNAL_KEY') or request.headers.get('X-INTERNAL-KEY') or request.headers.get('x-internal-key')
        if header:
            candidate = header.strip()
    if candidate and hmac.compare_digest(candidate, internal_key):
        return True
    return False


def _upsert_bot_user(telegram_id: int | None, *, username: str | None = None, first_name: str | None = None, last_name: str | None = None) -> BotUser | None:
    if telegram_id is None:
        return None
    bot_user, _ = BotUser.objects.get_or_create(telegram_id=telegram_id)
    updated = False
    if username is not None and bot_user.username != username:
        bot_user.username = username
        updated = True
    if first_name is not None and bot_user.first_name != first_name:
        bot_user.first_name = first_name
        updated = True
    if last_name is not None and bot_user.last_name != last_name:
        bot_user.last_name = last_name
        updated = True
    if updated:
        bot_user.save(update_fields=['username', 'first_name', 'last_name'])
    return bot_user


@api_view(['POST'])
@permission_classes([AllowAny])
def create_donation_intent(request):
    """Internal endpoint used by the Telegram bot to register an expected donation."""
    if not _is_internal_request(request):
        return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    data = request.data or {}
    campaign_id = data.get('campaign_id')
    token = (data.get('token') or '').upper()
    amount = data.get('amount_decimal')
    value_base_units = data.get('value_base_units')
    donor_telegram_id = data.get('donor_telegram_id')
    telegram_username = data.get('telegram_username')
    telegram_first_name = data.get('telegram_first_name')
    telegram_last_name = data.get('telegram_last_name')
    expires_in = data.get('expires_in_minutes', 90)

    if not campaign_id:
        return Response({'error': 'campaign_id is required'}, status=status.HTTP_400_BAD_REQUEST)
    if token not in {choice[0] for choice in Donation.TOKEN_CHOICES}:
        return Response({'error': 'token must be AVAX or USDT'}, status=status.HTTP_400_BAD_REQUEST)
    if amount is None:
        return Response({'error': 'amount_decimal is required'}, status=status.HTTP_400_BAD_REQUEST)

    campaign = get_object_or_404(Campaign, pk=campaign_id)
    ngo = campaign.ngo
    wallet_address = (ngo.wallet_address or '').lower()
    if not wallet_address:
        return Response({'error': 'NGO wallet address missing'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        amount_decimal = Decimal(str(amount))
    except Exception:
        return Response({'error': 'amount_decimal must be numeric'}, status=status.HTTP_400_BAD_REQUEST)

    token_decimals = 18 if token == 'AVAX' else 6
    
    # Calculate base value in smallest units
    if value_base_units is None:
        base_value = int((amount_decimal * (Decimal(10) ** token_decimals)).to_integral_value())
    else:
        try:
            base_value = int(Decimal(str(value_base_units)))
        except Exception:
            return Response({'error': 'value_base_units must be numeric'}, status=status.HTTP_400_BAD_REQUEST)

    # Collision detection: Check for existing intents with same (ngo_wallet, token, value) and increment if needed
    collision_count = 0
    max_attempts = 1000  # Safety limit
    
    logger.info(f"Checking for intent collisions: NGO={ngo.name}, token={token}, base_value={base_value}")
    
    while collision_count < max_attempts:
        adjusted_value = base_value + collision_count
        
        # Check if this exact combination exists in pending intents
        existing_intent = DonationIntent.objects.filter(
            ngo__wallet_address__iexact=wallet_address,
            token=token,
            value_base_units=adjusted_value,
            status='pending',
            created_at__gt=timezone.now() - timedelta(minutes=30)  # Only check recent intents
        ).first()
        
        if not existing_intent:
            # No collision found, use this value
            final_value = adjusted_value
            logger.info(f"Unique value found after {collision_count} attempts: {final_value}")
            break
        
        collision_count += 1
    
    if collision_count >= max_attempts:
        logger.error(f"Too many intent collisions for NGO {ngo.name}")
        return Response(
            {'error': 'Too many concurrent donation intents, please try again in a moment'}, 
            status=status.HTTP_429_TOO_MANY_REQUESTS
        )
    
    # Calculate final decimal amount (may be slightly different due to collision avoidance)
    final_amount_decimal = Decimal(final_value) / (Decimal(10) ** token_decimals)
    quant = final_value

    bot_user = None
    donor_id_int = None
    if donor_telegram_id is not None:
        try:
            donor_id_int = int(donor_telegram_id)
        except (TypeError, ValueError):
            return Response({'error': 'donor_telegram_id must be an integer'}, status=status.HTTP_400_BAD_REQUEST)
        bot_user = _upsert_bot_user(
            donor_id_int,
            username=telegram_username,
            first_name=telegram_first_name,
            last_name=telegram_last_name,
        )

    try:
        expires_delta = timedelta(minutes=int(expires_in)) if expires_in is not None else timedelta(minutes=90)
    except Exception:
        expires_delta = timedelta(minutes=90)

    intent = DonationIntent.objects.create(
        ngo=ngo,
        campaign=campaign,
        token=token,
        token_decimals=token_decimals,
        amount_decimal=final_amount_decimal,
        value_base_units=quant,
        wallet_address=wallet_address,
        donor_telegram_id=donor_id_int,
        bot_user=bot_user,
        expires_at=timezone.now() + expires_delta,
    )

    serializer = DonationIntentSerializer(intent)
    return Response({
        'reference': intent.reference,
        'expires_at': intent.expires_at.isoformat() if intent.expires_at else None,
        'amount_decimal': str(final_amount_decimal),
        'value_base_units': str(quant),
        'original_amount': str(amount_decimal),
        'adjusted_for_uniqueness': collision_count > 0,
        'intent': serializer.data,
    }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([AllowAny])
def list_donation_intents(request):
    if not _is_internal_request(request):
        return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    status_filter = request.query_params.get('status', DonationIntent.STATUS_PENDING)
    wallet = (request.query_params.get('wallet_address') or '').lower()
    token = request.query_params.get('token')

    intents = DonationIntent.objects.all()
    if status_filter:
        intents = intents.filter(status=status_filter)
    if wallet:
        intents = intents.filter(wallet_address=wallet)
    if token:
        intents = intents.filter(token=token.upper())

    serializer = DonationIntentSerializer(intents.order_by('-created_at')[:200], many=True)
    return Response({'results': serializer.data})


@api_view(['POST'])
@permission_classes([AllowAny])
def confirm_donation(request):
    if not _is_internal_request(request):
        return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    data = request.data or {}
    tx_hash = (data.get('tx_hash') or '').lower()
    chain_id = data.get('chain_id', 43113)
    token = (data.get('token') or '').upper()
    value_units = data.get('value_base_units')
    wallet_address = (data.get('to_address') or data.get('wallet_address') or '').lower()
    from_address = (data.get('from_address') or '').lower()
    block_number = data.get('block_number')
    timestamp_raw = data.get('timestamp')
    intent_reference = data.get('intent_reference')

    if not tx_hash:
        return Response({'error': 'tx_hash is required'}, status=status.HTTP_400_BAD_REQUEST)
    if token not in {choice[0] for choice in Donation.TOKEN_CHOICES}:
        return Response({'error': 'token must be AVAX or USDT'}, status=status.HTTP_400_BAD_REQUEST)
    if value_units is None:
        return Response({'error': 'value_base_units is required'}, status=status.HTTP_400_BAD_REQUEST)
    if not wallet_address:
        return Response({'error': 'to_address is required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        value_base_units = Decimal(str(value_units))
    except Exception:
        return Response({'error': 'value_base_units must be numeric'}, status=status.HTTP_400_BAD_REQUEST)

    ngo = get_object_or_404(NGO, wallet_address=wallet_address)

    intent = None
    queryset = DonationIntent.objects.select_related('campaign', 'ngo', 'bot_user').filter(wallet_address=wallet_address)
    if intent_reference:
        intent = queryset.filter(reference=intent_reference).first()
    else:
        intent = queryset.filter(status=DonationIntent.STATUS_PENDING, token=token, value_base_units=value_base_units).order_by('created_at').first()

    if not intent:
        return Response({'error': 'Matching donation intent not found'}, status=status.HTTP_404_NOT_FOUND)

    existing = Donation.objects.filter(tx_hash=tx_hash).first()
    if intent.status != DonationIntent.STATUS_PENDING:
        if existing:
            serializer = DonationSerializer(existing)
            return Response({'donation': serializer.data}, status=status.HTTP_200_OK)
        return Response({'error': 'Intent already fulfilled'}, status=status.HTTP_409_CONFLICT)

    token_decimals = intent.token_decimals or (18 if token == 'AVAX' else 6)
    amount_decimal = Decimal(value_base_units) / (Decimal(10) ** token_decimals)

    if existing:
        if not existing.intent:
            existing.intent = intent
            existing.save(update_fields=['intent'])
        intent.mark_fulfilled()
        serializer = DonationSerializer(existing)
        return Response({'donation': serializer.data})

    tx_time = None
    if timestamp_raw:
        try:
            if isinstance(timestamp_raw, (int, float, Decimal)):
                tx_time = datetime.fromtimestamp(float(timestamp_raw), tz=timezone.utc)
            else:
                tx_time = datetime.fromisoformat(str(timestamp_raw).replace('Z', '+00:00'))
        except Exception:
            tx_time = timezone.now()

    donor_telegram_id = intent.donor_telegram_id
    bot_user = intent.bot_user
    if bot_user is None:
        bot_user = _upsert_bot_user(donor_telegram_id)

    donation = Donation.objects.create(
        ngo=intent.ngo,
        campaign=intent.campaign,
        token=token,
        amount_decimal=amount_decimal.quantize(Decimal('0.000001')),
        value_base_units=value_base_units,
        tx_hash=tx_hash,
        chain_id=chain_id,
        sender_address=from_address,
        recipient_address=wallet_address,
        block_number=block_number,
        tx_timestamp=tx_time,
        donor_telegram_id=donor_telegram_id,
        confirmed_at=timezone.now(),
        bot_user=bot_user,
        intent=intent,
    )

    intent.mark_fulfilled()

    serializer = DonationSerializer(donation)
    return Response({'donation': serializer.data}, status=status.HTTP_201_CREATED)
