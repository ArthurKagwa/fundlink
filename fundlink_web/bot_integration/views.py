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
import requests
import os

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
        
        # Actually send the notification to Telegram
        try:
            telegram_sent = _send_telegram_notification(telegram_id, message_type, message_data)
            log.sent_successfully = telegram_sent
            log.save()
        except Exception as e:
            log.sent_successfully = False
            log.save()
            return Response({'error': f'Failed to send Telegram notification: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
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
    """Idempotent bot user registration (internal).
    Accept Authorization: Bearer <key> OR X-INTERNAL-KEY: <key>.
    This avoids conflicts with DRF JWT (which also inspects Authorization) when
    clients mistakenly send the internal key where a JWT is expected.
    """
    internal_key = getattr(settings, 'INTERNAL_API_KEY', '')
    auth_header = request.headers.get('Authorization', '')
    alt_header = request.headers.get('X-INTERNAL-KEY', '')

    print("DEBUG - register_user called")
    print(f"DEBUG - INTERNAL_API_KEY configured: {bool(internal_key)}")
    print(f"DEBUG - Bearer header present: {auth_header.startswith('Bearer ')}  Alt header present: {bool(alt_header)}")

    supplied = None
    if auth_header.startswith('Bearer '):
        supplied = auth_header.split(' ', 1)[1].strip()
    elif alt_header:
        supplied = alt_header.strip()

    if internal_key:
        if not (supplied and hmac.compare_digest(supplied, internal_key)):
            if supplied:
                print(f"DEBUG - Token mismatch prefix supplied={supplied[:6]} expected={internal_key[:6]}")
            else:
                print("DEBUG - No acceptable internal auth header supplied")
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


@api_view(['GET'])
@permission_classes([AllowAny])
def user_exists(request):
    """Lightweight existence check for a bot user.
    Query param: telegram_id=<id>
    Returns: {exists: bool}
    Always 200 for idempotent caller logic.
    """
    telegram_id = request.query_params.get('telegram_id') or request.GET.get('telegram_id')
    if not telegram_id:
        return Response({'error': 'telegram_id is required'}, status=status.HTTP_400_BAD_REQUEST)
    exists = BotUser.objects.filter(telegram_id=telegram_id).exists()
    return Response({'exists': exists})


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


def _send_telegram_notification(telegram_id: int, message_type: str, message_data: dict) -> bool:
    """Send actual notification to Telegram user"""
    try:
        # Get Telegram bot token from environment
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not bot_token:
            print(f"❌ TELEGRAM_BOT_TOKEN not configured")
            return False
            
        # Format the message based on type
        if message_type == 'donation_receipt' or message_type == 'donation_confirmed':
            amount = message_data.get('amount') or message_data.get('amount_decimal', 'Unknown')
            token = message_data.get('token', 'AVAX')
            ngo_name = message_data.get('ngo_name', 'Unknown NGO')
            tx_hash = message_data.get('tx_hash', '')
            explorer_url = message_data.get('explorer_url', '')
            
            message = f"🎉 **Donation Confirmed!**\\n\\n"
            message += f"💰 Amount: {amount} {token}\\n"
            message += f"🏢 NGO: {ngo_name}\\n"
            if tx_hash:
                short_hash = f"{tx_hash[:10]}...{tx_hash[-8:]}" if len(tx_hash) > 20 else tx_hash
                message += f"📄 Transaction: `{short_hash}`\\n"
            if explorer_url:
                message += f"🔍 [View on Snowtrace]({explorer_url})\\n"
            message += f"\\nThank you for your donation! 💝"
        else:
            message = f"📢 Notification: {message_type}\\n\\nData: {json.dumps(message_data, indent=2)}"
        
        # Send message via Telegram Bot API
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            'chat_id': telegram_id,
            'text': message,
            'parse_mode': 'Markdown',
            'disable_web_page_preview': False
        }
        
        response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('ok'):
                print(f"✅ Telegram notification sent to {telegram_id}")
                return True
            else:
                print(f"❌ Telegram API error: {result.get('description', 'Unknown error')}")
                return False
        else:
            print(f"❌ Telegram API HTTP error: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error sending Telegram notification: {e}")
        return False
