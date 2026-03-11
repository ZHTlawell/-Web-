"""校验服务测试。"""

import pytest

from app.services.validation_service import 从表单构建参数, 从表单构建单数据参数, 校验请求头可编码


def test_从表单构建参数_可正确解析():
    """表单数据应能转为 Runzo 参数对象。"""
    参数 = 从表单构建参数(
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
        }
    )

    assert 参数.user_id == "10001"
    assert 参数.environment.value == "test"
    assert 参数.start_from_day_start_time == 1773676800000
    assert 参数.user_data.hr_max == 198


def test_从表单构建参数_断点起跑时间可为空():
    """断点起跑时间留空时应解析为 None。"""
    参数 = 从表单构建参数(
        {
            "userId": "10001",
            "environment": "test",
            "authorization": "Bearer abcdefg",
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

    assert 参数.start_from_day_start_time is None


def test_校验请求头可编码_遇到中文报错():
    """请求头包含中文时应抛出异常。"""
    with pytest.raises(ValueError):
        校验请求头可编码({"Authorization": "Bearer 中文"})


def test_从表单构建单数据参数_可正确解析():
    """单数据上传表单应能正确解析。"""
    参数 = 从表单构建单数据参数(
        {
            "environment": "test",
            "userId": "10001",
            "authorization": "Bearer abcdefg",
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

    assert 参数.daily_id == "daily-001"
    assert 参数.training_type.value == "Threshold"
    assert 参数.week_index == 1
    assert 参数.day_start_time == 1773676800000
    assert len(参数.training_blocks) == 2
    assert 参数.training_blocks[0]["minPace"] == "6:00"


def test_从表单构建单数据参数_interval可由表单字段拼出训练块():
    """Interval 应按热身段 + 循环体结构组装。"""
    参数 = 从表单构建单数据参数(
        {
            "environment": "test",
            "userId": "10001",
            "authorization": "Bearer abcdefg",
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

    assert 参数.training_type.value == "Interval"
    assert len(参数.training_blocks) == 2
    assert 参数.training_blocks[0]["minPace"] == "6:00"
    assert 参数.training_blocks[1]["repeatNum"] == 6
    assert 参数.training_blocks[1]["intervalDistance"] == 1.0
    assert 参数.training_blocks[1]["joggingDistance"] == 0.5


def test_从表单构建单数据参数_interval无训练块时抛错():
    """Interval 缺少必填阶段字段时应抛错。"""
    with pytest.raises(ValueError):
        从表单构建单数据参数(
            {
                "userId": "10001",
                "authorization": "Bearer abcdefg",
                "dailyId": "daily-001",
                "trainingType": "Interval",
                "runningDistance": "5",
                "intervalRepeatNum": "2",
            }
        )


def test_从表单构建单数据参数_rest沿用_easy字段():
    """Rest 应沿用 Easy 类字段构建 trainingBlocks。"""
    参数 = 从表单构建单数据参数(
        {
            "environment": "test",
            "userId": "10001",
            "authorization": "Bearer abcdefg",
            "dailyId": "daily-003",
            "trainingType": "Rest",
            "runningDistance": "5",
            "easyMinPace": "6:20",
            "easyMaxPace": "6:40",
        }
    )

    assert 参数.training_type.value == "Rest"
    assert 参数.training_blocks == [{"minPace": "6:20", "maxPace": "6:40"}]
