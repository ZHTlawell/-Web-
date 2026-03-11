#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Runzo 造训练数据 + 结算脚本（单用户 · MongoDB 动态读取版 · dayStartTime 排序 + 人工确认 + 断点起跑）

本次改动（针对你的要求）：
✅ 彻底避免“被系统代理转发到 127.0.0.1:9090”：
   - requests.Session().trust_env = False（不读取 HTTP_PROXY/HTTPS_PROXY/ALL_PROXY 等环境变量）
✅ 下次运行从指定 dayStartTime 开始往后执行：
   - START_FROM_DAY_START_TIME = 1771430400000 （包含该时间点）

# 运行进度锚点：防止“计划重算导致 _id 变化”时回头跑旧周
LAST_DONE_DAY_START_TIME = None  # 会在运行中自动更新
✅ 其余逻辑保持不变：
   - MongoDB 读取 echo.runzo_training_daily（createBy=89947197695000195）
   - 过滤 Rest
   - 严格按 dayStartTime(Int64) 升序
   - 每周结束人工确认后重新读取最新计划
   - 第一次跑完 Easy/LSD、Threshold、Interval 各一次后人工确认

依赖：
  pip install requests pymongo
"""

from __future__ import annotations

import copy
import json
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import requests
from pymongo import MongoClient


# ================= 固定配置 =================
USER_ID = "92114529545000186"
AUTHORIZATION = "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJsb2dpblR5cGUiOiJsb2dpbiIsImxvZ2luSWQiOiI5MTUwMTM3MzY5NjAwMDEwMyIsInJuU3RyIjoienlVeU5JTUFyMzVDUWI5QlpSblFieFdOWFpOZHFqUzkiLCJlZmYiOjE3NzQ1MDUwMzM3MTIsImFwcE5hbWUiOiJSdW5uZXJBSSJ9.FLWkI7X4zMWDN3uhOM8JVEMFv7aZ3GkZDP2Q9AOZtcg"  # ⚠️ 替换为真实 token（纯英文/数字，别带换行）
LAST_DONE_DAY_START_TIME = None

USER_DATA = {
    "gender": "male",
    "age": 22,
    "weight": 75,
    "height": 175,
    "hrMax": 198,
    "hrRest": 65,
    "targetDistance": 5,
    "intensityPreference": "medium",
}

# 断点起跑：只执行 dayStartTime >= 该值的训练
START_FROM_DAY_START_TIME = 1773676800000

# MongoDB
MONGO_URI = "mongodb://rwuser:Z3jaDyu*c!ZVKm*GBgpb@1.94.8.122:8004/echo?authSource=admin&directConnection=true"
MONGO_DB = "echo"
MONGO_COLLECTION = "runzo_training_daily"
MONGO_QUERY = {"createBy": "92114529545000186"}

OUT_DIR = "out_runzo_single_user"

SIMULATE_URL = "http://113.44.60.56:8001/simulate"
SETTLE_URL = "https://tsapiv1-test.shasoapp.com/turing-runner//runzo/settlement/watch-settle"

DAY_SLEEP_SECONDS = 0.2


# ================= 工具函数 =================
def assert_headers_latin1(headers: Dict[str, Any]):
    bad = []
    for k, v in headers.items():
        try:
            str(v).encode("latin-1")
        except UnicodeEncodeError:
            bad.append((k, v))
    if bad:
        msg = "\n".join([f"{k}={v!r}" for k, v in bad])
        raise ValueError(
            "请求头包含非英文字符，requests 无法发送（必须 latin-1 可编码）。\n"
            "请检查 Authorization / 其他 header（不要中文、不要换行）。\n"
            f"非法 header:\n{msg}"
        )


def wait_user_confirm(tip: str):
    print("\n" + "=" * 70)
    print(tip)
    # 临时关闭人工确认：仅打印提示，不阻塞等待输入
    if input(">>> ").strip().lower() != "y":
        print("⛔ 已人工终止执行")
        raise SystemExit(0)
    print("✅ 继续执行...\n")
    # print("⚠️ 已跳过人工确认（临时关闭确认机制）")
    # print("✅ 自动继续执行...\n")


def to_oid_str(x: Any) -> str:
    return str(x)


def detect_week_field(cycle: List[Dict[str, Any]]) -> Optional[str]:
    for d in cycle:
        if "weekIndex" in d and d.get("weekIndex") is not None:
            return "weekIndex"
    return None


def get_week(daily: Dict[str, Any], week_field: Optional[str]) -> int:
    if week_field:
        return int(daily.get(week_field))
    return -1


# ================= Mongo 读取（dayStartTime 排序 + 断点起跑） =================
def fetch_cycle_from_mongo(processed_ids: Set[str], last_done_day_start_time: Optional[int]) -> List[Dict[str, Any]]:
    """
    - 过滤 Rest
    - 过滤已执行 _id（processed_ids）
    - 过滤 dayStartTime < START_FROM_DAY_START_TIME（断点起跑）
    - 严格按 dayStartTime(Int64) 升序排序
    """
    client = MongoClient(MONGO_URI)
    try:
        col = client[MONGO_DB][MONGO_COLLECTION]
        docs = list(col.find(MONGO_QUERY))
    finally:
        client.close()

    # 断点过滤下限：优先使用 last_done_day_start_time（防止 _id 变化导致回跑）


    min_dst = None


    if START_FROM_DAY_START_TIME is not None:


        min_dst = int(START_FROM_DAY_START_TIME)


    if last_done_day_start_time is not None:


        # 下一条必须严格大于上一条完成的 dayStartTime


        min_dst = max(min_dst or (last_done_day_start_time + 1), last_done_day_start_time + 1)



    out: List[Dict[str, Any]] = []
    for d in docs:
        if d.get("trainingType") == "Rest":
            continue

        did = to_oid_str(d.get("_id"))
        if did in processed_ids:
            continue

        if "dayStartTime" not in d or d.get("dayStartTime") is None:
            raise RuntimeError(f"❌ 发现缺少 dayStartTime 的训练计划: dailyId={did}")

        dst = int(d["dayStartTime"])
        if dst < START_FROM_DAY_START_TIME:
            continue

        out.append(d)

    out.sort(key=lambda x: int(x["dayStartTime"]))
    return out


# ================= simulate payload =================
def pace(block: Dict[str, Any]):
    return str(block.get("minPace", "0:00")), str(block.get("maxPace", "0:00"))


def build_simulate_payload(daily: Dict[str, Any]) -> Dict[str, Any]:
    ttype = daily["trainingType"]
    blocks = daily.get("trainingBlocks", []) or []
    distance = float(daily.get("runningDistance", 0) or 0)

    base = {"userData": copy.deepcopy(USER_DATA), "trainingPlan": {}, "stateDescription": ""}

    if ttype == "Easy":
        mn, mx = pace(blocks[0])
        base["trainingPlan"] = {
            "trainingType": "Easy",
            "targetDistance": distance,
            "phasePace": {"main": {"min": mn, "max": mx}},
        }

    elif ttype == "LSD":
        mn, mx = pace(blocks[0])
        base["trainingPlan"] = {
            "trainingType": "LSD",
            "targetDistance": distance,
            "phasePace": {"main": {"min": mn, "max": mx}, "rest": {"min": mn, "max": mx}},
        }

    elif ttype == "Threshold":
        wmn, wmx = pace(blocks[0])
        mmn, mmx = pace(blocks[1])
        base["trainingPlan"] = {
            "trainingType": "Threshold",
            "targetDistance": distance,
            "phasePace": {
                "warmup": {"min": wmn, "max": wmx},
                "main": {"min": mmn, "max": mmx},
                "rest": {"min": wmn, "max": wmx},
            },
            "phaseDistance": {
                "warmup": float(blocks[0].get("distance", 0) or 0),
                "main": float(blocks[1].get("distance", 0) or 0),
                "rest": 0.1,
            },
        }

    elif ttype == "Interval":
        base["trainingPlan"] = {
            "trainingType": "Interval",
            "targetDistance": distance,
            "trainingBlocks": blocks,
        }

    else:
        raise ValueError(f"不支持的训练类型: {ttype}")

    return base


def post(session: requests.Session, url: str, payload: Dict[str, Any], headers: Optional[Dict[str, str]] = None):
    # 分离连接/读取超时：连接 10s，读取 180s（避免偶发生成慢）
    r = session.post(url, json=payload, headers=headers, timeout=(10, 180))
    if r.status_code >= 400:
        raise RuntimeError(f"{url} failed ({r.status_code}): {r.text}")
    return r.json()


# ================= 主流程 =================
def main():
    global LAST_DONE_DAY_START_TIME
    base_headers = {
        "ts-user-id": USER_ID,
        "Authorization": AUTHORIZATION,
        "lang": "zh_CN",
        "ts-time-zone-id": "Asia/Shanghai",
        "ts-country": "CN",
    }
    assert_headers_latin1(base_headers)

    out = Path(OUT_DIR) / USER_ID
    out.mkdir(parents=True, exist_ok=True)

    processed_ids: Set[str] = set()

    cycle = fetch_cycle_from_mongo(processed_ids, LAST_DONE_DAY_START_TIME)
    if not cycle:
        raise SystemExit(
            f"❌ MongoDB 未查到任何可执行训练计划（可能都 < {START_FROM_DAY_START_TIME} 或已被过滤）"
        )

    week_field = detect_week_field(cycle)
    print(f"Week field detected: {week_field or 'None'}")
    print(f"Start from dayStartTime >= {START_FROM_DAY_START_TIME}")
    print(f"Loaded items: {len(cycle)}")

    seen_easy_lsd = False
    seen_threshold = False
    seen_interval = False
    first_round_confirmed = False

    with requests.Session() as s:
        # ✅ 关键：不读取系统代理环境变量，避免被转发到 127.0.0.1:9090
        s.trust_env = False

        while cycle:
            daily = cycle.pop(0)
            daily_id = to_oid_str(daily["_id"])
            ttype = daily["trainingType"]
            daily_week = get_week(daily, week_field)
            dst = int(daily["dayStartTime"])

            simulate_payload = build_simulate_payload(daily)
            (out / f"{dst}_{daily_id}_{ttype}_simulate_request.json").write_text(
                json.dumps(simulate_payload, ensure_ascii=False, indent=2), encoding="utf-8"
            )

            simulate_resp = post(s, SIMULATE_URL, simulate_payload)
            (out / f"{dst}_{daily_id}_{ttype}_simulate.json").write_text(
                json.dumps(simulate_resp, ensure_ascii=False, indent=2), encoding="utf-8"
            )

            settle_payload = dict(simulate_resp, dailyId=daily_id, userId=USER_ID)
            headers = dict(base_headers, **{"ts-request-id": str(uuid.uuid4())})
            settle_resp = post(s, SETTLE_URL, settle_payload, headers)

            # (out / f"{dst}_{daily_id}_{ttype}_settle.json").write_text(
            #     json.dumps(settle_resp, ensure_ascii=False, indent=2), encoding="utf-8"
            # )

            print(f"dayStartTime={dst} Week={daily_week} {ttype} dailyId={daily_id} ✅")
            processed_ids.add(daily_id)
            LAST_DONE_DAY_START_TIME = dst

            # 首次三类训练都完成后确认
            if not first_round_confirmed:
                if ttype in ("Easy", "LSD"):
                    seen_easy_lsd = True
                elif ttype == "Threshold":
                    seen_threshold = True
                elif ttype == "Interval":
                    seen_interval = True
                if seen_easy_lsd and seen_threshold and seen_interval:
                    wait_user_confirm("已完成 Easy/LSD、Threshold、Interval 各一次，是否继续？")
                    first_round_confirmed = True

            # 周切换确认：下一条 weekIndex 变化即认为本周结束
            next_week = get_week(cycle[0], week_field) if cycle else None
            if next_week != daily_week:
                wait_user_confirm(
                    f"第 {daily_week} 周训练完成，是否继续下一周？（将重新读取 Mongo 最新计划）"
                )
                cycle = fetch_cycle_from_mongo(processed_ids, LAST_DONE_DAY_START_TIME)
                week_field = detect_week_field(cycle)
                print(f"🔄 Reloaded. Remaining: {len(cycle)} | Week field: {week_field or 'None'}")

            time.sleep(DAY_SLEEP_SECONDS)


if __name__ == "__main__":
    main()
