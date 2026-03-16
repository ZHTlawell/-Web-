"""Application settings."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from app.models.runzo import RuntimeEnvironment


@dataclass(frozen=True)
class EnvironmentConnectionConfig:
    """Connection settings bound to a specific runtime environment."""

    code: RuntimeEnvironment
    name: str
    mongo_uri: str
    mongo_db: str
    mongo_collection: str
    settle_url: str


@dataclass(frozen=True)
class RuntimeSettings:
    """Server runtime settings."""

    simulate_url: str
    day_sleep_seconds: float
    default_lang: str
    default_time_zone: str
    default_country: str
    test_env: EnvironmentConnectionConfig
    preprod_env: EnvironmentConnectionConfig


@lru_cache(maxsize=1)
def get_settings() -> RuntimeSettings:
    """Load runtime settings, preferring environment variables."""
    default_mongo_db = os.getenv("RUNZO_MONGO_DB", "echo")
    default_collection = os.getenv("RUNZO_MONGO_COLLECTION", "runzo_training_daily")
    return RuntimeSettings(
        simulate_url=os.getenv("RUNZO_SIMULATE_URL", "http://113.44.60.56:8001/simulate"),
        day_sleep_seconds=float(os.getenv("RUNZO_DAY_SLEEP_SECONDS", "0.2")),
        default_lang=os.getenv("RUNZO_DEFAULT_LANG", "zh_CN"),
        default_time_zone=os.getenv("RUNZO_DEFAULT_TIME_ZONE", "Asia/Shanghai"),
        default_country=os.getenv("RUNZO_DEFAULT_COUNTRY", "CN"),
        test_env=EnvironmentConnectionConfig(
            code=RuntimeEnvironment.TEST,
            name="测试环境",
            mongo_uri=os.getenv(
                "RUNZO_TEST_MONGO_URI",
                "mongodb://rwuser:Z3jaDyu*c!ZVKm*GBgpb@1.94.8.122:8004/echo?authSource=admin&directConnection=true",
            ),
            mongo_db=os.getenv("RUNZO_TEST_MONGO_DB", default_mongo_db),
            mongo_collection=os.getenv("RUNZO_TEST_MONGO_COLLECTION", default_collection),
            settle_url=os.getenv(
                "RUNZO_TEST_SETTLE_URL",
                "https://tsapiv1-test.shasoapp.com/turing-runner//runzo/settlement/watch-settle",
            ),
        ),
        preprod_env=EnvironmentConnectionConfig(
            code=RuntimeEnvironment.PREPROD,
            name="预发布环境",
            mongo_uri=os.getenv(
                "RUNZO_PREPROD_MONGO_URI",
                "mongodb://rwuser:hYEB%3D%23y3tyiZyYex2C0M@123.60.41.195:8635/echo?authSource=admin&directConnection=true",
            ),
            mongo_db=os.getenv("RUNZO_PREPROD_MONGO_DB", "rework"),
            mongo_collection=os.getenv("RUNZO_PREPROD_MONGO_COLLECTION", default_collection),
            settle_url=os.getenv(
                "RUNZO_PREPROD_SETTLE_URL",
                "https://tsapiv1.shasoapp.com/turing-runner//runzo/settlement/watch-settle",
            ),
        ),
    )


def get_environment_connection_config(environment: RuntimeEnvironment) -> EnvironmentConnectionConfig:
    """Return connection settings for the given environment code."""
    settings = get_settings()
    if environment == RuntimeEnvironment.PREPROD:
        return settings.preprod_env
    return settings.test_env
