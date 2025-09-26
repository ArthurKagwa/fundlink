"""Auth helpers for internal service communication."""

from __future__ import annotations

from typing import Dict, Optional


def internal_headers(api_key: Optional[str]) -> Dict[str, str]:
    if not api_key:
        return {}
    return {
        "Authorization": f"Bearer {api_key}",
        "X-INTERNAL-KEY": api_key,
    }


__all__ = ["internal_headers"]
