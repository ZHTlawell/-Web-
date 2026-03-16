"""MongoDB training plan reader."""

from __future__ import annotations

from typing import Any, Optional

from pymongo import MongoClient

from app.models.runzo import RunzoTaskParams
from app.services.payload_builder_service import stringify_object_id
from app.services.settings import EnvironmentConnectionConfig, RuntimeSettings


class MongoTrainingPlanService:
    """Read and filter training plans from MongoDB."""

    def __init__(self, settings: RuntimeSettings):
        self._settings = settings

    def fetch_training_plans(
        self,
        params: RunzoTaskParams,
        processed_ids: set[str],
        last_completed_day_start_time: Optional[int],
        env_config: EnvironmentConnectionConfig,
    ) -> list[dict[str, Any]]:
        """Read executable training plans for the current task."""
        client = MongoClient(env_config.mongo_uri)
        try:
            collection = client[env_config.mongo_db][env_config.mongo_collection]
            documents = list(collection.find({"createBy": params.query_create_by}))
        finally:
            client.close()

        min_day_start_time = (
            int(params.start_from_day_start_time) if params.start_from_day_start_time is not None else None
        )
        if last_completed_day_start_time is not None:
            next_min = last_completed_day_start_time + 1
            min_day_start_time = max(min_day_start_time, next_min) if min_day_start_time is not None else next_min

        results: list[dict[str, Any]] = []
        for document in documents:
            if document.get("trainingType") == "Rest":
                continue

            daily_id = stringify_object_id(document.get("_id"))
            if daily_id in processed_ids:
                continue

            if "dayStartTime" not in document or document.get("dayStartTime") is None:
                raise RuntimeError(f"发现缺少 dayStartTime 的训练计划: dailyId={daily_id}")

            day_start_time = int(document["dayStartTime"])
            if min_day_start_time is not None and day_start_time < min_day_start_time:
                continue

            results.append(document)

        results.sort(key=lambda item: int(item["dayStartTime"]))
        return results
