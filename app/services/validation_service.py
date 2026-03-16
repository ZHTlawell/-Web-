"""Input parsing and header validation helpers."""

from __future__ import annotations

from typing import Any, Mapping, Optional

from pydantic import ValidationError

from app.models.runzo import RunzoTaskParams, RunzoUserProfile, SingleUploadApiRequest, SingleUploadParams


def validate_headers_latin1(headers: dict[str, Any]) -> None:
    """Ensure header values are latin-1 encodable."""
    invalid_fields: list[str] = []
    for key, value in headers.items():
        try:
            str(value).encode("latin-1")
        except UnicodeEncodeError:
            invalid_fields.append(f"{key}={value!r}")
    if invalid_fields:
        raise ValueError(
            "请求头包含非英文字符，无法发送。请检查 Authorization 和其他 header。"
            f" 非法字段：{' | '.join(invalid_fields)}"
        )


def build_task_params_from_form(form_data: Mapping[str, Any], app_version: Optional[str] = None) -> RunzoTaskParams:
    """Parse multi-upload form data into task params."""
    raw_data = {
        "environment": form_data.get("environment", "test"),
        "userId": form_data.get("userId", ""),
        "authorization": form_data.get("authorization", ""),
        "tsAppVersion": app_version or form_data.get("tsAppVersion", ""),
        "startFromDayStartTime": form_data.get("startFromDayStartTime", "") or None,
        "mongoCreateBy": form_data.get("mongoCreateBy", ""),
        "user_data": {
            "gender": form_data.get("gender", "male"),
            "age": form_data.get("age", 22),
            "weight": form_data.get("weight", 75),
            "height": form_data.get("height", 175),
            "hrMax": form_data.get("hrMax", 198),
            "hrRest": form_data.get("hrRest", 65),
            "targetDistance": form_data.get("targetDistance", 5),
            "intensityPreference": form_data.get("intensityPreference", "medium"),
        },
    }
    try:
        return RunzoTaskParams.model_validate(raw_data)
    except ValidationError as exc:
        raise ValueError(exc.errors()[0]["msg"]) from exc


def build_single_upload_params_from_form(
    form_data: Mapping[str, Any],
    app_version: Optional[str] = None,
) -> SingleUploadParams:
    """Parse single-upload form data into params."""
    training_blocks = _build_training_blocks_from_form(form_data)
    raw_data = {
        "environment": form_data.get("environment", "test"),
        "userId": form_data.get("userId", ""),
        "authorization": form_data.get("authorization", ""),
        "tsAppVersion": app_version or form_data.get("tsAppVersion", ""),
        "dailyId": form_data.get("dailyId", ""),
        "trainingType": form_data.get("trainingType", ""),
        "runningDistance": form_data.get("runningDistance", 0),
        "trainingBlocks": training_blocks,
        "stateDescription": form_data.get("stateDescription", ""),
        "weekIndex": form_data.get("weekIndex", "") or None,
        "dayStartTime": form_data.get("dayStartTime", "") or None,
        "user_data": {
            "gender": form_data.get("gender", "male"),
            "age": form_data.get("age", 22),
            "weight": form_data.get("weight", 75),
            "height": form_data.get("height", 175),
            "hrMax": form_data.get("hrMax", 198),
            "hrRest": form_data.get("hrRest", 65),
            "targetDistance": form_data.get("targetDistance", 5),
            "intensityPreference": form_data.get("intensityPreference", "medium"),
        },
    }
    try:
        return SingleUploadParams.model_validate(raw_data)
    except ValidationError as exc:
        raise ValueError(exc.errors()[0]["msg"]) from exc


def build_single_upload_params_from_api_payload(
    payload: SingleUploadApiRequest,
    authorization: str,
    app_version: str,
) -> SingleUploadParams:
    """Convert the v1 JSON payload and headers into service params."""
    raw_data = {
        "environment": payload.environment.value,
        "userId": payload.user_id,
        "authorization": authorization,
        "tsAppVersion": app_version,
        "dailyId": payload.daily_id,
        "trainingType": payload.training_type.value,
        "runningDistance": payload.running_distance,
        "trainingBlocks": payload.training_blocks,
        "stateDescription": payload.state_description,
        "weekIndex": payload.week_index,
        "dayStartTime": payload.day_start_time,
        "user_data": payload.user_data.model_dump(by_alias=True),
    }
    try:
        return SingleUploadParams.model_validate(raw_data)
    except ValidationError as exc:
        raise ValueError(exc.errors()[0]["msg"]) from exc


def _build_training_blocks_from_form(form_data: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Convert form fields to trainingBlocks by training type."""
    training_type = str(form_data.get("trainingType", "")).strip()
    if training_type in {"Easy", "LSD", "Rest", "ExtraSession"}:
        return [
            {
                "minPace": _read_required_text(form_data, "easyMinPace", "主训练最小配速不能为空"),
                "maxPace": _read_required_text(form_data, "easyMaxPace", "主训练最大配速不能为空"),
            }
        ]

    if training_type == "Threshold":
        return [
            {
                "minPace": _read_required_text(form_data, "thresholdWarmupMinPace", "热身最小配速不能为空"),
                "maxPace": _read_required_text(form_data, "thresholdWarmupMaxPace", "热身最大配速不能为空"),
                "distance": _read_optional_float(form_data, "thresholdWarmupDistance"),
            },
            {
                "minPace": _read_required_text(form_data, "thresholdMainMinPace", "主段最小配速不能为空"),
                "maxPace": _read_required_text(form_data, "thresholdMainMaxPace", "主段最大配速不能为空"),
                "distance": _read_optional_float(form_data, "thresholdMainDistance"),
            },
        ]

    if training_type == "Interval":
        return _build_interval_blocks(form_data)

    return []


def _build_interval_blocks(form_data: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Build Interval training blocks required by simulate."""
    warmup_block = _read_interval_base_block(form_data, 1, "热身段")
    interval_block = _read_interval_repeat_block(form_data, 2, "主训练段", "interval")
    jogging_block = _read_interval_repeat_block(form_data, 3, "慢跑段", "jogging")
    repeat_num = _read_optional_int(form_data, "intervalRepeatNum") or 1
    return [
        warmup_block,
        {
            "repeatNum": repeat_num,
            **interval_block,
            **jogging_block,
        },
    ]


def _read_interval_base_block(form_data: Mapping[str, Any], index: int, phase_name: str) -> dict[str, Any]:
    """Read the Interval warmup block."""
    return {
        "minPace": _read_required_text(form_data, f"intervalBlock{index}MinPace", f"{phase_name}最小配速不能为空"),
        "maxPace": _read_required_text(form_data, f"intervalBlock{index}MaxPace", f"{phase_name}最大配速不能为空"),
        "distance": _read_required_float(form_data, f"intervalBlock{index}Distance", f"{phase_name}距离不能为空"),
    }


def _read_interval_repeat_block(
    form_data: Mapping[str, Any],
    index: int,
    phase_name: str,
    field_prefix: str,
) -> dict[str, Any]:
    """Read one phase inside the Interval repeat block."""
    return {
        f"{field_prefix}MinPace": _read_required_text(
            form_data, f"intervalBlock{index}MinPace", f"{phase_name}最小配速不能为空"
        ),
        f"{field_prefix}MaxPace": _read_required_text(
            form_data, f"intervalBlock{index}MaxPace", f"{phase_name}最大配速不能为空"
        ),
        f"{field_prefix}Distance": _read_required_float(
            form_data, f"intervalBlock{index}Distance", f"{phase_name}距离不能为空"
        ),
    }


def _read_required_text(form_data: Mapping[str, Any], field_name: str, error_message: str) -> str:
    """Read a required text field."""
    value = str(form_data.get(field_name, "")).strip()
    if not value:
        raise ValueError(error_message)
    return value


def _read_optional_float(form_data: Mapping[str, Any], field_name: str) -> Optional[float]:
    """Read an optional float field."""
    raw_value = form_data.get(field_name, "")
    if raw_value in ("", None):
        return None
    return float(raw_value)


def _read_required_float(form_data: Mapping[str, Any], field_name: str, error_message: str) -> float:
    """Read a required float field."""
    raw_value = form_data.get(field_name, "")
    if raw_value in ("", None):
        raise ValueError(error_message)
    return float(raw_value)


def _read_optional_int(form_data: Mapping[str, Any], field_name: str) -> Optional[int]:
    """Read an optional integer field."""
    raw_value = form_data.get(field_name, "")
    if raw_value in ("", None):
        return None
    return int(float(raw_value))


def build_base_headers(
    params: RunzoTaskParams,
    default_lang: str,
    default_time_zone: str,
    default_country: str,
) -> dict[str, str]:
    """Build settlement headers for multi-upload."""
    headers = {
        "ts-user-id": params.user_id,
        "Authorization": params.authorization,
        "ts-app-version": params.app_version,
        "lang": default_lang,
        "ts-time-zone-id": default_time_zone,
        "ts-country": default_country,
    }
    validate_headers_latin1(headers)
    return headers


def build_single_upload_headers(
    params: SingleUploadParams,
    default_lang: str,
    default_time_zone: str,
    default_country: str,
) -> dict[str, str]:
    """Build settlement headers for single-upload."""
    headers = {
        "ts-user-id": params.user_id,
        "Authorization": params.authorization,
        "ts-app-version": params.app_version,
        "lang": default_lang,
        "ts-time-zone-id": default_time_zone,
        "ts-country": default_country,
    }
    validate_headers_latin1(headers)
    return headers


def clone_user_profile(params: RunzoTaskParams) -> RunzoUserProfile:
    """Return a deep copy of the user profile."""
    return params.user_data.model_copy(deep=True)
