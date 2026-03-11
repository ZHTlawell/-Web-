"""单数据上传服务测试。"""

from app.services.single_upload_service import _构建结算请求体


def test_构建结算请求体_会覆盖_daily和userId():
    """settlement 请求体应使用页面输入覆盖 daily、dailyId 和 userId。"""
    simulate响应体 = {
        "daily": "old-daily",
        "userId": "old-user",
        "plan": {"ok": True},
    }

    settlement请求体 = _构建结算请求体(simulate响应体, "new-user", "daily-001")

    assert settlement请求体["daily"] == "daily-001"
    assert settlement请求体["dailyId"] == "daily-001"
    assert settlement请求体["userId"] == "new-user"
    assert settlement请求体["plan"] == {"ok": True}
