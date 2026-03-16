"""Validation service tests."""

import pytest

from app.models.runzo import SingleUploadApiRequest
from app.services.validation_service import (
    build_base_headers,
    build_single_upload_params_from_api_payload,
    build_single_upload_headers,
    build_single_upload_params_from_form,
    build_task_params_from_form,
    validate_headers_latin1,
)


def test_build_task_params_from_form_parses_correctly():
    """Form data should parse into task params."""
    params = build_task_params_from_form(
        {
            "userId": "10001",
            "authorization": "Bearer abcdefg",
            "startFromDayStartTime": "1773676800000",
            "mongoCreateBy": "10001",
            "gender": "male",
            "age": "22",
            "weight": "75",
            "height": "175",
            "hrMax": "198",
            "hrRest": "65",
            "targetDistance": "5",
            "intensityPreference": "medium",
        },
        app_version="3.1.4",
    )

    assert params.user_id == "10001"
    assert params.environment.value == "test"
    assert params.app_version == "3.1.4"
    assert params.start_from_day_start_time == 1773676800000
    assert params.user_data.hr_max == 198


def test_build_task_params_from_form_allows_empty_start_time():
    """Empty start time should parse to None."""
    params = build_task_params_from_form(
        {
            "userId": "10001",
            "environment": "test",
            "authorization": "Bearer abcdefg",
            "tsAppVersion": "2.6.0",
            "startFromDayStartTime": "",
            "mongoCreateBy": "10001",
            "gender": "male",
            "age": "22",
            "weight": "75",
            "height": "175",
            "hrMax": "198",
            "hrRest": "65",
            "targetDistance": "5",
            "intensityPreference": "medium",
        }
    )

    assert params.start_from_day_start_time is None


def test_validate_headers_latin1_raises_on_chinese_text():
    """Headers with Chinese characters should raise."""
    with pytest.raises(ValueError):
        validate_headers_latin1({"Authorization": "Bearer 中文"})


def test_build_single_upload_params_from_form_parses_correctly():
    """Single upload form should parse correctly."""
    params = build_single_upload_params_from_form(
        {
            "environment": "test",
            "userId": "10001",
            "authorization": "Bearer abcdefg",
            "tsAppVersion": "2.6.0",
            "dailyId": "daily-001",
            "trainingType": "Threshold",
            "runningDistance": "8",
            "stateDescription": "测试描述",
            "weekIndex": "1",
            "dayStartTime": "1773676800000",
            "thresholdWarmupMinPace": "6:00",
            "thresholdWarmupMaxPace": "6:30",
            "thresholdWarmupDistance": "2",
            "thresholdMainMinPace": "4:30",
            "thresholdMainMaxPace": "4:45",
            "thresholdMainDistance": "4",
            "gender": "male",
            "age": "22",
            "weight": "75",
            "height": "175",
            "hrMax": "198",
            "hrRest": "65",
            "targetDistance": "5",
            "intensityPreference": "medium",
        }
    )

    assert params.daily_id == "daily-001"
    assert params.training_type.value == "Threshold"
    assert params.week_index == 1
    assert params.day_start_time == 1773676800000
    assert len(params.training_blocks) == 2
    assert params.training_blocks[0]["minPace"] == "6:00"


def test_build_single_upload_params_from_form_builds_interval_blocks():
    """Interval should be assembled as warmup block plus repeat block."""
    params = build_single_upload_params_from_form(
        {
            "environment": "test",
            "userId": "10001",
            "authorization": "Bearer abcdefg",
            "tsAppVersion": "2.6.0",
            "dailyId": "daily-002",
            "trainingType": "Interval",
            "runningDistance": "6",
            "intervalBlock1MinPace": "6:00",
            "intervalBlock1MaxPace": "6:20",
            "intervalBlock1Distance": "1",
            "intervalBlock2MinPace": "4:15",
            "intervalBlock2MaxPace": "4:30",
            "intervalBlock2Distance": "1",
            "intervalBlock3MinPace": "6:30",
            "intervalBlock3MaxPace": "6:50",
            "intervalBlock3Distance": "0.5",
            "intervalRepeatNum": "6",
        }
    )

    assert params.training_type.value == "Interval"
    assert len(params.training_blocks) == 2
    assert params.training_blocks[0]["minPace"] == "6:00"
    assert params.training_blocks[1]["repeatNum"] == 6
    assert params.training_blocks[1]["intervalDistance"] == 1.0
    assert params.training_blocks[1]["joggingDistance"] == 0.5


def test_build_single_upload_params_from_form_raises_without_interval_fields():
    """Interval should raise when required phase fields are missing."""
    with pytest.raises(ValueError):
        build_single_upload_params_from_form(
            {
                "userId": "10001",
                "authorization": "Bearer abcdefg",
                "tsAppVersion": "2.6.0",
                "dailyId": "daily-001",
                "trainingType": "Interval",
                "runningDistance": "5",
                "intervalRepeatNum": "2",
            }
        )


def test_build_single_upload_params_from_form_rest_uses_easy_fields():
    """Rest should reuse Easy-like form fields."""
    params = build_single_upload_params_from_form(
        {
            "environment": "test",
            "userId": "10001",
            "authorization": "Bearer abcdefg",
            "tsAppVersion": "2.6.0",
            "dailyId": "daily-003",
            "trainingType": "Rest",
            "runningDistance": "5",
            "easyMinPace": "6:20",
            "easyMaxPace": "6:40",
        }
    )

    assert params.training_type.value == "Rest"
    assert params.training_blocks == [{"minPace": "6:20", "maxPace": "6:40"}]


def test_build_base_headers_use_passed_app_version():
    """Multi-upload headers should use the passed app version."""
    params = build_task_params_from_form(
        {
            "userId": "10001",
            "authorization": "Bearer abcdefg",
            "mongoCreateBy": "10001",
        },
        app_version="3.1.4",
    )

    headers = build_base_headers(params, default_lang="zh_CN", default_time_zone="Asia/Shanghai", default_country="CN")

    assert headers["ts-app-version"] == "3.1.4"


def test_build_single_upload_headers_use_passed_app_version():
    """Single-upload headers should use the passed app version."""
    params = build_single_upload_params_from_form(
        {
            "userId": "10001",
            "authorization": "Bearer abcdefg",
            "dailyId": "daily-003",
            "trainingType": "Easy",
            "runningDistance": "5",
            "easyMinPace": "6:20",
            "easyMaxPace": "6:40",
        },
        app_version="4.0.1",
    )

    headers = build_single_upload_headers(
        params,
        default_lang="zh_CN",
        default_time_zone="Asia/Shanghai",
        default_country="CN",
    )

    assert headers["ts-app-version"] == "4.0.1"


def test_build_single_upload_params_from_api_payload_parses_correctly():
    """v1 JSON payload should convert into service params."""
    payload = SingleUploadApiRequest.model_validate(
        {
            "environment": "preprod",
            "userId": "10001",
            "dailyId": "daily-009",
            "trainingType": "Threshold",
            "runningDistance": 8,
            "stateDescription": "今天有点累",
            "weekIndex": 1,
            "dayStartTime": 1773676800000,
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
    )

    params = build_single_upload_params_from_api_payload(
        payload,
        authorization="Bearer abcdefg",
        app_version="2.6.0",
    )

    assert params.environment.value == "preprod"
    assert params.user_id == "10001"
    assert params.authorization == "Bearer abcdefg"
    assert params.app_version == "2.6.0"
    assert params.daily_id == "daily-009"
    assert params.training_blocks[0]["distance"] == 2
