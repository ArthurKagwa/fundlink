"""
Deep link service for generating MetaMask links.
"""
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import FUJI_CONFIG


class DeepLinkService:
    """Generate MetaMask deep links for donations."""
    
    @staticmethod
    def generate_link(to_address: str, token: str, amount: str) -> str:
        """Generate MetaMask deep link for donation."""
        if token == 'AVAX':
            # Convert AVAX to wei (18 decimals)
            amount_wei = int(float(amount) * (10 ** FUJI_CONFIG['avax_decimals']))
            return f"https://metamask.app.link/send/{to_address}?value={amount_wei}"
        elif token == 'USDT':
            # Convert USDT amount (6 decimals)
            amount_units = int(float(amount) * (10 ** FUJI_CONFIG['usdt_decimals']))
            return (
                f"https://metamask.app.link/send/{to_address}"
                f"?value={amount_units}&contractAddress={FUJI_CONFIG['usdt_contract']}"
            )
        else:
            raise ValueError(f"Unsupported token: {token}")
    
    @staticmethod
    def validate_address(address: str) -> bool:
        """Basic validation for Ethereum addresses."""
        if not address or not isinstance(address, str):
            return False
        
        # Check if it's a valid hex address (basic check)
        if not address.startswith('0x') or len(address) != 42:
            return False
        
        try:
            int(address, 16)
            return True
        except ValueError:
            return False