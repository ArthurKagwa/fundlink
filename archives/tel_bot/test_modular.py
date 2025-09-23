#!/usr/bin/env python3
"""
Test script to verify the modular bot structure works correctly.
This tests imports and basic functionality without requiring Telegram.
"""
import sys
import os
import logging

# Add the tel_bot directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_imports():
    """Test that all modules can be imported successfully."""
    print("🧪 Testing module imports...")
    
    try:
        # Test config import
        from config import BOT_TOKEN, MESSAGES, DONATION_PRESETS
        print("✅ Config module imported successfully")
        
        # Test core imports
        from core.validators import validate_amount, validate_telegram_id
        from core.exceptions import FundlinkBotError
        print("✅ Core modules imported successfully")
        
        # Test services imports  
        from services.deep_link import DeepLinkService
        from services.message_formatter import MessageFormatter
        print("✅ Services modules imported successfully")
        
        # Test that API client can be created (but don't test actual API calls)
        from services.api_client import APIClient
        api_client = APIClient()
        print("✅ API client created successfully")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_validators():
    """Test validation functions."""
    print("\n🧪 Testing validators...")
    
    try:
        from core.validators import validate_amount, validate_telegram_id, validate_ethereum_address
        
        # Test amount validation
        assert validate_amount("1.0", "AVAX") == True
        assert validate_amount("0", "AVAX") == False
        assert validate_amount("invalid", "AVAX") == False
        print("✅ Amount validation working")
        
        # Test telegram ID validation
        assert validate_telegram_id(123456789) == True
        assert validate_telegram_id(-1) == False
        assert validate_telegram_id("invalid") == False
        print("✅ Telegram ID validation working")
        
        # Test address validation
        assert validate_ethereum_address("0x742d35Cc6634C0532925a3b8D6D1f8b8cb6d75e6") == True
        assert validate_ethereum_address("invalid") == False
        print("✅ Address validation working")
        
        return True
        
    except Exception as e:
        print(f"❌ Validator test error: {e}")
        return False

def test_deep_links():
    """Test deep link generation."""
    print("\n🧪 Testing deep link generation...")
    
    try:
        from services.deep_link import DeepLinkService
        
        # Test AVAX deep link
        avax_link = DeepLinkService.generate_link(
            "0x742d35Cc6634C0532925a3b8D6D1f8b8cb6d75e6", 
            "AVAX", 
            "1.0"
        )
        assert "metamask.app.link" in avax_link
        assert "0x742d35Cc6634C0532925a3b8D6D1f8b8cb6d75e6" in avax_link
        print("✅ AVAX deep link generation working")
        
        # Test USDT deep link
        usdt_link = DeepLinkService.generate_link(
            "0x742d35Cc6634C0532925a3b8D6D1f8b8cb6d75e6", 
            "USDT", 
            "10"
        )
        assert "metamask.app.link" in usdt_link
        assert "contractAddress" in usdt_link
        print("✅ USDT deep link generation working")
        
        return True
        
    except Exception as e:
        print(f"❌ Deep link test error: {e}")
        return False

def test_message_formatting():
    """Test message formatting."""
    print("\n🧪 Testing message formatting...")
    
    try:
        from services.message_formatter import MessageFormatter
        
        # Test campaign info formatting
        campaign = {
            'title': 'Test Campaign',
            'ngo_name': 'Test NGO',
            'description': 'Test description',
            'token_options': ['AVAX', 'USDT']
        }
        
        info_text = MessageFormatter.format_campaign_info(campaign)
        assert 'Test Campaign' in info_text
        assert 'Test NGO' in info_text
        assert 'AVAX, USDT' in info_text
        print("✅ Campaign info formatting working")
        
        # Test empty donation history
        history = MessageFormatter.format_donation_history([])
        assert "haven't made any donations" in history
        print("✅ Empty donation history formatting working")
        
        # Test text truncation
        long_text = "x" * 5000
        truncated = MessageFormatter.truncate_text(long_text, 100)
        assert len(truncated) <= 100
        print("✅ Text truncation working")
        
        return True
        
    except Exception as e:
        print(f"❌ Message formatting test error: {e}")
        return False

def main():
    """Run all tests."""
    print("🚀 Starting Fundlink Bot Modular Structure Tests\n")
    
    tests = [
        test_imports,
        test_validators,
        test_deep_links,
        test_message_formatting
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()  # Add spacing between tests
    
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The modular structure is working correctly.")
        return 0
    else:
        print("❌ Some tests failed. Check the error messages above.")
        return 1

if __name__ == '__main__':
    sys.exit(main())