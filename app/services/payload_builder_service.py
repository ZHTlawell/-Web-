"""simulate payload builder."""

from __future__ import annotations

from typing import Any, Optional

from app.models.runzo import RunzoUserProfile


def get_pace_range(block: dict[str, Any]) -> tuple[str, str]:
    """Read min/max pace from a training block."""
    return str(block.get("minPace", "0:00")), str(block.get("maxPace", "0:00"))


def detect_week_field(cycle: list[dict[str, Any]]) -> Optional[str]:
    """Detect the week field name from a training plan list."""
    for daily in cycle:
        if "weekIndex" in daily and daily.get("weekIndex") is not None:
            return "weekIndex"
    return None


def get_week_index(daily: dict[str, Any], week_field_name: Optional[str]) -> int:
    """Read week index using the detected field name."""
    if week_field_name:
        return int(daily.get(week_field_name))
    return -1


def stringify_object_id(value: Any) -> str:
    """Convert Mongo _id to string."""
    return str(value)


def build_simulate_payload(daily: dict[str, Any], user_profile: RunzoUserProfile) -> dict[str, Any]:
    """Build simulate payload based on training type."""
    training_type = daily["trainingType"]
    training_blocks = daily.get("trainingBlocks", []) or []
    target_distance = float(daily.get("runningDistance", 0) or 0)

    payload: dict[str, Any] = {
        "userData": user_profile.model_dump(by_alias=True),
        "trainingPlan": {},
        "stateDescription": "",
    }

    if training_type in {"Easy", "Rest", "ExtraSession"}:
        if len(training_blocks) < 1:
            raise ValueError(f"{training_type} 训练缺少 trainingBlocks")
        min_pace, max_pace = get_pace_range(training_blocks[0])
        payload["trainingPlan"] = {
            "trainingType": training_type,
            "targetDistance": target_distance,
            "phasePace": {"main": {"min": min_pace, "max": max_pace}},
        }
    elif training_type == "LSD":
        if len(training_blocks) < 1:
            raise ValueError("LSD 训练缺少 trainingBlocks")
        min_pace, max_pace = get_pace_range(training_blocks[0])
        payload["trainingPlan"] = {
            "trainingType": "LSD",
            "targetDistance": target_distance,
            "phasePace": {
                "main": {"min": min_pace, "max": max_pace},
                "rest": {"min": min_pace, "max": max_pace},
            },
        }
    elif training_type == "Threshold":
        if len(training_blocks) < 2:
            raise ValueError("Threshold 训练至少需要两个训练块")
        warmup_min, warmup_max = get_pace_range(training_blocks[0])
        main_min, main_max = get_pace_range(training_blocks[1])
        payload["trainingPlan"] = {
            "trainingType": "Threshold",
            "targetDistance": target_distance,
            "phasePace": {
                "warmup": {"min": warmup_min, "max": warmup_max},
                "main": {"min": main_min, "max": main_max},
                "rest": {"min": warmup_min, "max": warmup_max},
            },
            "phaseDistance": {
                "warmup": float(training_blocks[0].get("distance", 0) or 0),
                "main": float(training_blocks[1].get("distance", 0) or 0),
                "rest": 0.1,
            },
        }
    elif training_type == "Interval":
        payload["trainingPlan"] = {
            "trainingType": "Interval",
            "targetDistance": target_distance,
            "trainingBlocks": training_blocks,
        }
    else:
        raise ValueError(f"不支持的训练类型: {training_type}")

    return payload
