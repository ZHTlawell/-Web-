"""浏览器会话标识处理。"""

from __future__ import annotations

import uuid
from typing import Tuple

from fastapi import Request, Response


会话Cookie名称 = "runzo_session_id"
会话Cookie有效期秒数 = 60 * 60 * 24 * 30


def 获取或创建会话标识(request: Request) -> Tuple[str, bool]:
    """从 Cookie 读取会话标识，不存在时生成新的。"""
    会话标识 = request.cookies.get(会话Cookie名称)
    if 会话标识:
        return 会话标识, False
    return str(uuid.uuid4()), True


def 写入会话Cookie(response: Response, 会话标识: str) -> None:
    """把会话标识写回浏览器 Cookie。"""
    response.set_cookie(
        key=会话Cookie名称,
        value=会话标识,
        max_age=会话Cookie有效期秒数,
        httponly=True,
        samesite="lax",
    )
