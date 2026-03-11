"""MongoDB 训练计划读取服务。"""

from __future__ import annotations

from typing import Dict, List, Optional, Set

from pymongo import MongoClient

from app.models.runzo import Runzo表单参数
from app.services.settings import 环境连接配置, 运行配置
from app.services.payload_builder_service import 转换对象ID


class Mongo训练计划服务:
    """负责从 Mongo 读取并过滤训练计划。"""

    def __init__(self, 配置: 运行配置):
        self._配置 = 配置

    def 获取训练计划(
        self,
        参数: Runzo表单参数,
        已处理ID列表: Set[str],
        上次完成日开始时间: Optional[int],
        环境配置: 环境连接配置,
    ) -> List[Dict[str, object]]:
        """根据用户参数读取训练计划。"""
        client = MongoClient(环境配置.mongo_uri)
        try:
            collection = client[环境配置.mongo_db][环境配置.mongo_collection]
            文档列表 = list(collection.find({"createBy": 参数.任务查询创建人}))
        finally:
            client.close()

        最小日开始时间 = (
            int(参数.start_from_day_start_time)
            if 参数.start_from_day_start_time is not None
            else None
        )
        if 上次完成日开始时间 is not None:
            候选下限 = 上次完成日开始时间 + 1
            最小日开始时间 = (
                max(最小日开始时间, 候选下限)
                if 最小日开始时间 is not None
                else 候选下限
            )

        结果列表: List[Dict[str, object]] = []
        for 文档 in 文档列表:
            if 文档.get("trainingType") == "Rest":
                continue

            daily_id = 转换对象ID(文档.get("_id"))
            if daily_id in 已处理ID列表:
                continue

            if "dayStartTime" not in 文档 or 文档.get("dayStartTime") is None:
                raise RuntimeError(f"发现缺少 dayStartTime 的训练计划: dailyId={daily_id}")

            日开始时间 = int(文档["dayStartTime"])
            if 最小日开始时间 is not None and 日开始时间 < 最小日开始时间:
                continue

            结果列表.append(文档)

        结果列表.sort(key=lambda item: int(item["dayStartTime"]))
        return 结果列表
