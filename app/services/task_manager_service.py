"""内存态 Runzo 单任务管理服务。"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Callable, Dict, Optional, Set

from app.models.runzo import (
    Runzo任务接口响应,
    Runzo任务视图,
    Runzo执行上下文,
    Runzo表单参数,
    日志级别,
    任务状态,
    任务检查点类型,
    运行环境,
)
from app.services.mongo_service import Mongo训练计划服务
from app.services.payload_builder_service import (
    检测周字段,
    构建模拟请求体,
    获取周序号,
    转换对象ID,
)
from app.services.runzo_api_service import Runzo接口服务
from app.services.settings import 获取环境连接配置, 获取配置, 环境连接配置
from app.services.validation_service import 构建基础请求头, 构建用户画像副本


@dataclass
class _任务会话:
    """保存单个浏览器会话对应的任务运行资源。"""

    当前任务: Optional[Runzo执行上下文] = None
    当前线程: Optional[threading.Thread] = None
    继续事件: threading.Event = field(default_factory=threading.Event)
    取消事件: threading.Event = field(default_factory=threading.Event)


class Runzo任务管理器:
    """负责按浏览器会话启动、继续、终止和查询 Runzo 任务。"""

    def __init__(
        self,
        mongo_service: Mongo训练计划服务,
        api_service_factory: Callable[[环境连接配置], Runzo接口服务],
        sleep_seconds: float,
        默认语言: str,
        默认时区: str,
        默认国家: str,
        环境配置解析器: Callable[[运行环境], 环境连接配置],
    ):
        self._mongo_service = mongo_service
        self._api_service_factory = api_service_factory
        self._sleep_seconds = sleep_seconds
        self._默认语言 = 默认语言
        self._默认时区 = 默认时区
        self._默认国家 = 默认国家
        self._环境配置解析器 = 环境配置解析器
        self._锁 = threading.RLock()
        self._会话任务映射: Dict[str, _任务会话] = {}

    def 获取当前任务视图(self, 会话标识: str) -> Runzo任务视图:
        """读取指定会话当前任务的安全快照。"""
        with self._锁:
            会话 = self._会话任务映射.get(会话标识)
            if 会话 is None or 会话.当前任务 is None:
                return Runzo任务视图()
            return 会话.当前任务.model_copy(deep=True).转为视图()

    def 启动任务(self, 会话标识: str, 参数: Runzo表单参数) -> Runzo任务接口响应:
        """为指定会话创建并启动一个新任务。"""
        with self._锁:
            会话 = self._获取或创建会话(会话标识)
            if 会话.当前任务 and 会话.当前任务.状态 in {任务状态.执行中, 任务状态.等待确认}:
                raise RuntimeError("当前会话已有任务正在执行或等待确认，请先继续或终止当前任务。")

            会话.继续事件.clear()
            会话.取消事件.clear()
            任务 = Runzo执行上下文(
                任务ID=str(uuid.uuid4()),
                参数=参数,
                状态=任务状态.执行中,
                当前环境=参数.environment,
                摘要="任务已创建，等待开始读取训练计划。",
            )
            任务.添加日志(日志级别.信息, "任务已创建，准备开始执行。")
            会话.当前任务 = 任务

            线程 = threading.Thread(target=self._执行任务线程, args=(会话标识, 任务.任务ID), daemon=True)
            会话.当前线程 = 线程
            线程.start()

            return Runzo任务接口响应(成功=True, 消息="任务已启动。", 数据=任务.转为视图())

    def 继续任务(self, 会话标识: str) -> Runzo任务接口响应:
        """继续指定会话中已暂停的任务。"""
        with self._锁:
            会话 = self._会话任务映射.get(会话标识)
            if 会话 is None or 会话.当前任务 is None:
                raise RuntimeError("当前没有可继续的任务。")
            if 会话.当前任务.状态 != 任务状态.等待确认:
                raise RuntimeError("当前任务不处于等待确认状态。")
            会话.当前任务.状态 = 任务状态.执行中
            会话.当前任务.摘要 = "已收到继续指令，任务恢复执行。"
            会话.当前任务.检查点类型 = None
            会话.当前任务.检查点提示 = None
            会话.当前任务.添加日志(日志级别.信息, "页面已发送继续执行指令。")
            会话.继续事件.set()
            return Runzo任务接口响应(成功=True, 消息="任务已继续执行。", 数据=会话.当前任务.转为视图())

    def 终止任务(self, 会话标识: str) -> Runzo任务接口响应:
        """终止指定会话中的当前任务。"""
        with self._锁:
            会话 = self._会话任务映射.get(会话标识)
            if 会话 is None or 会话.当前任务 is None:
                raise RuntimeError("当前没有可终止的任务。")

            if 会话.当前任务.状态 in {任务状态.已完成, 任务状态.已失败, 任务状态.已终止}:
                return Runzo任务接口响应(成功=True, 消息="任务已经结束。", 数据=会话.当前任务.转为视图())

            会话.取消事件.set()
            会话.继续事件.set()
            会话.当前任务.状态 = 任务状态.已终止
            会话.当前任务.摘要 = "任务已被人工终止。"
            会话.当前任务.错误信息 = None
            会话.当前任务.检查点类型 = None
            会话.当前任务.检查点提示 = None
            会话.当前任务.添加日志(日志级别.警告, "用户在页面点击了终止任务。")
            return Runzo任务接口响应(成功=True, 消息="任务已终止。", 数据=会话.当前任务.转为视图())

    def _获取或创建会话(self, 会话标识: str) -> _任务会话:
        """返回指定会话的任务容器，不存在时自动创建。"""
        return self._会话任务映射.setdefault(会话标识, _任务会话())

    def _执行任务线程(self, 会话标识: str, 任务ID: str) -> None:
        """后台线程入口。"""
        with self._锁:
            会话 = self._会话任务映射.get(会话标识)
            if 会话 is None or 会话.当前任务 is None or 会话.当前任务.任务ID != 任务ID:
                return
            任务 = 会话.当前任务

        try:
            self._执行任务主体(会话标识, 任务)
        except Exception as exc:  # noqa: BLE001
            with self._锁:
                会话 = self._会话任务映射.get(会话标识)
                if 会话 and 会话.当前任务 and 会话.当前任务.任务ID == 任务ID:
                    会话.当前任务.状态 = 任务状态.已失败
                    会话.当前任务.错误信息 = str(exc)
                    会话.当前任务.摘要 = "任务执行失败。"
                    会话.当前任务.添加日志(日志级别.错误, str(exc))

    def _执行任务主体(self, 会话标识: str, 任务: Runzo执行上下文) -> None:
        """按原脚本规则执行完整任务流。"""
        会话 = self._获取或创建会话(会话标识)
        基础请求头 = 构建基础请求头(
            参数=任务.参数,
            默认语言=self._默认语言,
            默认时区=self._默认时区,
            默认国家=self._默认国家,
        )
        环境配置 = self._环境配置解析器(任务.参数.environment)
        用户画像 = 构建用户画像副本(任务.参数)
        已处理ID集合: Set[str] = set(任务.已处理ID列表)

        cycle = self._mongo_service.获取训练计划(
            参数=任务.参数,
            已处理ID列表=已处理ID集合,
            上次完成日开始时间=任务.上次完成日开始时间,
            环境配置=环境配置,
        )
        if not cycle:
            raise RuntimeError("MongoDB 未查到任何可执行训练计划。")

        任务.周字段名 = 检测周字段(cycle)
        任务.摘要 = f"已载入 {len(cycle)} 条训练计划，开始执行。"
        任务.添加日志(日志级别.信息, f"当前环境：{环境配置.name}。")
        任务.添加日志(日志级别.信息, f"已载入 {len(cycle)} 条训练计划。")

        api_service = self._api_service_factory(环境配置)
        try:
            while cycle:
                if 会话.取消事件.is_set():
                    return

                daily = cycle.pop(0)
                daily_id = 转换对象ID(daily["_id"])
                训练类型 = str(daily["trainingType"])
                当前周 = 获取周序号(daily, 任务.周字段名)
                日开始时间 = int(daily["dayStartTime"])

                with self._锁:
                    当前会话 = self._会话任务映射.get(会话标识)
                    if 当前会话 is None or 当前会话.当前任务 is None or 当前会话.当前任务.任务ID != 任务.任务ID:
                        return
                    任务.当前训练类型 = 训练类型
                    任务.当前周 = 当前周
                    任务.当前日开始时间 = 日开始时间
                    任务.摘要 = f"正在执行 {训练类型}，dayStartTime={日开始时间}。"
                    任务.添加日志(
                        日志级别.信息,
                        f"开始执行训练：dayStartTime={日开始时间}，week={当前周}，type={训练类型}。",
                    )

                模拟请求体 = 构建模拟请求体(daily, 用户画像)
                simulate_resp = api_service.模拟训练(模拟请求体)
                settle_payload = dict(simulate_resp, dailyId=daily_id, userId=任务.参数.user_id)
                请求头 = dict(基础请求头, **{"ts-request-id": str(uuid.uuid4())})
                api_service.结算训练(settle_payload, 请求头)

                with self._锁:
                    任务.已完成数量 += 1
                    任务.已处理ID列表.append(daily_id)
                    任务.上次完成日开始时间 = 日开始时间
                    任务.摘要 = f"{训练类型} 执行完成。"
                    任务.添加日志(
                        日志级别.成功,
                        f"训练完成：dayStartTime={日开始时间}，week={当前周}，type={训练类型}。",
                    )

                已处理ID集合.add(daily_id)
                self._更新首次类型标记(任务, 训练类型)

                if (not 任务.已完成首次类型确认) and 任务.已见到轻松或LSD and 任务.已见到阈值 and 任务.已见到间歇:
                    任务.已完成首次类型确认 = True
                    self._等待检查点(
                        会话标识,
                        任务,
                        任务检查点类型.首次类型确认,
                        "已完成 Easy/LSD、Threshold、Interval 各一次，请点击继续执行。",
                    )
                    if 会话.取消事件.is_set():
                        return

                下一周 = 获取周序号(cycle[0], 任务.周字段名) if cycle else None
                if 下一周 != 当前周:
                    self._等待检查点(
                        会话标识,
                        任务,
                        任务检查点类型.周切换确认,
                        f"第 {当前周} 周训练完成，请点击继续执行下一周。",
                    )
                    if 会话.取消事件.is_set():
                        return

                    cycle = self._mongo_service.获取训练计划(
                        参数=任务.参数,
                        已处理ID列表=已处理ID集合,
                        上次完成日开始时间=任务.上次完成日开始时间,
                        环境配置=环境配置,
                    )
                    任务.周字段名 = 检测周字段(cycle)
                    任务.添加日志(日志级别.信息, f"已重新读取训练计划，剩余 {len(cycle)} 条。")

                if self._sleep_seconds > 0:
                    time.sleep(self._sleep_seconds)

            with self._锁:
                任务.状态 = 任务状态.已完成
                任务.摘要 = "全部训练已执行完成。"
                任务.检查点类型 = None
                任务.检查点提示 = None
                任务.添加日志(日志级别.成功, "任务已全部执行完成。")
        finally:
            api_service.关闭()

    def _更新首次类型标记(self, 任务: Runzo执行上下文, 训练类型: str) -> None:
        """更新首次三类训练的完成标记。"""
        if 训练类型 in {"Easy", "LSD"}:
            任务.已见到轻松或LSD = True
        elif 训练类型 == "Threshold":
            任务.已见到阈值 = True
        elif 训练类型 == "Interval":
            任务.已见到间歇 = True

    def _等待检查点(self, 会话标识: str, 任务: Runzo执行上下文, 类型: 任务检查点类型, 提示: str) -> None:
        """把任务切换为等待确认状态，并阻塞到收到继续命令。"""
        with self._锁:
            会话 = self._会话任务映射.get(会话标识)
            if 会话 is None:
                return
            任务.状态 = 任务状态.等待确认
            任务.检查点类型 = 类型
            任务.检查点提示 = 提示
            任务.摘要 = 提示
            任务.添加日志(日志级别.警告, 提示)
            会话.继续事件.clear()

        while not 会话.取消事件.is_set():
            if 会话.继续事件.wait(timeout=0.2):
                会话.继续事件.clear()
                with self._锁:
                    当前会话 = self._会话任务映射.get(会话标识)
                    if 当前会话 is None or 当前会话.当前任务 is None or 当前会话.当前任务.任务ID != 任务.任务ID:
                        return
                    任务.状态 = 任务状态.执行中
                    任务.检查点类型 = None
                    任务.检查点提示 = None
                    任务.摘要 = "已收到继续执行指令。"
                    任务.添加日志(日志级别.信息, "继续执行任务。")
                return


_配置 = 获取配置()
task_manager = Runzo任务管理器(
    mongo_service=Mongo训练计划服务(_配置),
    api_service_factory=lambda 环境配置: Runzo接口服务(
        simulate_url=_配置.simulate_url,
        settle_url=环境配置.settle_url,
    ),
    sleep_seconds=_配置.day_sleep_seconds,
    默认语言=_配置.default_lang,
    默认时区=_配置.default_time_zone,
    默认国家=_配置.default_country,
    环境配置解析器=获取环境连接配置,
)
