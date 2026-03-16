"""Single-upload execution service."""

from __future__ import annotations

import json
from typing import Any

from app.models.runzo import (
    SingleUploadApiData,
    SingleUploadDebugInfo,
    SingleUploadExecutionArtifacts,
    SingleUploadParams,
    SingleUploadResultView,
)
from app.services.payload_builder_service import build_simulate_payload
from app.services.runzo_api_service import RunzoApiService
from app.services.settings import get_environment_connection_config, get_settings
from app.services.validation_service import build_single_upload_headers


def execute_single_upload_artifacts(params: SingleUploadParams) -> SingleUploadExecutionArtifacts:
    """Execute one complete simulate -> settlement flow and keep structured artifacts."""
    settings = get_settings()
    env_config = get_environment_connection_config(params.environment)
    simulate_request = build_simulate_payload(params.daily_payload, params.user_data)
    simulate_request["stateDescription"] = params.state_description

    artifacts = SingleUploadExecutionArtifacts(
        environment=params.environment,
        summary="单数据上传执行失败。",
        simulate_request=simulate_request,
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

        artifacts.success = True
        artifacts.summary = "单数据上传执行成功。"
        artifacts.simulate_response = simulate_response
        artifacts.settlement_request = settlement_request
        artifacts.settlement_response = settlement_response
        return artifacts
    except Exception as exc:  # noqa: BLE001
        artifacts.success = False
        artifacts.summary = "单数据上传执行失败。"
        artifacts.error_message = str(exc)
        return artifacts
    finally:
        api_service.close()


def execute_single_upload(params: SingleUploadParams) -> SingleUploadResultView:
    """Execute one complete simulate -> settlement flow for the current web page."""
    artifacts = execute_single_upload_artifacts(params)
    return SingleUploadResultView(
        success=artifacts.success,
        environment=artifacts.environment,
        execution_status="执行成功" if artifacts.success else "执行失败",
        summary=artifacts.summary,
        error_message=artifacts.error_message,
        simulate_request=_dump_json(artifacts.simulate_request),
        simulate_response=_dump_json(artifacts.simulate_response),
        settlement_request=_dump_json(artifacts.settlement_request),
        settlement_response=_dump_json(artifacts.settlement_response),
    )


def execute_single_upload_api(params: SingleUploadParams, include_debug: bool) -> SingleUploadApiData:
    """Execute the single-upload flow for the v1 JSON API."""
    artifacts = execute_single_upload_artifacts(params)
    return SingleUploadApiData(
        success=artifacts.success,
        executionStatus="success" if artifacts.success else "failed",
        summary=artifacts.summary,
        environment=artifacts.environment,
        errorMessage=artifacts.error_message,
        debugInfo=_build_debug_info(artifacts) if include_debug else None,
    )


def build_settlement_payload(simulate_response: dict[str, Any], user_id: str, daily_id: str) -> dict[str, Any]:
    """Build settlement payload based on the simulate response."""
    settlement_payload = dict(simulate_response)
    settlement_payload["daily"] = daily_id
    settlement_payload["dailyId"] = daily_id
    settlement_payload["userId"] = user_id
    return settlement_payload


def _build_debug_info(artifacts: SingleUploadExecutionArtifacts) -> SingleUploadDebugInfo:
    """Build optional debug info for the v1 API response."""
    return SingleUploadDebugInfo(
        simulateRequest=artifacts.simulate_request,
        simulateResponse=artifacts.simulate_response,
        settlementRequest=artifacts.settlement_request,
        settlementResponse=artifacts.settlement_response,
    )


def _dump_json(payload: Any) -> str:
    """Serialize JSON-compatible content for the web page."""
    if payload is None:
        return ""
    return json.dumps(payload, ensure_ascii=False, indent=2)
