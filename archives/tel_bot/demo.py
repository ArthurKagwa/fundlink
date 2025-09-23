#!/usr/bin/env python3
"""
Demo script showing the modular Fundlink bot capabilities.
This demonstrates the key features without requiring a full Telegram setup.
"""
import sys
import os
import asyncio

# Add the tel_bot directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services import APIClient, MessageFormatter, DeepLinkService
from core.validators import validate_amount, validate_ethereum_address
from config import DONATION_PRESETS, MESSAGES

def demo_validation():
    """Demonstrate validation capabilities."""
    print("🔍 Validation Demo")
    print("=" * 50)
    
    # Test different amounts
    test_amounts = [
        ("1.0", "AVAX", "✅"),
        ("0", "AVAX", "❌"),
        ("invalid", "AVAX", "❌"),
        ("10", "USDT", "✅"),
        ("1000000", "USDT", "❌")  # Too large
    ]
    
    for amount, token, expected in test_amounts:
        result = "✅" if validate_amount(amount, token) else "❌"
        status = "PASS" if result == expected else "FAIL"
        print(f"  {amount} {token}: {result} ({status})")
    
    # Test address validation
    addresses = [
        ("0x742d35Cc6634C0532925a3b8D6D1f8b8cb6d75e6", "✅"),
        ("invalid", "❌"),
        ("0x123", "❌")  # Too short
    ]
    
    print("\n  Address Validation:")
    for address, expected in addresses:
        result = "✅" if validate_ethereum_address(address) else "❌" 
        status = "PASS" if result == expected else "FAIL"
        print(f"  {address[:20]}...: {result} ({status})")

def demo_deep_links():
    """Demonstrate deep link generation."""
    print("\n🔗 Deep Link Generation Demo")
    print("=" * 50)
    
    ngo_address = "0x742d35Cc6634C0532925a3b8D6D1f8b8cb6d75e6"
    
    # Generate AVAX link
    avax_link = DeepLinkService.generate_link(ngo_address, "AVAX", "1.0")
    print(f"AVAX Link (1.0): {avax_link}")
    
    # Generate USDT link
    usdt_link = DeepLinkService.generate_link(ngo_address, "USDT", "10")
    print(f"USDT Link (10): {usdt_link}")

def demo_message_formatting():
    """Demonstrate message formatting."""
    print("\n📄 Message Formatting Demo")
    print("=" * 50)
    
    # Mock campaign data
    campaign = {
        'title': 'Hurricane Relief Fund',
        'ngo_name': 'Red Cross International',
        'description': 'Emergency relief for hurricane victims in the Caribbean region.',
        'token_options': ['AVAX', 'USDT'],
        'goal_amount': '10000'
    }
    
    formatted = MessageFormatter.format_campaign_info(campaign)
    print("Campaign Info:")
    print(formatted)
    
    # Mock donation history
    donations = [
        {
            'amount': '1.5',
            'token': 'AVAX',
            'campaign_title': 'Hurricane Relief Fund',
            'ngo_name': 'Red Cross International',
            'tx_hash': '0xabcd1234567890abcdef1234567890abcdef1234567890abcdef1234567890ab',
            'confirmed_at': '2024-01-15T10:30:00Z',
            'created_at': '2024-01-15T10:25:00Z'
        }
    ]
    
    history = MessageFormatter.format_donation_history(donations)
    print("\nDonation History:")
    print(history)

def demo_config():
    """Demonstrate configuration."""
    print("\n⚙️  Configuration Demo")
    print("=" * 50)
    
    print("Donation Presets:")
    for token, amounts in DONATION_PRESETS.items():
        print(f"  {token}: {', '.join(amounts)}")
    
    print(f"\nWelcome Message Preview:")
    welcome = MESSAGES['welcome'].format(name="Alice")
    print(f"  {welcome[:100]}...")

async def demo_api_client():
    """Demonstrate API client (without actual API calls)."""
    print("\n🌐 API Client Demo")
    print("=" * 50)
    
    client = APIClient()
    print(f"API Base URL: {client.base_url}")
    print(f"Headers configured: {'Authorization' in client.headers}")
    print(f"Timeout: {client.timeout}s")
    
    # Note: We don't make actual API calls in this demo
    print("✅ API client initialized successfully")

def main():
    """Run all demos."""
    print("🚀 Fundlink Bot Modular Architecture Demo")
    print("=" * 60)
    print("This demo showcases the modular bot's key capabilities")
    print("without requiring a full Telegram or backend setup.\n")
    
    # Run synchronous demos
    demo_validation()
    demo_deep_links()
    demo_message_formatting()
    demo_config()
    
    # Run async demo
    asyncio.run(demo_api_client())
    
    print("\n🎉 Demo completed! The modular structure provides:")
    print("  • Clean separation of concerns")
    print("  • Robust validation and error handling")
    print("  • Easy testing and maintenance")
    print("  • Scalable architecture for future features")
    print("\n💡 Ready for MVP deployment!")

if __name__ == '__main__':
    main()