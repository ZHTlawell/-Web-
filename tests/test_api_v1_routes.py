"""v1 JSON API route tests."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.models.runzo import SingleUploadApiData, SingleUploadDebugInfo
from app.routes import api_v1_routes


def _build_request_payload(include_debug: bool = False) -> dict[str, object]:
    """Build one valid JSON payload for the v1 single-upload API."""
    return {
        "environment": "test",
        "userId": "10001",
        "dailyId": "daily-001",
        "trainingType": "Threshold",
        "runningDistance": 8,
        "stateDescription": "今天有点累",
        "weekIndex": 1,
        "dayStartTime": 1773676800000,
        "includeDebug": include_debug,
        "userData": {
            "gender": "male",
            "age": 22,
            "weight": 75,
            "height": 175,
            "hrMax": 198,
            "hrRest": 65,
            "targetDistance": 5,
            "intensityPreference": "medium",
        },
        "trainingBlocks": [
            {"minPace": "6:00", "maxPace": "6:30", "distance": 2},
            {"minPace": "4:30", "maxPace": "4:45", "distance": 4},
        ],
    }


def test_v1_single_upload_execute_returns_success_json(monkeypatch):
    """v1 single-upload API should return the unified JSON envelope."""
    monkeypatch.setattr(
        api_v1_routes,
        "execute_single_upload_api",
        lambda params, include_debug: SingleUploadApiData(
            success=True,
            executionStatus="success",
            summary="单数据上传执行成功。",
            environment="test",
            debugInfo=SingleUploadDebugInfo(
                simulateRequest={"ok": True},
                simulateResponse={"simulate": True},
                settlementRequest={"dailyId": "daily-001"},
                settlementResponse={"settled": True},
            )
            if include_debug
            else None,
        ),
    )

    client = TestClient(app)
    response = client.post(
        "/api/runzo/v1/single-upload/execute",
        headers={
            "Authorization": "Bearer abcdefg",
            "ts-app-version": "2.6.0",
        },
        json=_build_request_payload(include_debug=True),
    )

    assert response.status_code == 200
    assert response.json()["code"] == 0
    assert response.json()["message"] == "success"
    assert response.json()["data"]["executionStatus"] == "success"
    assert response.json()["data"]["debugInfo"]["simulateRequest"] == {"ok": True}


def test_v1_single_upload_execute_requires_authorization_header():
    """v1 single-upload API should reject missing Authorization headers."""
    client = TestClient(app)
    response = client.post(
        "/api/runzo/v1/single-upload/execute",
        headers={"ts-app-version": "2.6.0"},
        json=_build_request_payload(),
    )

    assert response.status_code == 400
    assert response.json()["code"] == 4001
    assert "Authorization" in response.json()["message"]


def test_v1_single_upload_execute_returns_business_failure(monkeypatch):
    """Business execution failures should return code 4002 with JSON data."""
    monkeypatch.setattr(
        api_v1_routes,
        "execute_single_upload_api",
        lambda params, include_debug: SingleUploadApiData(
            success=False,
            executionStatus="failed",
            summary="单数据上传执行失败。",
            environment="preprod",
            errorMessage="simulate 接口失败（500）：boom",
        ),
    )

    client = TestClient(app)
    response = client.post(
        "/api/runzo/v1/single-upload/execute",
        headers={
            "Authorization": "Bearer abcdefg",
            "ts-app-version": "2.6.0",
        },
        json=_build_request_payload(),
    )

    assert response.status_code == 400
    assert response.json()["code"] == 4002
    assert response.json()["message"] == "execution failed"
    assert response.json()["data"]["executionStatus"] == "failed"
