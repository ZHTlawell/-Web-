"""Runzo domain models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TaskStatus(str, Enum):
    """Task runtime status."""

    PENDING = "待开始"
    RUNNING = "执行中"
    WAITING_CONFIRM = "等待确认"
    COMPLETED = "已完成"
    FAILED = "已失败"
    CANCELLED = "已终止"


class RuntimeEnvironment(str, Enum):
    """Available runtime environments."""

    TEST = "test"
    PREPROD = "preprod"


class TrainingType(str, Enum):
    """Supported Runzo training types."""

    EASY = "Easy"
    LSD = "LSD"
    REST = "Rest"
    EXTRA_SESSION = "ExtraSession"
    THRESHOLD = "Threshold"
    INTERVAL = "Interval"


class TaskCheckpointType(str, Enum):
    """Checkpoint types used when a task pauses."""

    FIRST_TYPE_CONFIRM = "首次类型确认"
    WEEK_SWITCH_CONFIRM = "周切换确认"


class LogLevel(str, Enum):
    """Log levels displayed in UI."""

    INFO = "信息"
    SUCCESS = "成功"
    WARNING = "警告"
    ERROR = "错误"


class RunzoUserProfile(BaseModel):
    """User profile input payload."""

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
    def validate_positive_int(cls, value: int) -> int:
        """Ensure integer fields are positive."""
        if value <= 0:
            raise ValueError("该字段必须大于 0")
        return value

    @field_validator("weight", "height", "target_distance")
    @classmethod
    def validate_positive_float(cls, value: float) -> float:
        """Ensure float fields are positive."""
        if value <= 0:
            raise ValueError("该字段必须大于 0")
        return value


class RunzoTaskParams(BaseModel):
    """Request parameters for multi-upload task execution."""

    user_id: str = Field(alias="userId")
    environment: RuntimeEnvironment = Field(default=RuntimeEnvironment.TEST, alias="environment")
    authorization: str
    app_version: str = Field(alias="tsAppVersion")
    start_from_day_start_time: Optional[int] = Field(default=None, alias="startFromDayStartTime")
    mongo_create_by: Optional[str] = Field(default=None, alias="mongoCreateBy")
    user_data: RunzoUserProfile

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("user_id", "authorization", "app_version")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        """Validate required text fields."""
        text = value.strip()
        if not text:
            raise ValueError("该字段不能为空")
        return text

    @field_validator("start_from_day_start_time")
    @classmethod
    def validate_start_time(cls, value: Optional[int]) -> Optional[int]:
        """Validate optional start timestamp."""
        if value is None:
            return None
        if value <= 0:
            raise ValueError("起跑时间必须大于 0")
        return value

    @property
    def query_create_by(self) -> str:
        """Return createBy used for Mongo queries."""
        return (self.mongo_create_by or self.user_id).strip()


class SingleUploadParams(BaseModel):
    """Request parameters for single-upload execution."""

    user_id: str = Field(alias="userId")
    environment: RuntimeEnvironment = Field(default=RuntimeEnvironment.TEST, alias="environment")
    authorization: str
    app_version: str = Field(alias="tsAppVersion")
    daily_id: str = Field(alias="dailyId")
    training_type: TrainingType = Field(alias="trainingType")
    running_distance: float = Field(alias="runningDistance")
    training_blocks: list[dict[str, Any]] = Field(alias="trainingBlocks")
    state_description: str = Field(default="", alias="stateDescription")
    week_index: Optional[int] = Field(default=None, alias="weekIndex")
    day_start_time: Optional[int] = Field(default=None, alias="dayStartTime")
    user_data: RunzoUserProfile

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("user_id", "authorization", "app_version", "daily_id")
    @classmethod
    def validate_required_strings(cls, value: str) -> str:
        """Validate required text fields."""
        text = value.strip()
        if not text:
            raise ValueError("该字段不能为空")
        return text

    @field_validator("running_distance")
    @classmethod
    def validate_running_distance(cls, value: float) -> float:
        """Validate target running distance."""
        if value <= 0:
            raise ValueError("目标距离必须大于 0")
        return value

    @field_validator("week_index", "day_start_time")
    @classmethod
    def validate_optional_positive_int(cls, value: Optional[int]) -> Optional[int]:
        """Validate optional positive integers."""
        if value is None:
            return None
        if value <= 0:
            raise ValueError("该字段必须大于 0")
        return value

    @field_validator("training_blocks")
    @classmethod
    def validate_training_blocks(cls, value: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Ensure training blocks are not empty."""
        if not value:
            raise ValueError("训练块 JSON 不能为空")
        return value

    @property
    def daily_payload(self) -> dict[str, Any]:
        """Convert input to the daily structure used by simulate payload builder."""
        daily: dict[str, Any] = {
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


class SingleUploadResultView(BaseModel):
    """Execution result returned to the single-upload page."""

    success: bool = False
    environment: RuntimeEnvironment = RuntimeEnvironment.TEST
    execution_status: str = "待开始"
    summary: str = "尚未执行单数据上传。"
    error_message: Optional[str] = None
    simulate_request: str = ""
    simulate_response: str = ""
    settlement_request: str = ""
    settlement_response: str = ""


class TaskLogEntry(BaseModel):
    """Task log item."""

    timestamp: datetime
    level: LogLevel
    message: str


class TaskView(BaseModel):
    """Read-only task snapshot for page rendering and API output."""

    task_id: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING
    summary: str = "尚未开始执行任务。"
    environment: RuntimeEnvironment = RuntimeEnvironment.TEST
    checkpoint_type: Optional[TaskCheckpointType] = None
    checkpoint_message: Optional[str] = None
    current_week: Optional[int] = None
    current_training_type: Optional[str] = None
    current_day_start_time: Optional[int] = None
    completed_count: int = 0
    logs: list[TaskLogEntry] = Field(default_factory=list)
    error_message: Optional[str] = None
    masked_token: Optional[str] = None


class TaskApiResponse(BaseModel):
    """Standard API JSON response for task endpoints."""

    success: bool
    message: str
    data: TaskView


class RunzoExecutionContext(BaseModel):
    """In-memory execution context used by background tasks."""

    task_id: str
    params: RunzoTaskParams
    status: TaskStatus
    summary: str
    environment: RuntimeEnvironment
    checkpoint_type: Optional[TaskCheckpointType] = None
    checkpoint_message: Optional[str] = None
    current_week: Optional[int] = None
    current_training_type: Optional[str] = None
    current_day_start_time: Optional[int] = None
    completed_count: int = 0
    logs: list[TaskLogEntry] = Field(default_factory=list)
    error_message: Optional[str] = None
    processed_ids: list[str] = Field(default_factory=list)
    last_completed_day_start_time: Optional[int] = None
    week_field_name: Optional[str] = None
    has_completed_first_type_confirm: bool = False
    has_seen_easy_or_lsd: bool = False
    has_seen_threshold: bool = False
    has_seen_interval: bool = False

    def to_view(self) -> TaskView:
        """Convert runtime context to view snapshot."""
        return TaskView(
            task_id=self.task_id,
            status=self.status,
            summary=self.summary,
            environment=self.environment,
            checkpoint_type=self.checkpoint_type,
            checkpoint_message=self.checkpoint_message,
            current_week=self.current_week,
            current_training_type=self.current_training_type,
            current_day_start_time=self.current_day_start_time,
            completed_count=self.completed_count,
            logs=list(reversed(self.logs)),
            error_message=self.error_message,
            masked_token=self.masked_token,
        )

    @property
    def masked_token(self) -> str:
        """Return masked Authorization value for safe display."""
        raw_value = self.params.authorization.strip()
        if len(raw_value) <= 12:
            return "******"
        return f"{raw_value[:10]}...{raw_value[-6:]}"

    def add_log(self, level: LogLevel, message: str) -> None:
        """Append a log entry."""
        self.logs.append(TaskLogEntry(timestamp=datetime.now(), level=level, message=message))


def create_default_form_values() -> dict[str, Any]:
    """Return default values for the multi-upload page."""
    return {
        "environment": "test",
        "userId": "92114529545000186",
        "authorization": "",
        "tsAppVersion": "",
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


def create_default_single_upload_form_values() -> dict[str, Any]:
    """Return default values for the single-upload page."""
    return {
        "environment": "test",
        "userId": "92114529545000186",
        "authorization": "",
        "tsAppVersion": "",
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
