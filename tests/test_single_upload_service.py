"""Single upload service tests."""

from app.services.single_upload_service import build_settlement_payload


def test_build_settlement_payload_overrides_daily_and_user_id():
    """Settlement payload should override daily, dailyId and userId."""
    simulate_response = {
        "daily": "old-daily",
        "userId": "old-user",
        "plan": {"ok": True},
    }

    settlement_payload = build_settlement_payload(simulate_response, "new-user", "daily-001")

    assert settlement_payload["daily"] == "daily-001"
    assert settlement_payload["dailyId"] == "daily-001"
    assert settlement_payload["userId"] == "new-user"
    assert settlement_payload["plan"] == {"ok": True}
