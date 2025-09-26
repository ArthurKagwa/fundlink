from __future__ import annotations

import os
from typing import Optional

from prometheus_client import CollectorRegistry, Counter, Histogram

_metrics_singleton = None


class _Metrics:
    def __init__(self):
        self.registry = CollectorRegistry()
        self.requests = Counter(
            "fundlink_bot_requests_total",
            "Total number of inbound Telegram text messages processed",
            registry=self.registry,
        )
        self.latency = Histogram(
            "fundlink_bot_response_latency_seconds",
            "Bot end-to-end response latency in seconds",
            registry=self.registry,
            buckets=(0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10),
        )


def get_metrics() -> Optional[_Metrics]:
    global _metrics_singleton
    if os.getenv("DISABLE_METRICS") == "1":  # opt-out
        return None
    if _metrics_singleton is None:
        _metrics_singleton = _Metrics()
    return _metrics_singleton


__all__ = ["get_metrics"]
