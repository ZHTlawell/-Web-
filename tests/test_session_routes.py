"""Session-isolated route tests."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.models.runzo import SingleUploadResultView, TaskView
from app.routes import api_routes, page_routes
from app.services.session_service import SESSION_COOKIE_NAME


class FakeTaskManager:
    """Return different snapshots per session id for route isolation tests."""

    def get_current_task_view(self, session_id: str) -> TaskView:
        return TaskView(task_id=session_id, summary=f"当前会话：{session_id}")


def test_clients_are_isolated_by_cookie(monkeypatch):
    """Two clients should receive different session ids and task views."""
    fake_manager = FakeTaskManager()
    monkeypatch.setattr(page_routes, "task_manager", fake_manager)
    monkeypatch.setattr(api_routes, "task_manager", fake_manager)

    client_a = TestClient(app)
    client_b = TestClient(app)

    response_a = client_a.get("/api/runzo/status")
    response_b = client_b.get("/api/runzo/status")

    session_a = client_a.cookies.get(SESSION_COOKIE_NAME)
    session_b = client_b.cookies.get(SESSION_COOKIE_NAME)

    assert response_a.status_code == 200
    assert response_b.status_code == 200
    assert session_a
    assert session_b
    assert session_a != session_b
    assert response_a.json()["data"]["task_id"] == session_a
    assert response_b.json()["data"]["task_id"] == session_b


def test_single_upload_endpoint_can_return_htmx_fragment(monkeypatch):
    """Single upload endpoint should return partial HTML for HTMX."""
    monkeypatch.setattr(
        api_routes,
        "execute_single_upload",
        lambda params: SingleUploadResultView(
            success=True,
            summary="单数据上传执行成功。",
            simulate_request="{}",
            simulate_response="{}",
            settlement_request="{}",
            settlement_response='{"ok": true}',
        ),
    )

    client = TestClient(app)
    response = client.post(
        "/api/runzo/single-upload/execute",
        headers={"HX-Request": "true"},
        data={
            "environment": "test",
            "userId": "10001",
            "authorization": "Bearer abcdefg",
            "tsAppVersion": "2.6.0",
            "dailyId": "daily-001",
            "trainingType": "Easy",
            "runningDistance": "5",
            "easyMinPace": "6:00",
            "easyMaxPace": "6:30",
        },
    )

    assert response.status_code == 200
    assert "单数据上传执行成功" in response.text
