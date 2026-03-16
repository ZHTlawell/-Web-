"""In-memory Runzo task manager."""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Callable, Optional

from app.models.runzo import (
    LogLevel,
    RunzoExecutionContext,
    RunzoTaskParams,
    RuntimeEnvironment,
    TaskApiResponse,
    TaskCheckpointType,
    TaskStatus,
    TaskView,
)
from app.services.mongo_service import MongoTrainingPlanService
from app.services.payload_builder_service import (
    build_simulate_payload,
    detect_week_field,
    get_week_index,
    stringify_object_id,
)
from app.services.runzo_api_service import RunzoApiService
from app.services.settings import EnvironmentConnectionConfig, get_environment_connection_config, get_settings
from app.services.validation_service import build_base_headers, clone_user_profile


@dataclass
class _TaskSession:
    """Runtime resources bound to one browser session."""

    current_task: Optional[RunzoExecutionContext] = None
    current_thread: Optional[threading.Thread] = None
    continue_event: threading.Event = field(default_factory=threading.Event)
    cancel_event: threading.Event = field(default_factory=threading.Event)


class RunzoTaskManager:
    """Manage task lifecycle per browser session."""

    def __init__(
        self,
        mongo_service: MongoTrainingPlanService,
        api_service_factory: Callable[[EnvironmentConnectionConfig], RunzoApiService],
        sleep_seconds: float,
        default_lang: str,
        default_time_zone: str,
        default_country: str,
        environment_config_resolver: Callable[[RuntimeEnvironment], EnvironmentConnectionConfig],
    ):
        self._mongo_service = mongo_service
        self._api_service_factory = api_service_factory
        self._sleep_seconds = sleep_seconds
        self._default_lang = default_lang
        self._default_time_zone = default_time_zone
        self._default_country = default_country
        self._environment_config_resolver = environment_config_resolver
        self._lock = threading.RLock()
        self._session_tasks: dict[str, _TaskSession] = {}

    def get_current_task_view(self, session_id: str) -> TaskView:
        """Return a safe snapshot of the current task."""
        with self._lock:
            session = self._session_tasks.get(session_id)
            if session is None or session.current_task is None:
                return TaskView()
            return session.current_task.model_copy(deep=True).to_view()

    def start_task(self, session_id: str, params: RunzoTaskParams) -> TaskApiResponse:
        """Create and start a new task for the given session."""
        with self._lock:
            session = self._get_or_create_session(session_id)
            if session.current_task and session.current_task.status in {
                TaskStatus.RUNNING,
                TaskStatus.WAITING_CONFIRM,
            }:
                raise RuntimeError("当前会话已有任务正在执行或等待确认，请先继续或终止当前任务。")

            session.continue_event.clear()
            session.cancel_event.clear()
            task = RunzoExecutionContext(
                task_id=str(uuid.uuid4()),
                params=params,
                status=TaskStatus.RUNNING,
                environment=params.environment,
                summary="任务已创建，等待开始读取训练计划。",
            )
            task.add_log(LogLevel.INFO, "任务已创建，准备开始执行。")
            session.current_task = task

            thread = threading.Thread(target=self._run_task_thread, args=(session_id, task.task_id), daemon=True)
            session.current_thread = thread
            thread.start()

            return TaskApiResponse(success=True, message="任务已启动。", data=task.to_view())

    def continue_task(self, session_id: str) -> TaskApiResponse:
        """Continue a paused task for the given session."""
        with self._lock:
            session = self._session_tasks.get(session_id)
            if session is None or session.current_task is None:
                raise RuntimeError("当前没有可继续的任务。")
            if session.current_task.status != TaskStatus.WAITING_CONFIRM:
                raise RuntimeError("当前任务不处于等待确认状态。")
            session.current_task.status = TaskStatus.RUNNING
            session.current_task.summary = "已收到继续指令，任务恢复执行。"
            session.current_task.checkpoint_type = None
            session.current_task.checkpoint_message = None
            session.current_task.add_log(LogLevel.INFO, "页面已发送继续执行指令。")
            session.continue_event.set()
            return TaskApiResponse(success=True, message="任务已继续执行。", data=session.current_task.to_view())

    def cancel_task(self, session_id: str) -> TaskApiResponse:
        """Cancel the current task for the given session."""
        with self._lock:
            session = self._session_tasks.get(session_id)
            if session is None or session.current_task is None:
                raise RuntimeError("当前没有可终止的任务。")

            if session.current_task.status in {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED}:
                return TaskApiResponse(success=True, message="任务已经结束。", data=session.current_task.to_view())

            session.cancel_event.set()
            session.continue_event.set()
            session.current_task.status = TaskStatus.CANCELLED
            session.current_task.summary = "任务已被人工终止。"
            session.current_task.error_message = None
            session.current_task.checkpoint_type = None
            session.current_task.checkpoint_message = None
            session.current_task.add_log(LogLevel.WARNING, "用户在页面点击了终止任务。")
            return TaskApiResponse(success=True, message="任务已终止。", data=session.current_task.to_view())

    def _get_or_create_session(self, session_id: str) -> _TaskSession:
        """Return the session container, creating it when missing."""
        return self._session_tasks.setdefault(session_id, _TaskSession())

    def _run_task_thread(self, session_id: str, task_id: str) -> None:
        """Background thread entrypoint."""
        with self._lock:
            session = self._session_tasks.get(session_id)
            if session is None or session.current_task is None or session.current_task.task_id != task_id:
                return
            task = session.current_task

        try:
            self._run_task_body(session_id, task)
        except Exception as exc:  # noqa: BLE001
            with self._lock:
                session = self._session_tasks.get(session_id)
                if session and session.current_task and session.current_task.task_id == task_id:
                    session.current_task.status = TaskStatus.FAILED
                    session.current_task.error_message = str(exc)
                    session.current_task.summary = "任务执行失败。"
                    session.current_task.add_log(LogLevel.ERROR, str(exc))

    def _run_task_body(self, session_id: str, task: RunzoExecutionContext) -> None:
        """Execute the full task flow with original script rules."""
        session = self._get_or_create_session(session_id)
        base_headers = build_base_headers(
            params=task.params,
            default_lang=self._default_lang,
            default_time_zone=self._default_time_zone,
            default_country=self._default_country,
        )
        env_config = self._environment_config_resolver(task.params.environment)
        user_profile = clone_user_profile(task.params)
        processed_ids = set(task.processed_ids)

        cycle = self._mongo_service.fetch_training_plans(
            params=task.params,
            processed_ids=processed_ids,
            last_completed_day_start_time=task.last_completed_day_start_time,
            env_config=env_config,
        )
        if not cycle:
            raise RuntimeError("MongoDB 未查到任何可执行训练计划。")

        task.week_field_name = detect_week_field(cycle)
        task.summary = f"已载入 {len(cycle)} 条训练计划，开始执行。"
        task.add_log(LogLevel.INFO, f"当前环境：{env_config.name}。")
        task.add_log(LogLevel.INFO, f"已载入 {len(cycle)} 条训练计划。")

        api_service = self._api_service_factory(env_config)
        try:
            while cycle:
                if session.cancel_event.is_set():
                    return

                daily = cycle.pop(0)
                daily_id = stringify_object_id(daily["_id"])
                training_type = str(daily["trainingType"])
                current_week = get_week_index(daily, task.week_field_name)
                day_start_time = int(daily["dayStartTime"])

                with self._lock:
                    current_session = self._session_tasks.get(session_id)
                    if (
                        current_session is None
                        or current_session.current_task is None
                        or current_session.current_task.task_id != task.task_id
                    ):
                        return
                    task.current_training_type = training_type
                    task.current_week = current_week
                    task.current_day_start_time = day_start_time
                    task.summary = f"正在执行 {training_type}，dayStartTime={day_start_time}。"
                    task.add_log(
                        LogLevel.INFO,
                        f"开始执行训练：dayStartTime={day_start_time}，week={current_week}，type={training_type}。",
                    )

                simulate_payload = build_simulate_payload(daily, user_profile)
                simulate_response = api_service.simulate_training(simulate_payload)
                settle_payload = dict(simulate_response, dailyId=daily_id, userId=task.params.user_id)
                headers = dict(base_headers, **{"ts-request-id": str(uuid.uuid4())})
                api_service.settle_training(settle_payload, headers)

                with self._lock:
                    task.completed_count += 1
                    task.processed_ids.append(daily_id)
                    task.last_completed_day_start_time = day_start_time
                    task.summary = f"{training_type} 执行完成。"
                    task.add_log(
                        LogLevel.SUCCESS,
                        f"训练完成：dayStartTime={day_start_time}，week={current_week}，type={training_type}。",
                    )

                processed_ids.add(daily_id)
                self._update_first_type_flags(task, training_type)

                if (
                    not task.has_completed_first_type_confirm
                    and task.has_seen_easy_or_lsd
                    and task.has_seen_threshold
                    and task.has_seen_interval
                ):
                    task.has_completed_first_type_confirm = True
                    self._wait_for_checkpoint(
                        session_id,
                        task,
                        TaskCheckpointType.FIRST_TYPE_CONFIRM,
                        "已完成 Easy/LSD、Threshold、Interval 各一次，请点击继续执行。",
                    )
                    if session.cancel_event.is_set():
                        return

                next_week = get_week_index(cycle[0], task.week_field_name) if cycle else None
                if next_week != current_week:
                    self._wait_for_checkpoint(
                        session_id,
                        task,
                        TaskCheckpointType.WEEK_SWITCH_CONFIRM,
                        f"第 {current_week} 周训练完成，请点击继续执行下一周。",
                    )
                    if session.cancel_event.is_set():
                        return

                    cycle = self._mongo_service.fetch_training_plans(
                        params=task.params,
                        processed_ids=processed_ids,
                        last_completed_day_start_time=task.last_completed_day_start_time,
                        env_config=env_config,
                    )
                    task.week_field_name = detect_week_field(cycle)
                    task.add_log(LogLevel.INFO, f"已重新读取训练计划，剩余 {len(cycle)} 条。")

                if self._sleep_seconds > 0:
                    time.sleep(self._sleep_seconds)

            with self._lock:
                task.status = TaskStatus.COMPLETED
                task.summary = "全部训练已执行完成。"
                task.checkpoint_type = None
                task.checkpoint_message = None
                task.add_log(LogLevel.SUCCESS, "任务已全部执行完成。")
        finally:
            api_service.close()

    def _update_first_type_flags(self, task: RunzoExecutionContext, training_type: str) -> None:
        """Update markers used for the first checkpoint."""
        if training_type in {"Easy", "LSD"}:
            task.has_seen_easy_or_lsd = True
        elif training_type == "Threshold":
            task.has_seen_threshold = True
        elif training_type == "Interval":
            task.has_seen_interval = True

    def _wait_for_checkpoint(
        self,
        session_id: str,
        task: RunzoExecutionContext,
        checkpoint_type: TaskCheckpointType,
        message: str,
    ) -> None:
        """Switch the task to waiting state until continue is received."""
        with self._lock:
            session = self._session_tasks.get(session_id)
            if session is None:
                return
            task.status = TaskStatus.WAITING_CONFIRM
            task.checkpoint_type = checkpoint_type
            task.checkpoint_message = message
            task.summary = message
            task.add_log(LogLevel.WARNING, message)
            session.continue_event.clear()

        while not session.cancel_event.is_set():
            if session.continue_event.wait(timeout=0.2):
                session.continue_event.clear()
                with self._lock:
                    current_session = self._session_tasks.get(session_id)
                    if (
                        current_session is None
                        or current_session.current_task is None
                        or current_session.current_task.task_id != task.task_id
                    ):
                        return
                    task.status = TaskStatus.RUNNING
                    task.checkpoint_type = None
                    task.checkpoint_message = None
                    task.summary = "已收到继续执行指令。"
                    task.add_log(LogLevel.INFO, "继续执行任务。")
                return


_settings = get_settings()
task_manager = RunzoTaskManager(
    mongo_service=MongoTrainingPlanService(_settings),
    api_service_factory=lambda env_config: RunzoApiService(
        simulate_url=_settings.simulate_url,
        settle_url=env_config.settle_url,
    ),
    sleep_seconds=_settings.day_sleep_seconds,
    default_lang=_settings.default_lang,
    default_time_zone=_settings.default_time_zone,
    default_country=_settings.default_country,
    environment_config_resolver=get_environment_connection_config,
)
