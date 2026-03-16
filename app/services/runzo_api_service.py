"""Runzo upstream API client."""

from __future__ import annotations

from typing import Any

import httpx


class RunzoApiService:
    """Client for simulate and settlement APIs."""

    def __init__(self, simulate_url: str, settle_url: str):
        self._simulate_url = simulate_url
        self._settle_url = settle_url
        self._client = httpx.Client(
            timeout=httpx.Timeout(180.0, connect=10.0),
            trust_env=False,
        )

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._client.close()

    def simulate_training(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Call the simulate endpoint."""
        response = self._client.post(self._simulate_url, json=payload)
        if response.status_code >= 400:
            raise RuntimeError(f"simulate 接口失败（{response.status_code}）：{response.text}")
        return response.json()

    def settle_training(self, payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
        """Call the settlement endpoint."""
        response = self._client.post(self._settle_url, json=payload, headers=headers)
        if response.status_code >= 400:
            raise RuntimeError(f"settlement 接口失败（{response.status_code}）：{response.text}")
        return response.json()
