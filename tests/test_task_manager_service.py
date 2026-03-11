"""任务管理服务测试。"""

from __future__ import annotations

import time

from app.models.runzo import Runzo表单参数
from app.services.task_manager_service import Runzo任务管理器


class 假Mongo服务:
    """用于测试的假 Mongo 服务。"""

    def __init__(self, 计划列表):
        self._计划列表 = 计划列表
        self.调用次数 = 0

    def 获取训练计划(self, 参数, 已处理ID列表, 上次完成日开始时间, 环境配置):
        self.调用次数 += 1
        结果 = []
        for 项 in self._计划列表:
            if str(项["_id"]) in 已处理ID列表:
                continue
            if 上次完成日开始时间 is not None and int(项["dayStartTime"]) <= 上次完成日开始时间:
                continue
            结果.append(dict(项))
        return 结果


class 假Runzo接口服务:
    """用于测试的假 Runzo API 服务。"""

    def 关闭(self):
        """测试桩无需释放资源。"""

    def 模拟训练(self, payload):
        return {"mock": True, "payloadType": payload["trainingPlan"]["trainingType"]}

    def 结算训练(self, payload, headers):
        return {"settled": True, "dailyId": payload["dailyId"]}


def _创建参数() -> Runzo表单参数:
    """构建测试任务参数。"""
    return Runzo表单参数.model_validate(
        {
            "userId": "10001",
            "environment": "test",
            "authorization": "Bearer test-token-123456",
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


def test_任务在首次检查点暂停并可继续():
    """任务应在首次类型确认后暂停，继续后最终完成。"""
    计划列表 = [
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
    管理器 = Runzo任务管理器(
        mongo_service=假Mongo服务(计划列表),
        api_service_factory=lambda 环境配置: 假Runzo接口服务(),
        sleep_seconds=0,
        默认语言="zh_CN",
        默认时区="Asia/Shanghai",
        默认国家="CN",
        环境配置解析器=lambda 环境: type("环境配置", (), {"name": "测试环境", "mongo_uri": "", "settle_url": ""})(),
    )

    会话标识 = "session-a"
    管理器.启动任务(会话标识, _创建参数())

    截止时间 = time.time() + 3
    while time.time() < 截止时间:
        快照 = 管理器.获取当前任务视图(会话标识)
        if 快照.状态.value == "等待确认":
            break
        time.sleep(0.05)

    assert 管理器.获取当前任务视图(会话标识).状态.value == "等待确认"

    管理器.继续任务(会话标识)

    截止时间 = time.time() + 3
    while time.time() < 截止时间:
        快照 = 管理器.获取当前任务视图(会话标识)
        if 快照.状态.value == "已完成":
            break
        if 快照.状态.value == "等待确认":
            管理器.继续任务(会话标识)
        time.sleep(0.05)

    assert 管理器.获取当前任务视图(会话标识).状态.value == "已完成"


def test_断点起跑时间允许为空():
    """当断点起跑时间为 None 时，任务仍可正常启动。"""
    参数 = Runzo表单参数.model_validate(
        {
            "userId": "10001",
            "environment": "test",
            "authorization": "Bearer test-token-123456",
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

    assert 参数.start_from_day_start_time is None


def test_不同会话的任务彼此隔离():
    """不同会话应看到各自独立的任务快照。"""
    计划列表 = [
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
    管理器 = Runzo任务管理器(
        mongo_service=假Mongo服务(计划列表),
        api_service_factory=lambda 环境配置: 假Runzo接口服务(),
        sleep_seconds=0,
        默认语言="zh_CN",
        默认时区="Asia/Shanghai",
        默认国家="CN",
        环境配置解析器=lambda 环境: type("环境配置", (), {"name": "测试环境", "mongo_uri": "", "settle_url": ""})(),
    )

    会话甲 = "session-alpha"
    会话乙 = "session-beta"

    管理器.启动任务(会话甲, _创建参数())

    截止时间 = time.time() + 3
    while time.time() < 截止时间:
        if 管理器.获取当前任务视图(会话甲).状态.value == "等待确认":
            break
        time.sleep(0.05)

    会话甲快照 = 管理器.获取当前任务视图(会话甲)
    会话乙快照 = 管理器.获取当前任务视图(会话乙)

    assert 会话甲快照.任务ID is not None
    assert 会话甲快照.状态.value == "等待确认"
    assert 会话乙快照.任务ID is None
    assert 会话乙快照.状态.value == "待开始"
