"""Single-upload execution service."""

from __future__ import annotations

import json
from typing import Any

from app.models.runzo import SingleUploadParams, SingleUploadResultView
from app.services.payload_builder_service import build_simulate_payload
from app.services.runzo_api_service import RunzoApiService
from app.services.settings import get_environment_connection_config, get_settings
from app.services.validation_service import build_single_upload_headers


def execute_single_upload(params: SingleUploadParams) -> SingleUploadResultView:
    """Execute one complete simulate -> settlement flow."""
    settings = get_settings()
    env_config = get_environment_connection_config(params.environment)
    simulate_request = build_simulate_payload(params.daily_payload, params.user_data)
    simulate_request["stateDescription"] = params.state_description

    result = SingleUploadResultView(
        environment=params.environment,
        execution_status="执行中",
        simulate_request=json.dumps(simulate_request, ensure_ascii=False, indent=2),
    )

    headers = build_single_upload_headers(
        params=params,
        default_lang=settings.default_lang,
        default_time_zone=settings.default_time_zone,
        default_country=settings.default_country,
    )

    api_service = RunzoApiService(simulate_url=settings.simulate_url, settle_url=env_config.settle_url)
    try:
        simulate_response = api_service.simulate_training(simulate_request)
        settlement_request = build_settlement_payload(simulate_response, params.user_id, params.daily_id)
        settlement_response = api_service.settle_training(settlement_request, headers)

        result.success = True
        result.execution_status = "执行成功"
        result.summary = "单数据上传执行成功。"
        result.simulate_response = json.dumps(simulate_response, ensure_ascii=False, indent=2)
        result.settlement_request = json.dumps(settlement_request, ensure_ascii=False, indent=2)
        result.settlement_response = json.dumps(settlement_response, ensure_ascii=False, indent=2)
        return result
    except Exception as exc:  # noqa: BLE001
        result.success = False
        result.execution_status = "执行失败"
        result.summary = "单数据上传执行失败。"
        result.error_message = str(exc)
        return result
    finally:
        api_service.close()


def build_settlement_payload(simulate_response: dict[str, Any], user_id: str, daily_id: str) -> dict[str, Any]:
    """Build settlement payload based on the simulate response."""
    settlement_payload = dict(simulate_response)
    settlement_payload["daily"] = daily_id
    settlement_payload["dailyId"] = daily_id
    settlement_payload["userId"] = user_id
    return settlement_payload
