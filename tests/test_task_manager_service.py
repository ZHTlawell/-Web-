"""Task manager service tests."""

from __future__ import annotations

import time

from app.models.runzo import RunzoTaskParams
from app.services.task_manager_service import RunzoTaskManager


class FakeMongoService:
    """Fake Mongo service used in tests."""

    def __init__(self, plan_list):
        self._plan_list = plan_list
        self.call_count = 0

    def fetch_training_plans(self, params, processed_ids, last_completed_day_start_time, env_config):
        self.call_count += 1
        results = []
        for item in self._plan_list:
            if str(item["_id"]) in processed_ids:
                continue
            if last_completed_day_start_time is not None and int(item["dayStartTime"]) <= last_completed_day_start_time:
                continue
            results.append(dict(item))
        return results


class FakeRunzoApiService:
    """Fake upstream Runzo API service."""

    def close(self):
        """No resources to close in tests."""

    def simulate_training(self, payload):
        return {"mock": True, "payloadType": payload["trainingPlan"]["trainingType"]}

    def settle_training(self, payload, headers):
        return {"settled": True, "dailyId": payload["dailyId"]}


def _build_params() -> RunzoTaskParams:
    """Build test task parameters."""
    return RunzoTaskParams.model_validate(
        {
            "userId": "10001",
            "environment": "test",
            "authorization": "Bearer test-token-123456",
            "tsAppVersion": "2.6.0",
            "startFromDayStartTime": 1000,
            "mongoCreateBy": "10001",
            "user_data": {
                "gender": "male",
                "age": 22,
                "weight": 75,
                "height": 175,
                "hrMax": 198,
                "hrRest": 65,
                "targetDistance": 5,
                "intensityPreference": "medium",
            },
        }
    )


def _build_manager(plan_list) -> RunzoTaskManager:
    """Build a task manager with fake dependencies."""
    return RunzoTaskManager(
        mongo_service=FakeMongoService(plan_list),
        api_service_factory=lambda env_config: FakeRunzoApiService(),
        sleep_seconds=0,
        default_lang="zh_CN",
        default_time_zone="Asia/Shanghai",
        default_country="CN",
        environment_config_resolver=lambda environment: type(
            "EnvironmentConfig",
            (),
            {"name": "测试环境", "mongo_uri": "", "settle_url": ""},
        )(),
    )


def test_task_pauses_at_first_checkpoint_and_can_continue():
    """Task should pause at the first checkpoint and finish after continue."""
    plan_list = [
        {
            "_id": "1",
            "trainingType": "Easy",
            "dayStartTime": 1000,
            "runningDistance": 5,
            "weekIndex": 1,
            "trainingBlocks": [{"minPace": "6:00", "maxPace": "6:30"}],
        },
        {
            "_id": "2",
            "trainingType": "Threshold",
            "dayStartTime": 2000,
            "runningDistance": 8,
            "weekIndex": 1,
            "trainingBlocks": [
                {"minPace": "6:00", "maxPace": "6:30", "distance": 2},
                {"minPace": "4:30", "maxPace": "4:45", "distance": 4},
            ],
        },
        {
            "_id": "3",
            "trainingType": "Interval",
            "dayStartTime": 3000,
            "runningDistance": 6,
            "weekIndex": 1,
            "trainingBlocks": [{"minPace": "4:10", "maxPace": "4:30"}],
        },
    ]
    manager = _build_manager(plan_list)
    session_id = "session-a"

    manager.start_task(session_id, _build_params())

    deadline = time.time() + 3
    while time.time() < deadline:
        snapshot = manager.get_current_task_view(session_id)
        if snapshot.status.value == "等待确认":
            break
        time.sleep(0.05)

    assert manager.get_current_task_view(session_id).status.value == "等待确认"

    manager.continue_task(session_id)

    deadline = time.time() + 3
    while time.time() < deadline:
        snapshot = manager.get_current_task_view(session_id)
        if snapshot.status.value == "已完成":
            break
        if snapshot.status.value == "等待确认":
            manager.continue_task(session_id)
        time.sleep(0.05)

    assert manager.get_current_task_view(session_id).status.value == "已完成"


def test_start_time_can_be_none():
    """Task parameters should allow an empty start time."""
    params = RunzoTaskParams.model_validate(
        {
            "userId": "10001",
            "environment": "test",
            "authorization": "Bearer test-token-123456",
            "tsAppVersion": "2.6.0",
            "startFromDayStartTime": None,
            "mongoCreateBy": "10001",
            "user_data": {
                "gender": "male",
                "age": 22,
                "weight": 75,
                "height": 175,
                "hrMax": 198,
                "hrRest": 65,
                "targetDistance": 5,
                "intensityPreference": "medium",
            },
        }
    )

    assert params.start_from_day_start_time is None


def test_tasks_are_isolated_between_sessions():
    """Different sessions should see isolated task snapshots."""
    plan_list = [
        {
            "_id": "1",
            "trainingType": "Easy",
            "dayStartTime": 1000,
            "runningDistance": 5,
            "weekIndex": 1,
            "trainingBlocks": [{"minPace": "6:00", "maxPace": "6:30"}],
        },
        {
            "_id": "2",
            "trainingType": "Threshold",
            "dayStartTime": 2000,
            "runningDistance": 8,
            "weekIndex": 1,
            "trainingBlocks": [
                {"minPace": "6:00", "maxPace": "6:30", "distance": 2},
                {"minPace": "4:30", "maxPace": "4:45", "distance": 4},
            ],
        },
        {
            "_id": "3",
            "trainingType": "Interval",
            "dayStartTime": 3000,
            "runningDistance": 6,
            "weekIndex": 1,
            "trainingBlocks": [{"minPace": "4:10", "maxPace": "4:30"}],
        },
    ]
    manager = _build_manager(plan_list)
    session_a = "session-alpha"
    session_b = "session-beta"

    manager.start_task(session_a, _build_params())

    deadline = time.time() + 3
    while time.time() < deadline:
        if manager.get_current_task_view(session_a).status.value == "等待确认":
            break
        time.sleep(0.05)

    session_a_snapshot = manager.get_current_task_view(session_a)
    session_b_snapshot = manager.get_current_task_view(session_b)

    assert session_a_snapshot.task_id is not None
    assert session_a_snapshot.status.value == "等待确认"
    assert session_b_snapshot.task_id is None
    assert session_b_snapshot.status.value == "待开始"
