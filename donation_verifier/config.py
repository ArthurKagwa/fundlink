from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

try:  # optional dependency; fallback to no-op if unavailable
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - safe fallback
    def load_dotenv(path):  # type: ignore
        return False


@dataclass(slots=True)
class VerifierSettings:
    rpc_url: str
    backend_url: str
    internal_api_key: str
    chain_id: int = 43113
    usdt_contract: Optional[str] = None
    poll_interval: int = 15
    block_batch_size: int = 50
    state_path: Path = Path("donation_verifier_state.json")
    start_block: Optional[int] = None
    log_level: str = "INFO"
    bot_notify_secret: Optional[str] = None

    @classmethod
    def load(cls) -> "VerifierSettings":
        root_env = Path(__file__).resolve().parents[1] / '.env'
        if root_env.exists():
            load_dotenv(root_env)

        rpc_url = os.getenv('AVALANCHE_RPC_URL') or os.getenv('FUJI_RPC_URL') or os.getenv('RPC_URL')
        backend_url = os.getenv('BACKEND_URL', 'http://localhost:8000')
        internal_api_key = os.getenv('INTERNAL_API_KEY', '')
        chain_id = int(os.getenv('CHAIN_ID', 43113))
        usdt_contract = os.getenv('USDT_CONTRACT_ADDRESS')
        poll_interval = int(os.getenv('VERIFIER_POLL_INTERVAL', 15))
        block_batch_size = int(os.getenv('VERIFIER_BLOCK_BATCH', 50))
        state_path = Path(os.getenv('VERIFIER_STATE_PATH', 'donation_verifier_state.json'))
        start_block_raw = os.getenv('VERIFIER_START_BLOCK')
        start_block = int(start_block_raw) if start_block_raw else None
        log_level = os.getenv('VERIFIER_LOG_LEVEL', 'INFO')
        bot_notify_secret = os.getenv('BOT_NOTIFY_SECRET', '')

        if not rpc_url:
            raise RuntimeError('AVALANCHE_RPC_URL (or FUJI_RPC_URL/RPC_URL) must be set for the donation verifier')
        if not internal_api_key:
            raise RuntimeError('INTERNAL_API_KEY must be configured for verifier backend calls')

        return cls(
            rpc_url=rpc_url,
            backend_url=backend_url,
            internal_api_key=internal_api_key,
            chain_id=chain_id,
            usdt_contract=usdt_contract,
            poll_interval=poll_interval,
            block_batch_size=block_batch_size,
            state_path=state_path,
            start_block=start_block,
            log_level=log_level,
            bot_notify_secret=bot_notify_secret,
        )
