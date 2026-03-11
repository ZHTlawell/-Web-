"""payload 构建服务测试。"""

from app.models.runzo import Runzo用户画像
from app.services.payload_builder_service import 构建模拟请求体


def _默认画像() -> Runzo用户画像:
    """构建测试用用户画像。"""
    return Runzo用户画像()


def test_threshold_payload_结构正确():
    """Threshold 应生成 warmup/main/rest 三段结构。"""
    daily = {
        "trainingType": "Threshold",
        "runningDistance": 8,
        "trainingBlocks": [
            {"minPace": "6:00", "maxPace": "6:30", "distance": 2},
            {"minPace": "4:30", "maxPace": "4:45", "distance": 4},
        ],
    }

    payload = 构建模拟请求体(daily, _默认画像())

    assert payload["trainingPlan"]["trainingType"] == "Threshold"
    assert payload["trainingPlan"]["phasePace"]["warmup"]["min"] == "6:00"
    assert payload["trainingPlan"]["phasePace"]["main"]["max"] == "4:45"
    assert payload["trainingPlan"]["phaseDistance"]["main"] == 4.0


def test_interval_payload_保留训练块():
    """Interval 应直接保留 trainingBlocks。"""
    daily = {
        "trainingType": "Interval",
        "runningDistance": 5,
        "trainingBlocks": [
            {
                "distance": 0.5,
                "minPace": "7:20",
                "maxPace": "7:50",
            },
            {
                "repeatNum": 3,
                "intervalDistance": 0.8,
                "intervalMinPace": "5:10",
                "intervalMaxPace": "5:40",
                "joggingDistance": 0.2,
                "joggingMinPace": "7:20",
                "joggingMaxPace": "7:50",
            }
        ],
    }

    payload = 构建模拟请求体(daily, _默认画像())

    assert payload["trainingPlan"]["trainingType"] == "Interval"
    assert payload["trainingPlan"]["trainingBlocks"][1]["repeatNum"] == 3
    assert payload["trainingPlan"]["trainingBlocks"][1]["intervalDistance"] == 0.8


def test_rest_payload_按_easy逻辑构建():
    """Rest 应按 Easy 同类结构生成请求体。"""
    daily = {
        "trainingType": "Rest",
        "runningDistance": 3,
        "trainingBlocks": [{"minPace": "7:00", "maxPace": "7:30"}],
    }

    payload = 构建模拟请求体(daily, _默认画像())

    assert payload["trainingPlan"]["trainingType"] == "Rest"
    assert payload["trainingPlan"]["phasePace"]["main"]["min"] == "7:00"
