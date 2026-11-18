"""APScheduler 调度器（任务注册中心）。

B1 阶段仅提供调度器骨架与内置任务注册表，后续批次在 register_jobs 中接入
采集、定时控制、告警检测、报表订阅等周期性任务。
"""

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger("scheduler")

scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")

# job_id -> 任务说明
REGISTERED_JOBS: dict[str, str] = {}


async def _heartbeat() -> None:
    """心跳任务：占位，便于验证调度器工作正常。"""
    logger.debug("scheduler heartbeat")


def register_jobs() -> None:
    """注册内置周期任务（B1 仅心跳，后续批次扩展）。"""
    if not scheduler.get_job("heartbeat"):
        scheduler.add_job(
            _heartbeat,
            trigger=IntervalTrigger(seconds=60),
            id="heartbeat",
            replace_existing=True,
        )
        REGISTERED_JOBS["heartbeat"] = "调度器心跳"


def start_scheduler() -> None:
    register_jobs()
    if not scheduler.running:
        scheduler.start()
        logger.info("调度器已启动，任务数：%s", len(scheduler.get_jobs()))


def shutdown_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("调度器已停止")
