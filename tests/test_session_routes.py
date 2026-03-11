"""会话隔离路由测试。"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.models.runzo import Runzo任务视图, 单数据上传结果视图
from app.routes import api_routes, page_routes
from app.services.session_service import 会话Cookie名称


class 假任务管理器:
    """根据会话标识返回不同快照，便于验证路由是否隔离。"""

    def 获取当前任务视图(self, 会话标识: str) -> Runzo任务视图:
        return Runzo任务视图(任务ID=会话标识, 摘要=f"当前会话：{会话标识}")


def test_不同客户端通过_cookie_隔离任务视图(monkeypatch):
    """两个客户端应获得不同会话标识和不同任务视图。"""
    假管理器 = 假任务管理器()
    monkeypatch.setattr(page_routes, "task_manager", 假管理器)
    monkeypatch.setattr(api_routes, "task_manager", 假管理器)

    客户端甲 = TestClient(app)
    客户端乙 = TestClient(app)

    响应甲 = 客户端甲.get("/api/runzo/status")
    响应乙 = 客户端乙.get("/api/runzo/status")

    会话甲 = 客户端甲.cookies.get(会话Cookie名称)
    会话乙 = 客户端乙.cookies.get(会话Cookie名称)

    assert 响应甲.status_code == 200
    assert 响应乙.status_code == 200
    assert 会话甲
    assert 会话乙
    assert 会话甲 != 会话乙
    assert 响应甲.json()["数据"]["任务ID"] == 会话甲
    assert 响应乙.json()["数据"]["任务ID"] == 会话乙


def test_单数据上传接口可返回_htmx结果片段(monkeypatch):
    """单数据上传接口应能正常返回局部 HTML。"""
    monkeypatch.setattr(
        api_routes,
        "执行单数据上传",
        lambda 参数: 单数据上传结果视图(
            是否成功=True,
            摘要="单数据上传执行成功。",
            simulate请求体="{}",
            simulate响应体="{}",
            settlement请求体="{}",
            settlement响应体='{"ok": true}',
        ),
    )

    客户端 = TestClient(app)
    响应 = 客户端.post(
        "/api/runzo/single-upload/execute",
        headers={"HX-Request": "true"},
        data={
            "environment": "test",
            "userId": "10001",
            "authorization": "Bearer abcdefg",
            "dailyId": "daily-001",
            "trainingType": "Easy",
            "runningDistance": "5",
            "easyMinPace": "6:00",
            "easyMaxPace": "6:30",
        },
    )

    assert 响应.status_code == 200
    assert "单数据上传执行成功" in 响应.text
