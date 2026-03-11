"""单数据上传服务。"""

from __future__ import annotations

import json
from typing import Any, Dict

from app.models.runzo import 单数据上传结果视图, 单数据上传表单参数
from app.services.payload_builder_service import 构建模拟请求体
from app.services.runzo_api_service import Runzo接口服务
from app.services.settings import 获取环境连接配置, 获取配置
from app.services.validation_service import 构建单数据基础请求头


def 执行单数据上传(参数: 单数据上传表单参数) -> 单数据上传结果视图:
    """执行单次 simulate 与 settlement 串联调用。"""
    配置 = 获取配置()
    环境配置 = 获取环境连接配置(参数.environment)
    simulate请求体 = 构建模拟请求体(参数.daily对象, 参数.user_data)
    simulate请求体["stateDescription"] = 参数.state_description

    结果 = 单数据上传结果视图(
        当前环境=参数.environment,
        执行状态="执行中",
        simulate请求体=json.dumps(simulate请求体, ensure_ascii=False, indent=2),
    )

    请求头 = 构建单数据基础请求头(
        参数=参数,
        默认语言=配置.default_lang,
        默认时区=配置.default_time_zone,
        默认国家=配置.default_country,
    )

    接口服务 = Runzo接口服务(simulate_url=配置.simulate_url, settle_url=环境配置.settle_url)
    try:
        simulate响应体 = 接口服务.模拟训练(simulate请求体)
        settlement请求体 = _构建结算请求体(simulate响应体, 参数.user_id, 参数.daily_id)
        settlement响应体 = 接口服务.结算训练(settlement请求体, 请求头)

        结果.是否成功 = True
        结果.执行状态 = "执行成功"
        结果.摘要 = "单数据上传执行成功。"
        结果.simulate响应体 = json.dumps(simulate响应体, ensure_ascii=False, indent=2)
        结果.settlement请求体 = json.dumps(settlement请求体, ensure_ascii=False, indent=2)
        结果.settlement响应体 = json.dumps(settlement响应体, ensure_ascii=False, indent=2)
        return 结果
    except Exception as exc:  # noqa: BLE001
        结果.是否成功 = False
        结果.执行状态 = "执行失败"
        结果.摘要 = "单数据上传执行失败。"
        结果.错误信息 = str(exc)
        return 结果
    finally:
        接口服务.关闭()


def _构建结算请求体(simulate响应体: Dict[str, Any], 用户ID: str, daily_id: str) -> Dict[str, Any]:
    """基于 simulate 响应构建 settlement 请求体。"""
    settlement请求体 = dict(simulate响应体)
    settlement请求体["daily"] = daily_id
    settlement请求体["dailyId"] = daily_id
    settlement请求体["userId"] = 用户ID
    return settlement请求体
