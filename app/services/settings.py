"""应用配置定义。"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from app.models.runzo import 运行环境


@dataclass(frozen=True)
class 环境连接配置:
    """与具体环境绑定的连接配置。"""

    code: 运行环境
    name: str
    mongo_uri: str
    mongo_db: str
    mongo_collection: str
    settle_url: str


@dataclass(frozen=True)
class 运行配置:
    """集中管理服务端运行配置。"""

    simulate_url: str
    day_sleep_seconds: float
    default_lang: str
    default_time_zone: str
    default_country: str
    测试环境: 环境连接配置
    预发布环境: 环境连接配置


@lru_cache(maxsize=1)
def 获取配置() -> 运行配置:
    """读取运行配置，优先使用环境变量。"""
    全局默认库名 = os.getenv("RUNZO_MONGO_DB", "echo")
    全局默认集合名 = os.getenv("RUNZO_MONGO_COLLECTION", "runzo_training_daily")
    return 运行配置(
        simulate_url=os.getenv("RUNZO_SIMULATE_URL", "http://113.44.60.56:8001/simulate"),
        day_sleep_seconds=float(os.getenv("RUNZO_DAY_SLEEP_SECONDS", "0.2")),
        default_lang=os.getenv("RUNZO_DEFAULT_LANG", "zh_CN"),
        default_time_zone=os.getenv("RUNZO_DEFAULT_TIME_ZONE", "Asia/Shanghai"),
        default_country=os.getenv("RUNZO_DEFAULT_COUNTRY", "CN"),
        测试环境=环境连接配置(
            code=运行环境.测试,
            name="测试环境",
            mongo_uri=os.getenv(
                "RUNZO_TEST_MONGO_URI",
                "mongodb://rwuser:Z3jaDyu*c!ZVKm*GBgpb@1.94.8.122:8004/echo?authSource=admin&directConnection=true",
            ),
            mongo_db=os.getenv("RUNZO_TEST_MONGO_DB", 全局默认库名),
            mongo_collection=os.getenv("RUNZO_TEST_MONGO_COLLECTION", 全局默认集合名),
            settle_url=os.getenv(
                "RUNZO_TEST_SETTLE_URL",
                "https://tsapiv1-test.shasoapp.com/turing-runner//runzo/settlement/watch-settle",
            ),
        ),
        预发布环境=环境连接配置(
            code=运行环境.预发布,
            name="预发布环境",
            mongo_uri=os.getenv(
                "RUNZO_PREPROD_MONGO_URI",
                "mongodb://rwuser:hYEB%3D%23y3tyiZyYex2C0M@123.60.41.195:8635/echo?authSource=admin&directConnection=true",
            ),
            mongo_db=os.getenv("RUNZO_PREPROD_MONGO_DB", "rework"),
            mongo_collection=os.getenv("RUNZO_PREPROD_MONGO_COLLECTION", 全局默认集合名),
            settle_url=os.getenv(
                "RUNZO_PREPROD_SETTLE_URL",
                "https://tsapiv1.shasoapp.com/turing-runner//runzo/settlement/watch-settle",
            ),
        ),
    )


def 获取环境连接配置(环境: 运行环境) -> 环境连接配置:
    """按环境代号返回对应的连接配置。"""
    配置 = 获取配置()
    if 环境 == 运行环境.预发布:
        return 配置.预发布环境
    return 配置.测试环境
