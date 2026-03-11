"""simulate 请求体构建服务。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.models.runzo import Runzo用户画像


def 获取配速范围(block: Dict[str, Any]) -> tuple[str, str]:
    """读取训练块的最小和最大配速。"""
    return str(block.get("minPace", "0:00")), str(block.get("maxPace", "0:00"))


def 检测周字段(cycle: List[Dict[str, Any]]) -> Optional[str]:
    """从训练计划列表中探测周字段名称。"""
    for daily in cycle:
        if "weekIndex" in daily and daily.get("weekIndex") is not None:
            return "weekIndex"
    return None


def 获取周序号(daily: Dict[str, Any], 周字段名: Optional[str]) -> int:
    """按探测到的字段读取周序号。"""
    if 周字段名:
        return int(daily.get(周字段名))
    return -1


def 转换对象ID(value: Any) -> str:
    """统一把 Mongo _id 转成字符串。"""
    return str(value)


def 构建模拟请求体(daily: Dict[str, Any], 用户画像: Runzo用户画像) -> Dict[str, Any]:
    """根据训练类型构建 simulate 接口请求体。"""
    训练类型 = daily["trainingType"]
    训练块列表 = daily.get("trainingBlocks", []) or []
    目标距离 = float(daily.get("runningDistance", 0) or 0)

    基础结构: Dict[str, Any] = {
        "userData": 用户画像.model_dump(by_alias=True),
        "trainingPlan": {},
        "stateDescription": "",
    }

    if 训练类型 in {"Easy", "Rest", "ExtraSession"}:
        if len(训练块列表) < 1:
            raise ValueError(f"{训练类型} 训练缺少 trainingBlocks")
        最小配速, 最大配速 = 获取配速范围(训练块列表[0])
        基础结构["trainingPlan"] = {
            "trainingType": 训练类型,
            "targetDistance": 目标距离,
            "phasePace": {"main": {"min": 最小配速, "max": 最大配速}},
        }
    elif 训练类型 == "LSD":
        if len(训练块列表) < 1:
            raise ValueError("LSD 训练缺少 trainingBlocks")
        最小配速, 最大配速 = 获取配速范围(训练块列表[0])
        基础结构["trainingPlan"] = {
            "trainingType": "LSD",
            "targetDistance": 目标距离,
            "phasePace": {
                "main": {"min": 最小配速, "max": 最大配速},
                "rest": {"min": 最小配速, "max": 最大配速},
            },
        }
    elif 训练类型 == "Threshold":
        if len(训练块列表) < 2:
            raise ValueError("Threshold 训练至少需要两个训练块")
        热身最小, 热身最大 = 获取配速范围(训练块列表[0])
        主段最小, 主段最大 = 获取配速范围(训练块列表[1])
        基础结构["trainingPlan"] = {
            "trainingType": "Threshold",
            "targetDistance": 目标距离,
            "phasePace": {
                "warmup": {"min": 热身最小, "max": 热身最大},
                "main": {"min": 主段最小, "max": 主段最大},
                "rest": {"min": 热身最小, "max": 热身最大},
            },
            "phaseDistance": {
                "warmup": float(训练块列表[0].get("distance", 0) or 0),
                "main": float(训练块列表[1].get("distance", 0) or 0),
                "rest": 0.1,
            },
        }
    elif 训练类型 == "Interval":
        基础结构["trainingPlan"] = {
            "trainingType": "Interval",
            "targetDistance": 目标距离,
            "trainingBlocks": 训练块列表,
        }
    else:
        raise ValueError(f"不支持的训练类型: {训练类型}")

    return 基础结构
