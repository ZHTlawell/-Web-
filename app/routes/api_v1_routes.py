"""v1 JSON API route definitions."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.models.runzo import SingleUploadApiRequest, SingleUploadApiResponse
from app.services.single_upload_service import execute_single_upload_api
from app.services.validation_service import build_single_upload_params_from_api_payload

router = APIRouter(prefix="/api/runzo/v1", tags=["runzo-v1"])


@router.post("/single-upload/execute")
async def execute_single_upload_v1(request: Request) -> JSONResponse:
    """Execute the v1 single-upload JSON API."""
    try:
        payload_dict = await request.json()
    except json.JSONDecodeError:
        return _json_response(status_code=400, code=4001, message="请求体必须是合法 JSON 对象。")

    if not isinstance(payload_dict, dict):
        return _json_response(status_code=400, code=4001, message="请求体必须是 JSON 对象。")

    try:
        payload = SingleUploadApiRequest.model_validate(payload_dict)
        authorization = _require_header(request, "Authorization")
        app_version = _require_app_version(request)
        params = build_single_upload_params_from_api_payload(payload, authorization=authorization, app_version=app_version)
        result_data = execute_single_upload_api(params, include_debug=payload.include_debug)
    except ValidationError as exc:
        return _json_response(status_code=400, code=4001, message=exc.errors()[0]["msg"])
    except ValueError as exc:
        return _json_response(status_code=400, code=4001, message=str(exc))
    except Exception:  # noqa: BLE001
        return _json_response(status_code=500, code=5000, message="服务内部异常。")

    if result_data.success:
        return _json_response(status_code=200, code=0, message="success", data=result_data)
    return _json_response(status_code=400, code=4002, message="execution failed", data=result_data)


def _require_header(request: Request, header_name: str) -> str:
    """Read one required request header."""
    value = request.headers.get(header_name, "").strip()
    if not value:
        raise ValueError(f"请求头 {header_name} 不能为空。")
    return value


def _require_app_version(request: Request) -> str:
    """Read the required app version header."""
    value = request.headers.get("ts-app-version") or request.headers.get("x-ts-app-version") or ""
    app_version = value.strip()
    if not app_version:
        raise ValueError("请求头 ts-app-version 不能为空。")
    return app_version


def _json_response(
    *,
    status_code: int,
    code: int,
    message: str,
    data: Any = None,
) -> JSONResponse:
    """Build one JSON response with the unified v1 envelope."""
    payload = SingleUploadApiResponse(code=code, message=message, data=data)
    response_content = payload.model_dump(mode="json", by_alias=True, exclude_none=True)
    if data is None:
        response_content["data"] = None
    return JSONResponse(
        status_code=status_code,
        content=response_content,
    )
