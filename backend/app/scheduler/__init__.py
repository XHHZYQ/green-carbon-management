"""APScheduler 调度器（任务注册中心）。

调度器负责注册周期任务：心跳、实时数据模拟采集，后续批次再接入定时控制、
告警检测、报表订阅等。
"""

import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.services.collect_sim import simulate_collect
from app.services.control_service import drive_commands, run_due_timed_tasks
from app.services.scene_service import evaluate_link_rules, run_due_scene_schedules

logger = logging.getLogger("scheduler")

scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")

# job_id -> 任务说明
REGISTERED_JOBS: dict[str, str] = {}

# 实时数据模拟采集周期（秒）
COLLECT_SIM_INTERVAL_SEC = 15

# 控制指令状态流转周期（秒）
CONTROL_EXEC_INTERVAL_SEC = 2

# 定时控制任务检查周期（秒）
CONTROL_TIMED_INTERVAL_SEC = 10

# 场景定时执行检查周期（秒）
SCENE_TIMED_INTERVAL_SEC = 10

# 联动规则评估周期（秒）
SCENE_LINK_INTERVAL_SEC = 20

# 是否为首次模拟采集（首次需补齐过期数据）
_first_collect = True


async def _heartbeat() -> None:
    """心跳任务：占位，便于验证调度器工作正常。"""
    logger.debug("scheduler heartbeat")


async def _collect_sim() -> None:
    """模拟采集任务：为全部测点写入一条新数据（首次补齐过期数据）。"""
    global _first_collect
    try:
        count = await simulate_collect(catch_up=_first_collect)
        _first_collect = False
        logger.debug("模拟采集写入 %s 条", count)
    except Exception:  # noqa: BLE001
        logger.exception("模拟采集任务执行失败")


async def _control_exec() -> None:
    """控制指令状态流转：待下发 → 下发中 → 成功/失败/超时。"""
    try:
        await drive_commands()
    except Exception:  # noqa: BLE001
        logger.exception("控制指令状态流转失败")


async def _control_timed() -> None:
    """定时控制任务到点下发。"""
    try:
        count = await run_due_timed_tasks()
        if count:
            logger.debug("定时控制下发 %s 条", count)
    except Exception:  # noqa: BLE001
        logger.exception("定时控制任务下发失败")


async def _scene_timed() -> None:
    """场景定时任务到点执行。"""
    try:
        count = await run_due_scene_schedules()
        if count:
            logger.debug("场景定时执行 %s 个", count)
    except Exception:  # noqa: BLE001
        logger.exception("场景定时执行失败")


async def _scene_link() -> None:
    """联动规则命中自动执行。"""
    try:
        count = await evaluate_link_rules()
        if count:
            logger.debug("联动规则命中执行 %s 条", count)
    except Exception:  # noqa: BLE001
        logger.exception("联动规则评估失败")


def register_jobs() -> None:
    """注册内置周期任务。"""
    if not scheduler.get_job("heartbeat"):
        scheduler.add_job(
            _heartbeat,
            trigger=IntervalTrigger(seconds=60),
            id="heartbeat",
            replace_existing=True,
        )
        REGISTERED_JOBS["heartbeat"] = "调度器心跳"

    if not scheduler.get_job("collect_sim"):
        scheduler.add_job(
            _collect_sim,
            trigger=IntervalTrigger(seconds=COLLECT_SIM_INTERVAL_SEC),
            id="collect_sim",
            replace_existing=True,
            next_run_time=datetime.now(),  # 启动即执行一次
        )
        REGISTERED_JOBS["collect_sim"] = "实时数据模拟采集"

    if not scheduler.get_job("control_exec"):
        scheduler.add_job(
            _control_exec,
            trigger=IntervalTrigger(seconds=CONTROL_EXEC_INTERVAL_SEC),
            id="control_exec",
            replace_existing=True,
        )
        REGISTERED_JOBS["control_exec"] = "控制指令状态流转"

    if not scheduler.get_job("control_timed"):
        scheduler.add_job(
            _control_timed,
            trigger=IntervalTrigger(seconds=CONTROL_TIMED_INTERVAL_SEC),
            id="control_timed",
            replace_existing=True,
        )
        REGISTERED_JOBS["control_timed"] = "定时控制任务下发"

    if not scheduler.get_job("scene_timed"):
        scheduler.add_job(
            _scene_timed,
            trigger=IntervalTrigger(seconds=SCENE_TIMED_INTERVAL_SEC),
            id="scene_timed",
            replace_existing=True,
        )
        REGISTERED_JOBS["scene_timed"] = "场景定时执行"

    if not scheduler.get_job("scene_link"):
        scheduler.add_job(
            _scene_link,
            trigger=IntervalTrigger(seconds=SCENE_LINK_INTERVAL_SEC),
            id="scene_link",
            replace_existing=True,
        )
        REGISTERED_JOBS["scene_link"] = "联动规则评估执行"


def start_scheduler() -> None:
    register_jobs()
    if not scheduler.running:
        scheduler.start()
        logger.info("调度器已启动，任务数：%s", len(scheduler.get_jobs()))


def shutdown_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("调度器已停止")
