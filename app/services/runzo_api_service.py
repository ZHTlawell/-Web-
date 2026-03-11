"""Runzo 外部接口调用服务。"""

from __future__ import annotations

from typing import Any, Dict

import httpx


class Runzo接口服务:
    """负责调用 simulate 和 settlement 外部接口。"""

    def __init__(self, simulate_url: str, settle_url: str):
        self._simulate_url = simulate_url
        self._settle_url = settle_url
        self._client = httpx.Client(
            timeout=httpx.Timeout(180.0, connect=10.0),
            trust_env=False,
        )

    def 关闭(self) -> None:
        """关闭底层 HTTP 客户端。"""
        self._client.close()

    def 模拟训练(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """调用 simulate 接口。"""
        response = self._client.post(self._simulate_url, json=payload)
        if response.status_code >= 400:
            raise RuntimeError(f"simulate 接口失败（{response.status_code}）：{response.text}")
        return response.json()

    def 结算训练(self, payload: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
        """调用 settlement 接口。"""
        response = self._client.post(self._settle_url, json=payload, headers=headers)
        if response.status_code >= 400:
            raise RuntimeError(f"settlement 接口失败（{response.status_code}）：{response.text}")
        return response.json()
