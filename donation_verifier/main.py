from __future__ import annotations

import argparse
import logging

from .config import VerifierSettings
from .service import DonationVerifier


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='FundLink donation verifier')
    parser.add_argument('--run-once', action='store_true', help='Process a single iteration and exit')
    parser.add_argument('--log-level', default=None, help='Override log level (INFO, DEBUG, etc.)')
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    settings = VerifierSettings.load()
    if args.log_level:
        settings.log_level = args.log_level.upper()

    verifier = DonationVerifier(settings)
    logging.getLogger('web3').setLevel(logging.WARNING)
    if args.run_once:
        verifier.process_once()
        verifier.backend.close()
    else:
        verifier.run_forever()


if __name__ == '__main__':  # pragma: no cover
    main()
