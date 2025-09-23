"""
Validation utilities for Fundlink Telegram Bot.
"""
import re
from typing import Union


def validate_amount(amount_str: str, token: str) -> bool:
    """Validate donation amount."""
    try:
        amount = float(amount_str)
        
        # Check if amount is positive
        if amount <= 0:
            return False
        
        # Check token-specific limits (reasonable maximums for testnet)
        if token == 'AVAX' and amount > 100:  # Max 100 AVAX
            return False
        elif token == 'USDT' and amount > 10000:  # Max 10k USDT
            return False
        
        # Check minimum amounts
        if token == 'AVAX' and amount < 0.001:  # Min 0.001 AVAX
            return False
        elif token == 'USDT' and amount < 0.01:  # Min 0.01 USDT
            return False
        
        return True
        
    except (ValueError, TypeError):
        return False


def validate_telegram_id(telegram_id: Union[int, str]) -> bool:
    """Validate Telegram user ID."""
    try:
        if isinstance(telegram_id, str):
            telegram_id = int(telegram_id)
        
        # Telegram user IDs are positive integers
        if not isinstance(telegram_id, int) or telegram_id <= 0:
            return False
        
        # Telegram user IDs are typically large numbers
        if telegram_id < 1000:  # Basic sanity check
            return False
        
        return True
        
    except (ValueError, TypeError):
        return False


def validate_ethereum_address(address: str) -> bool:
    """Validate Ethereum address format."""
    if not address or not isinstance(address, str):
        return False
    
    # Check if it's a valid hex address
    if not address.startswith('0x') or len(address) != 42:
        return False
    
    # Check if it contains only hex characters
    hex_pattern = re.compile(r'^0x[a-fA-F0-9]{40}$')
    return bool(hex_pattern.match(address))


def validate_token(token: str) -> bool:
    """Validate supported token."""
    supported_tokens = ['AVAX', 'USDT']
    return token in supported_tokens


def validate_campaign_id(campaign_id: Union[int, str]) -> bool:
    """Validate campaign ID."""
    try:
        if isinstance(campaign_id, str):
            campaign_id = int(campaign_id)
        
        return isinstance(campaign_id, int) and campaign_id > 0
        
    except (ValueError, TypeError):
        return False