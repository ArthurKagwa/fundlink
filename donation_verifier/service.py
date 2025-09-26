from __future__ import annotations

import json
import logging
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from web3 import Web3
try:
    from web3.middleware import geth_poa_middleware
except ImportError:
    # For newer web3 versions
    from web3.middleware import ExtraDataToPOAMiddleware as geth_poa_middleware

from .backend import BackendClient
from .config import VerifierSettings

TRANSFER_TOPIC = Web3.keccak(text="Transfer(address,address,uint256)").hex()
ERC20_ABI = [
    {
        'anonymous': False,
        'inputs': [
            {'indexed': True, 'internalType': 'address', 'name': 'from', 'type': 'address'},
            {'indexed': True, 'internalType': 'address', 'name': 'to', 'type': 'address'},
            {'indexed': False, 'internalType': 'uint256', 'name': 'value', 'type': 'uint256'},
        ],
        'name': 'Transfer',
        'type': 'event',
    }
]


@dataclass
class IntentRecord:
    reference: str
    wallet: str
    token: str
    value_base_units: int
    data: Dict


class DonationVerifier:
    """Polls the Avalanche Fuji chain for NGO donations and confirms them via the backend."""

    def __init__(self, settings: VerifierSettings):
        self.settings = settings
        self.logger = logging.getLogger('donation_verifier')
        self.logger.setLevel(settings.log_level)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
        if not self.logger.handlers:
            self.logger.addHandler(handler)

        self.web3 = Web3(Web3.HTTPProvider(settings.rpc_url))
        self.web3.middleware_onion.inject(geth_poa_middleware, layer=0)
        self.backend = BackendClient(settings.backend_url, settings.internal_api_key, bot_notify_secret=settings.bot_notify_secret)
        self.state_path = settings.state_path
        self.state = self._load_state()
        self.usdt_contract = None
        if settings.usdt_contract:
            checksum = Web3.to_checksum_address(settings.usdt_contract)
            self.usdt_contract = self.web3.eth.contract(address=checksum, abi=ERC20_ABI)

    # ------------------------------------------------------------------
    # State helpers
    # ------------------------------------------------------------------
    def _load_state(self) -> Dict[str, int]:
        if self.state_path.exists():
            try:
                with self.state_path.open('r', encoding='utf-8') as fh:
                    data = json.load(fh)
                return {
                    'native_block': int(data.get('native_block', 0)),
                    'usdt_block': int(data.get('usdt_block', 0)),
                }
            except Exception as exc:  # pragma: no cover - defensive
                self.logger.warning('Failed to load verifier state (%s); starting fresh', exc)
        start_block = self.settings.start_block or max(self.web3.eth.block_number - 2, 0)
        return {'native_block': start_block, 'usdt_block': start_block}

    def _save_state(self) -> None:
        tmp_path = self.state_path.with_suffix('.tmp')
        with tmp_path.open('w', encoding='utf-8') as fh:
            json.dump(self.state, fh)
        tmp_path.replace(self.state_path)

    # ------------------------------------------------------------------
    def run_forever(self) -> None:
        try:
            while True:
                try:
                    self.process_once()
                except Exception as exc:
                    self.logger.exception('Verifier iteration failed: %s', exc)
                time.sleep(self.settings.poll_interval)
        finally:
            self.backend.close()

    # ------------------------------------------------------------------
    def process_once(self) -> None:
        intents_raw = self.backend.list_intents(status='pending')
        if not intents_raw:
            self.logger.debug('No pending donation intents; advancing block markers')
            latest_block = self.web3.eth.block_number
            self.state['native_block'] = latest_block
            self.state['usdt_block'] = latest_block
            self._save_state()
            return

        lookup = self._build_intent_lookup(intents_raw)
        if not lookup:
            self.logger.debug('Pending intents present but no wallet data available')
            return

        latest_block = self.web3.eth.block_number
        self.logger.debug('Processing blocks up to %s', latest_block)

        self._process_native(lookup, latest_block)
        if self.usdt_contract is not None:
            self._process_usdt(lookup, latest_block)

        self._save_state()

    # ------------------------------------------------------------------
    def _build_intent_lookup(self, intents: Iterable[Dict]) -> Dict[Tuple[str, str, int], List[IntentRecord]]:
        bucket: Dict[Tuple[str, str, int], List[IntentRecord]] = defaultdict(list)
        for raw in intents:
            wallet = (raw.get('wallet_address') or '').lower()
            token = (raw.get('token') or '').upper()
            value = raw.get('value_base_units')
            reference = raw.get('reference')
            if not wallet or not value or not reference or token not in {'AVAX', 'USDT'}:
                continue
            try:
                value_int = int(Decimal(str(value)))
            except Exception:
                continue
            record = IntentRecord(reference=reference, wallet=wallet, token=token, value_base_units=value_int, data=raw)
            bucket[(wallet, token, value_int)].append(record)
        return bucket

    def _match_intent(self, lookup: Dict[Tuple[str, str, int], List[IntentRecord]], wallet: str, token: str, value: int) -> Optional[IntentRecord]:
        key = (wallet, token, value)
        candidates = lookup.get(key)
        if not candidates:
            return None
        record = candidates.pop(0)
        if not candidates:
            lookup.pop(key, None)
        return record

    # ------------------------------------------------------------------
    def _process_native(self, lookup: Dict[Tuple[str, str, int], List[IntentRecord]], latest_block: int) -> None:
        start_block = self.state.get('native_block', latest_block)
        start_block = min(start_block, latest_block)
        if start_block >= latest_block:
            return
        end_block = min(start_block + self.settings.block_batch_size, latest_block)

        self.logger.debug('Scanning AVAX transfers from block %s to %s', start_block + 1, end_block)

        for block_number in range(start_block + 1, end_block + 1):
            block = self.web3.eth.get_block(block_number, full_transactions=True)
            block_ts = datetime.fromtimestamp(block['timestamp'], tz=timezone.utc)
            for tx in block['transactions']:
                to_addr = tx.get('to')
                if not to_addr:
                    continue
                wallet = to_addr.lower()
                match = self._match_intent(lookup, wallet, 'AVAX', int(tx.get('value', 0)))
                if not match:
                    continue

                receipt = self.web3.eth.get_transaction_receipt(tx['hash'])
                if receipt.status != 1:
                    self.logger.info('Tx %s failed; skipping', tx['hash'].hex())
                    continue

                tx_hash_hex = tx['hash'].hex()
                payload = {
                    'tx_hash': tx_hash_hex,
                    'chain_id': self.settings.chain_id,
                    'token': 'AVAX',
                    'value_base_units': str(int(tx['value'])),
                    'from_address': tx['from'].lower(),
                    'to_address': wallet,
                    'block_number': block_number,
                    'timestamp': block_ts.isoformat(),
                    'intent_reference': match.reference,
                }
                self._confirm_with_backend(payload, match)

        self.state['native_block'] = end_block

    # ------------------------------------------------------------------
    def _process_usdt(self, lookup: Dict[Tuple[str, str, int], List[IntentRecord]], latest_block: int) -> None:
        if self.usdt_contract is None:
            return
        start_block = self.state.get('usdt_block', latest_block)
        start_block = min(start_block, latest_block)
        if start_block >= latest_block:
            return
        end_block = min(start_block + self.settings.block_batch_size, latest_block)

        self.logger.debug('Scanning USDT transfers from block %s to %s', start_block + 1, end_block)

        logs = self.web3.eth.get_logs(
            {
                'fromBlock': hex(start_block + 1),
                'toBlock': hex(end_block),
                'address': self.usdt_contract.address,
                'topics': [TRANSFER_TOPIC],
            }
        )

        for log in logs:
            event = self.usdt_contract.events.Transfer().process_log(log)
            to_addr = event['args']['to'].lower()
            value = int(event['args']['value'])
            match = self._match_intent(lookup, to_addr, 'USDT', value)
            if not match:
                continue
            block_number = log['blockNumber']
            block = self.web3.eth.get_block(block_number)
            block_ts = datetime.fromtimestamp(block['timestamp'], tz=timezone.utc)
            payload = {
                'tx_hash': log['transactionHash'].hex(),
                'chain_id': self.settings.chain_id,
                'token': 'USDT',
                'value_base_units': str(value),
                'from_address': event['args']['from'].lower(),
                'to_address': to_addr,
                'block_number': block_number,
                'timestamp': block_ts.isoformat(),
                'intent_reference': match.reference,
            }
            self._confirm_with_backend(payload, match)

        self.state['usdt_block'] = end_block

    # ------------------------------------------------------------------
    def _confirm_with_backend(self, payload: Dict, intent: IntentRecord) -> None:
        try:
            result = self.backend.confirm_donation(payload)
            donation = result.get('donation') if isinstance(result, dict) else result
            self.logger.info('Confirmed donation via intent %s for tx %s', intent.reference, payload['tx_hash'])
            
            # Send Telegram notification to donor
            if donation and isinstance(donation, dict):
                telegram_id = donation.get('donor_telegram_id')
                if telegram_id:
                    try:
                        message_data = {
                            'tx_hash': payload['tx_hash'],
                            'amount': donation.get('amount_decimal'),
                            'token': donation.get('token'),
                            'ngo_name': donation.get('ngo', {}).get('name'),
                            'explorer_url': donation.get('explorer_url')
                        }
                        notify_result = self.backend.send_notification(
                            telegram_id=telegram_id,
                            message_type='donation_receipt',
                            message_data=message_data
                        )
                        self.logger.info('Sent Telegram receipt to user %s: %s', telegram_id, notify_result.get('message'))
                    except Exception as notify_exc:
                        self.logger.error('Failed to send Telegram notification to user %s: %s', telegram_id, notify_exc)
            
            if donation:
                self.logger.debug('Donation payload: %s', donation)
        except Exception as exc:
            self.logger.error('Failed to confirm donation for tx %s: %s', payload.get('tx_hash'), exc)
