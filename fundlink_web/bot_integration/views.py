from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import hmac
import hashlib
import json

INTERNAL_KEY_HEADER = 'Authorization'
from .models import NotificationLog
from donations.models import BotUser


@api_view(['POST'])
@permission_classes([AllowAny])
@csrf_exempt
def bot_notify(request):
    """
    Internal endpoint for the donation verifier to trigger Telegram notifications
    Secured by HMAC signature
    """
    # Authorization: Support new INTERNAL_API_KEY bearer OR legacy HMAC signature
    auth_header = request.headers.get(INTERNAL_KEY_HEADER, '')
    internal_key = getattr(settings, 'INTERNAL_API_KEY', '')
    authorized = False

    if internal_key and auth_header.startswith('Bearer '):
        token = auth_header.split(' ', 1)[1].strip()
        if token and hmac.compare_digest(token, internal_key):
            authorized = True

    if not authorized:
        signature = request.headers.get('X-Signature')
        if not (signature and verify_signature(request.body, signature)):
            return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)
    
    try:
        data = request.data
        telegram_id = data.get('telegram_id')
        message_type = data.get('message_type', 'donation_receipt')
        message_data = data.get('message_data', {})
        
        if not telegram_id:
            return Response({'error': 'telegram_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Log the notification attempt
        log = NotificationLog.objects.create(
            telegram_id=telegram_id,
            message_type=message_type,
            message_data=message_data,
            sent_successfully=False
        )
        
        # Here you would typically send the notification to a queue or directly to Telegram
        # For now, we'll just log it and return success
        # TODO: Implement actual Telegram notification sending
        
        log.sent_successfully = True
        log.save()
        
        return Response({
            'success': True,
            'message': 'Notification queued successfully',
            'log_id': log.id
        })
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def verify_signature(payload, signature):
    """Verify HMAC signature for internal API calls"""
    expected_signature = hmac.new(
        settings.BOT_NOTIFY_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature, expected_signature)


@api_view(['POST'])
@permission_classes([AllowAny])
@csrf_exempt
def register_user(request):
    """Idempotent bot user registration (internal)."""
    internal_key = getattr(settings, 'INTERNAL_API_KEY', '')
    auth_header = request.headers.get('Authorization', '')
    if internal_key:
        if not (auth_header.startswith('Bearer ') and hmac.compare_digest(auth_header.split(' ',1)[1], internal_key)):
            return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    data = request.data
    telegram_id = data.get('telegram_id')
    if not telegram_id:
        return Response({'error': 'telegram_id is required'}, status=status.HTTP_400_BAD_REQUEST)

    user, created = BotUser.objects.get_or_create(telegram_id=telegram_id)
    # Update mutable fields
    for field in ['username', 'first_name', 'last_name']:
        val = data.get(field)
        if val is not None:
            setattr(user, field, val)
    user.save()
    return Response({'ok': True, 'created': created})


@api_view(['POST'])
@permission_classes([AllowAny])
def webhook_telegram(request):
    """Telegram webhook endpoint"""
    import os
    import json
    import sys
    
    # Add telbot_llm to path if needed
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    telbot_llm_path = os.path.join(project_root, 'telbot_llm')
    if telbot_llm_path not in sys.path:
        sys.path.append(telbot_llm_path)
    
    try:
        from telegram import Update
        from telbot_llm.bot.main import build
        
        # Process the update
        bot_app = build()
        update = Update.de_json(request.data, bot_app.bot)
        if update:
            bot_app.process_update(update)
        return Response({'ok': True})
    except Exception as e:
        return Response({'ok': False, 'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """Health check endpoint"""
    return Response({
        'status': 'ok',
        'service': 'fundlink_backend',
        'version': '1.0.0'
    })
