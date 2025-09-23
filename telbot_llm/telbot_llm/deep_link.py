from decimal import Decimal, ROUND_DOWN
from typing import Dict
import os

FUJI_CHAIN_ID = 43113
DEFAULT_USDT = os.getenv("USDT_CONTRACT_ADDRESS", "0x5425890298aed601595a70AB815c96711a31Bc65")


def make_metamask_deep_link(address: str, amount: float, token: str | None = None, decimals: int | None = None) -> Dict:
    """Generate a MetaMask deep link for AVAX or an ERC20 token on Avalanche Fuji.

    Parameters
    ----------
    address : destination EVM address (checksummed preferred)
    amount : human readable token amount
    token : ERC20 contract address; if omitted native AVAX assumed
    decimals : token decimals (required when token provided)
    """
    addr = address.strip()
    if not (addr.startswith("0x") and len(addr) == 42):
        return {"error": "invalid_address"}

    if token:
        if decimals is None:
            return {"error": "decimals_required"}
        quant = (Decimal(str(amount)) * (Decimal(10) ** decimals)).to_integral_value(rounding=ROUND_DOWN)
        link = f"https://metamask.app.link/send/{addr}?asset={token}&value={quant}&chainId={FUJI_CHAIN_ID}"
        symbol = token
    else:
        quant = (Decimal(str(amount)) * (Decimal(10) ** 18)).to_integral_value(rounding=ROUND_DOWN)
        link = f"https://metamask.app.link/send/{addr}?value={quant}&chainId={FUJI_CHAIN_ID}"
        symbol = "AVAX"

    return {
        "to": addr,
        "amount": str(amount),
        "token": symbol,
        "value_base_units": str(quant),
        "deep_link": link,
        "chain_id": FUJI_CHAIN_ID,
    }

__all__ = ["make_metamask_deep_link"]
