"""输入参数与请求头校验服务。"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping

from pydantic import ValidationError

from app.models.runzo import Runzo表单参数, Runzo用户画像, 单数据上传表单参数


def 校验请求头可编码(headers: Dict[str, Any]) -> None:
    """校验请求头内容可以被 latin-1 编码。"""
    非法字段 = []
    for key, value in headers.items():
        try:
            str(value).encode("latin-1")
        except UnicodeEncodeError:
            非法字段.append(f"{key}={value!r}")
    if 非法字段:
        raise ValueError(
            "请求头包含非英文字符，无法发送。请检查 Authorization 和其他 header。"
            f" 非法字段：{' | '.join(非法字段)}"
        )


def 从表单构建参数(form_data: Mapping[str, Any]) -> Runzo表单参数:
    """把页面提交的表单数据解析为 Runzo 任务参数。"""
    原始数据 = {
        "environment": form_data.get("environment", "test"),
        "userId": form_data.get("userId", ""),
        "authorization": form_data.get("authorization", ""),
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
        return Runzo表单参数.model_validate(原始数据)
    except ValidationError as exc:
        raise ValueError(exc.errors()[0]["msg"]) from exc


def 从表单构建单数据参数(form_data: Mapping[str, Any]) -> 单数据上传表单参数:
    """把页面提交的表单数据解析为单数据上传参数。"""
    训练块列表 = _从表单构建训练块(form_data)

    原始数据 = {
        "environment": form_data.get("environment", "test"),
        "userId": form_data.get("userId", ""),
        "authorization": form_data.get("authorization", ""),
        "dailyId": form_data.get("dailyId", ""),
        "trainingType": form_data.get("trainingType", ""),
        "runningDistance": form_data.get("runningDistance", 0),
        "trainingBlocks": 训练块列表,
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
        return 单数据上传表单参数.model_validate(原始数据)
    except ValidationError as exc:
        raise ValueError(exc.errors()[0]["msg"]) from exc


def _从表单构建训练块(form_data: Mapping[str, Any]) -> List[Dict[str, Any]]:
    """按训练类型把页面字段转换为 trainingBlocks。"""
    训练类型 = str(form_data.get("trainingType", "")).strip()
    if 训练类型 in {"Easy", "LSD", "Rest", "ExtraSession"}:
        return [
            {
                "minPace": _读取必填文本(form_data, "easyMinPace", "主训练最小配速不能为空"),
                "maxPace": _读取必填文本(form_data, "easyMaxPace", "主训练最大配速不能为空"),
            }
        ]

    if 训练类型 == "Threshold":
        return [
            {
                "minPace": _读取必填文本(form_data, "thresholdWarmupMinPace", "热身最小配速不能为空"),
                "maxPace": _读取必填文本(form_data, "thresholdWarmupMaxPace", "热身最大配速不能为空"),
                "distance": _读取可选数字(form_data, "thresholdWarmupDistance"),
            },
            {
                "minPace": _读取必填文本(form_data, "thresholdMainMinPace", "主段最小配速不能为空"),
                "maxPace": _读取必填文本(form_data, "thresholdMainMaxPace", "主段最大配速不能为空"),
                "distance": _读取可选数字(form_data, "thresholdMainDistance"),
            },
        ]

    if 训练类型 == "Interval":
        return _构建区间训练块(form_data)

    return []


def _读取区间训练块(form_data: Mapping[str, Any], 索引: int) -> Dict[str, Any]:
    """读取单个区间训练块。"""
    最小配速 = str(form_data.get(f"intervalBlock{索引}MinPace", "")).strip()
    最大配速 = str(form_data.get(f"intervalBlock{索引}MaxPace", "")).strip()
    距离 = _读取可选数字(form_data, f"intervalBlock{索引}Distance")

    if not 最小配速 and not 最大配速 and 距离 is None:
        return {}

    训练块: Dict[str, Any] = {}
    if 最小配速:
        训练块["minPace"] = 最小配速
    if 最大配速:
        训练块["maxPace"] = 最大配速
    if 距离 is not None:
        训练块["distance"] = 距离
    return 训练块


def _构建区间训练块(form_data: Mapping[str, Any]) -> List[Dict[str, Any]]:
    """按 simulate 接口要求构建 Interval 训练块。"""
    热身段 = _读取区间基础段(form_data, 1, "热身段")
    主训练段 = _读取区间循环段(form_data, 2, "主训练段", "interval")
    慢跑段 = _读取区间循环段(form_data, 3, "慢跑段", "jogging")
    循环次数 = _读取可选整数(form_data, "intervalRepeatNum") or 1

    return [
        热身段,
        {
            "repeatNum": 循环次数,
            **主训练段,
            **慢跑段,
        },
    ]


def _读取区间基础段(form_data: Mapping[str, Any], 索引: int, 阶段名称: str) -> Dict[str, Any]:
    """读取 Interval 的基础训练段。"""
    return {
        "minPace": _读取必填文本(form_data, f"intervalBlock{索引}MinPace", f"{阶段名称}最小配速不能为空"),
        "maxPace": _读取必填文本(form_data, f"intervalBlock{索引}MaxPace", f"{阶段名称}最大配速不能为空"),
        "distance": _读取必填数字(form_data, f"intervalBlock{索引}Distance", f"{阶段名称}距离不能为空"),
    }


def _读取区间循环段(form_data: Mapping[str, Any], 索引: int, 阶段名称: str, 字段前缀: str) -> Dict[str, Any]:
    """读取 Interval 循环体中的单个阶段。"""
    return {
        f"{字段前缀}MinPace": _读取必填文本(form_data, f"intervalBlock{索引}MinPace", f"{阶段名称}最小配速不能为空"),
        f"{字段前缀}MaxPace": _读取必填文本(form_data, f"intervalBlock{索引}MaxPace", f"{阶段名称}最大配速不能为空"),
        f"{字段前缀}Distance": _读取必填数字(form_data, f"intervalBlock{索引}Distance", f"{阶段名称}距离不能为空"),
    }


def _读取必填文本(form_data: Mapping[str, Any], 字段名: str, 错误信息: str) -> str:
    """读取必填文本字段。"""
    值 = str(form_data.get(字段名, "")).strip()
    if not 值:
        raise ValueError(错误信息)
    return 值


def _读取可选数字(form_data: Mapping[str, Any], 字段名: str) -> float | None:
    """读取可选数字字段。"""
    原始值 = form_data.get(字段名, "")
    if 原始值 in ("", None):
        return None
    return float(原始值)


def _读取必填数字(form_data: Mapping[str, Any], 字段名: str, 错误信息: str) -> float:
    """读取必填数字字段。"""
    原始值 = form_data.get(字段名, "")
    if 原始值 in ("", None):
        raise ValueError(错误信息)
    return float(原始值)


def _读取可选整数(form_data: Mapping[str, Any], 字段名: str) -> int | None:
    """读取可选整数字段。"""
    原始值 = form_data.get(字段名, "")
    if 原始值 in ("", None):
        return None
    return int(float(原始值))


def 构建基础请求头(参数: Runzo表单参数, 默认语言: str, 默认时区: str, 默认国家: str) -> Dict[str, str]:
    """构建 settlement 请求使用的基础请求头。"""
    请求头 = {
        "ts-user-id": 参数.user_id,
        "Authorization": 参数.authorization,
        "lang": 默认语言,
        "ts-time-zone-id": 默认时区,
        "ts-country": 默认国家,
    }
    校验请求头可编码(请求头)
    return 请求头


def 构建单数据基础请求头(参数: 单数据上传表单参数, 默认语言: str, 默认时区: str, 默认国家: str) -> Dict[str, str]:
    """构建单数据上传 settlement 请求使用的基础请求头。"""
    请求头 = {
        "ts-user-id": 参数.user_id,
        "Authorization": 参数.authorization,
        "lang": 默认语言,
        "ts-time-zone-id": 默认时区,
        "ts-country": 默认国家,
    }
    校验请求头可编码(请求头)
    return 请求头


def 构建用户画像副本(参数: Runzo表单参数) -> Runzo用户画像:
    """返回用户画像副本，避免直接引用原始对象。"""
    return 参数.user_data.model_copy(deep=True)
