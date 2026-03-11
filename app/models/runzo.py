"""Runzo 相关数据模型定义。"""

from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class 任务状态(str, Enum):
    """任务运行状态。"""

    待开始 = "待开始"
    执行中 = "执行中"
    等待确认 = "等待确认"
    已完成 = "已完成"
    已失败 = "已失败"
    已终止 = "已终止"


class 运行环境(str, Enum):
    """可选运行环境。"""

    测试 = "test"
    预发布 = "preprod"


class 训练类型(str, Enum):
    """Runzo 支持的训练类型。"""

    Easy = "Easy"
    LSD = "LSD"
    Rest = "Rest"
    ExtraSession = "ExtraSession"
    Threshold = "Threshold"
    Interval = "Interval"


class 任务检查点类型(str, Enum):
    """任务暂停时使用的检查点类型。"""

    首次类型确认 = "首次类型确认"
    周切换确认 = "周切换确认"


class 日志级别(str, Enum):
    """日志显示级别。"""

    信息 = "信息"
    成功 = "成功"
    警告 = "警告"
    错误 = "错误"


class Runzo用户画像(BaseModel):
    """用户画像输入参数。"""

    gender: str = "male"
    age: int = 22
    weight: float = 75
    height: float = 175
    hr_max: int = Field(default=198, alias="hrMax")
    hr_rest: int = Field(default=65, alias="hrRest")
    target_distance: float = Field(default=5, alias="targetDistance")
    intensity_preference: str = Field(default="medium", alias="intensityPreference")

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("age", "hr_max", "hr_rest")
    @classmethod
    def 校验正整数(cls, value: int) -> int:
        """校验必须为正整数。"""
        if value <= 0:
            raise ValueError("该字段必须大于 0")
        return value

    @field_validator("weight", "height", "target_distance")
    @classmethod
    def 校验正数(cls, value: float) -> float:
        """校验必须为正数。"""
        if value <= 0:
            raise ValueError("该字段必须大于 0")
        return value


class Runzo表单参数(BaseModel):
    """页面提交的完整任务参数。"""

    user_id: str = Field(alias="userId")
    environment: 运行环境 = Field(default=运行环境.测试, alias="environment")
    authorization: str
    start_from_day_start_time: Optional[int] = Field(default=None, alias="startFromDayStartTime")
    mongo_create_by: Optional[str] = Field(default=None, alias="mongoCreateBy")
    user_data: Runzo用户画像

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("user_id", "authorization")
    @classmethod
    def 校验非空字符串(cls, value: str) -> str:
        """校验关键字符串非空。"""
        文本 = value.strip()
        if not 文本:
            raise ValueError("该字段不能为空")
        return 文本

    @field_validator("start_from_day_start_time")
    @classmethod
    def 校验起跑时间(cls, value: Optional[int]) -> Optional[int]:
        """校验断点起跑时间。"""
        if value is None:
            return None
        if value <= 0:
            raise ValueError("起跑时间必须大于 0")
        return value

    @property
    def 任务查询创建人(self) -> str:
        """返回 Mongo 查询时使用的 createBy。"""
        return (self.mongo_create_by or self.user_id).strip()


class 单数据上传表单参数(BaseModel):
    """页面提交的单数据上传参数。"""

    user_id: str = Field(alias="userId")
    environment: 运行环境 = Field(default=运行环境.测试, alias="environment")
    authorization: str
    daily_id: str = Field(alias="dailyId")
    training_type: 训练类型 = Field(alias="trainingType")
    running_distance: float = Field(alias="runningDistance")
    training_blocks: List[Dict[str, Any]] = Field(alias="trainingBlocks")
    state_description: str = Field(default="", alias="stateDescription")
    week_index: Optional[int] = Field(default=None, alias="weekIndex")
    day_start_time: Optional[int] = Field(default=None, alias="dayStartTime")
    user_data: Runzo用户画像

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("user_id", "authorization", "daily_id")
    @classmethod
    def 校验必填字符串(cls, value: str) -> str:
        """校验关键字符串非空。"""
        文本 = value.strip()
        if not 文本:
            raise ValueError("该字段不能为空")
        return 文本

    @field_validator("running_distance")
    @classmethod
    def 校验目标距离(cls, value: float) -> float:
        """校验训练目标距离。"""
        if value <= 0:
            raise ValueError("目标距离必须大于 0")
        return value

    @field_validator("week_index", "day_start_time")
    @classmethod
    def 校验可选正整数(cls, value: Optional[int]) -> Optional[int]:
        """校验可选数字字段。"""
        if value is None:
            return None
        if value <= 0:
            raise ValueError("该字段必须大于 0")
        return value

    @field_validator("training_blocks")
    @classmethod
    def 校验训练块列表(cls, value: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """校验训练块至少有一项。"""
        if not value:
            raise ValueError("训练块 JSON 不能为空")
        return value

    @property
    def daily对象(self) -> Dict[str, Any]:
        """转成构建 simulate 请求体需要的 daily 结构。"""
        daily: Dict[str, Any] = {
            "_id": self.daily_id,
            "trainingType": self.training_type.value,
            "runningDistance": self.running_distance,
            "trainingBlocks": self.training_blocks,
        }
        if self.week_index is not None:
            daily["weekIndex"] = self.week_index
        if self.day_start_time is not None:
            daily["dayStartTime"] = self.day_start_time
        return daily


class 单数据上传结果视图(BaseModel):
    """返回给单数据上传页面的执行结果。"""

    是否成功: bool = False
    当前环境: 运行环境 = 运行环境.测试
    执行状态: str = "待开始"
    摘要: str = "尚未执行单数据上传。"
    错误信息: Optional[str] = None
    simulate请求体: str = ""
    simulate响应体: str = ""
    settlement请求体: str = ""
    settlement响应体: str = ""


class Runzo日志项(BaseModel):
    """任务日志项。"""

    时间: datetime
    级别: 日志级别
    内容: str


class Runzo任务视图(BaseModel):
    """返回给页面和接口的任务快照。"""

    任务ID: Optional[str] = None
    状态: 任务状态 = 任务状态.待开始
    摘要: str = "尚未开始执行任务。"
    当前环境: 运行环境 = 运行环境.测试
    检查点类型: Optional[任务检查点类型] = None
    检查点提示: Optional[str] = None
    当前周: Optional[int] = None
    当前训练类型: Optional[str] = None
    当前日开始时间: Optional[int] = None
    已完成数量: int = 0
    日志列表: List[Runzo日志项] = Field(default_factory=list)
    错误信息: Optional[str] = None
    已屏蔽令牌: Optional[str] = None


class Runzo任务接口响应(BaseModel):
    """统一的 API JSON 响应。"""

    成功: bool
    消息: str
    数据: Runzo任务视图


class Runzo执行上下文(BaseModel):
    """任务执行过程中保存在内存中的上下文。"""

    任务ID: str
    参数: Runzo表单参数
    状态: 任务状态
    摘要: str
    当前环境: 运行环境
    检查点类型: Optional[任务检查点类型] = None
    检查点提示: Optional[str] = None
    当前周: Optional[int] = None
    当前训练类型: Optional[str] = None
    当前日开始时间: Optional[int] = None
    已完成数量: int = 0
    日志列表: List[Runzo日志项] = Field(default_factory=list)
    错误信息: Optional[str] = None
    已处理ID列表: List[str] = Field(default_factory=list)
    上次完成日开始时间: Optional[int] = None
    周字段名: Optional[str] = None
    已完成首次类型确认: bool = False
    已见到轻松或LSD: bool = False
    已见到阈值: bool = False
    已见到间歇: bool = False

    def 转为视图(self) -> Runzo任务视图:
        """将运行态转换为页面可消费的只读视图。"""
        return Runzo任务视图(
            任务ID=self.任务ID,
            状态=self.状态,
            摘要=self.摘要,
            当前环境=self.当前环境,
            检查点类型=self.检查点类型,
            检查点提示=self.检查点提示,
            当前周=self.当前周,
            当前训练类型=self.当前训练类型,
            当前日开始时间=self.当前日开始时间,
            已完成数量=self.已完成数量,
            日志列表=list(reversed(self.日志列表)),
            错误信息=self.错误信息,
            已屏蔽令牌=self.屏蔽后的令牌,
        )

    @property
    def 屏蔽后的令牌(self) -> str:
        """以脱敏形式返回 Authorization，避免页面暴露完整值。"""
        原始值 = self.参数.authorization.strip()
        if len(原始值) <= 12:
            return "******"
        return f"{原始值[:10]}...{原始值[-6:]}"

    def 添加日志(self, 级别: 日志级别, 内容: str) -> None:
        """追加一条日志。"""
        self.日志列表.append(Runzo日志项(时间=datetime.now(), 级别=级别, 内容=内容))


def 创建默认表单参数() -> Dict[str, Any]:
    """生成页面首屏展示的默认表单值。"""
    return {
        "environment": "test",
        "userId": "92114529545000186",
        "authorization": "",
        "startFromDayStartTime": "",
        "mongoCreateBy": "92114529545000186",
        "gender": "male",
        "age": 22,
        "weight": 75,
        "height": 175,
        "hrMax": 198,
        "hrRest": 65,
        "targetDistance": 5,
        "intensityPreference": "medium",
    }


def 创建单数据默认表单参数() -> Dict[str, Any]:
    """生成单数据上传页面的默认表单值。"""
    return {
        "environment": "test",
        "userId": "92114529545000186",
        "authorization": "",
        "dailyId": "",
        "trainingType": "Threshold",
        "runningDistance": 8,
        "stateDescription": "",
        "weekIndex": "",
        "dayStartTime": "",
        "easyMinPace": "6:00",
        "easyMaxPace": "6:30",
        "thresholdWarmupMinPace": "6:00",
        "thresholdWarmupMaxPace": "6:30",
        "thresholdWarmupDistance": 2,
        "thresholdMainMinPace": "4:30",
        "thresholdMainMaxPace": "4:45",
        "thresholdMainDistance": 4,
        "intervalBlock1MinPace": "6:00",
        "intervalBlock1MaxPace": "6:30",
        "intervalBlock1Distance": 1,
        "intervalBlock2MinPace": "4:20",
        "intervalBlock2MaxPace": "4:35",
        "intervalBlock2Distance": 1,
        "intervalRepeatNum": 6,
        "intervalBlock3MinPace": "6:00",
        "intervalBlock3MaxPace": "6:30",
        "intervalBlock3Distance": 1,
        "gender": "male",
        "age": 22,
        "weight": 75,
        "height": 175,
        "hrMax": 198,
        "hrRest": 65,
        "targetDistance": 5,
        "intensityPreference": "medium",
    }
