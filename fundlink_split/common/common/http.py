"""HTTP helper utilities shared by FundLink services."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Mapping, MutableMapping, Optional

import httpx


@dataclass(slots=True)
class ServiceClientConfig:
    base_url: str
    api_key: Optional[str] = None
    timeout: float = 20.0
    default_headers: Optional[Mapping[str, str]] = None

    def build_headers(self) -> Dict[str, str]:
        headers: Dict[str, str] = {}
        if self.default_headers:
            headers.update(self.default_headers)
        if self.api_key:
            headers.setdefault("Authorization", f"Bearer {self.api_key}")
            headers.setdefault("X-INTERNAL-KEY", self.api_key)
        return headers


class ServiceClient:
    """Thin async HTTP wrapper with structured error reporting."""

    def __init__(self, config: ServiceClientConfig):
        self.config = config
        self._client = httpx.AsyncClient(base_url=config.base_url, timeout=config.timeout)

    async def request(
        self,
        method: str,
        url: str,
        *,
        params: Optional[Mapping[str, Any]] = None,
        json_body: Optional[Mapping[str, Any]] = None,
        headers: Optional[Mapping[str, str]] = None,
    ) -> Any:
        merged_headers: MutableMapping[str, str] = self.config.build_headers()
        if headers:
            merged_headers.update(headers)

        response = await self._client.request(
            method,
            url,
            params=params,
            json=json_body,
            headers=merged_headers,
        )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:  # pragma: no cover - simple bubble
            raise

        if "application/json" in response.headers.get("content-type", ""):
            return response.json()
        return response.text

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "ServiceClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()


async def get_json(client: ServiceClient, path: str, params: Optional[Mapping[str, Any]] = None) -> Any:
    return await client.request("GET", path, params=params)


async def post_json(
    client: ServiceClient,
    path: str,
    payload: Mapping[str, Any],
    headers: Optional[Mapping[str, str]] = None,
) -> Any:
    return await client.request("POST", path, json_body=payload, headers=headers)


__all__ = ["ServiceClient", "ServiceClientConfig", "get_json", "post_json"]
