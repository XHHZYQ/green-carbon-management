"""实时数据模拟采集。

调度器周期调用（默认 15 秒），为每个测点写入一条新的采集数据，使实时监控
总览的实时曲线、组态图/平面图上的测点数值随时间变化。

- 模拟量：在量程内以当前值为中心做小幅随机游走；
- 累积量（电量、运行时长等）：只增不减；
- 首次启动时若测点近 1 小时数据过少（如长时间未运行），按 1 分钟粒度补齐，
  保证实时曲线不会出现空白。
"""

import logging
import random
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import SessionLocal
from app.models.dev import DevData, DevPoint

logger = logging.getLogger("scheduler")

# 累积量测点单位（此类测点按单调递增模拟）
CUMULATIVE_UNITS = {"kWh", "m³", "L", "t", "GJ", "h", "次"}

# 补齐数据的时间范围（分钟）与触发补齐的最小近期数据条数
CATCH_UP_MINUTES = 60
MIN_RECENT_ROWS = 10


def _next_value(lo: float, hi: float, prev: float | None, cumulative: bool) -> float:
    span = hi - lo
    if prev is None:
        prev = lo + span * random.uniform(0.3, 0.6)
    elif cumulative:
        return round(prev + max(span * 0.00002, 0.005) * random.uniform(0.2, 1.5), 3)
    step = span * 0.01
    return round(min(max(prev + random.uniform(-step, step), lo), hi), 3)


def _row(point: DevPoint, value: float, ts: datetime) -> DevData:
    return DevData(
        device_id=point.device_id,
        point_id=point.id,
        collect_value=value,
        unit=point.unit,
        data_quality="normal",
        collect_time=ts,
    )


async def _latest_map(session: AsyncSession, point_ids: list[int]) -> dict[int, DevData]:
    """取每测点最新一条采集数据。"""
    if not point_ids:
        return {}
    stmt = (
        select(DevData)
        .where(DevData.point_id.in_(point_ids))
        .distinct(DevData.point_id)
        .order_by(DevData.point_id, DevData.collect_time.desc())
    )
    return {r.point_id: r for r in (await session.execute(stmt)).scalars().all()}


async def _recent_counts(session: AsyncSession, point_ids: list[int], since: datetime) -> dict[int, int]:
    """统计各测点在指定时间之后的采集条数。"""
    if not point_ids:
        return {}
    stmt = (
        select(DevData.point_id, func.count())
        .where(DevData.point_id.in_(point_ids), DevData.collect_time >= since)
        .group_by(DevData.point_id)
    )
    return {pid: cnt for pid, cnt in (await session.execute(stmt)).all()}


async def simulate_collect(catch_up: bool = False) -> int:
    """为全部测点写入采集数据，返回写入条数。

    catch_up 为 True 时，对近 CATCH_UP_MINUTES 分钟数据过少的测点，
    按 1 分钟粒度补齐，避免实时曲线出现空白。
    """
    async with SessionLocal() as session:
        points = (await session.execute(select(DevPoint))).scalars().all()
        if not points:
            return 0
        point_ids = [p.id for p in points]
        latest = await _latest_map(session, point_ids)
        now = datetime.now().astimezone()
        counts = await _recent_counts(session, point_ids, now - timedelta(minutes=CATCH_UP_MINUTES)) if catch_up else {}
        rows: list[DevData] = []
        for p in points:
            lo, hi = float(p.range_min or 0), float(p.range_max or 100)
            cumulative = (p.unit or "") in CUMULATIVE_UNITS
            row = latest.get(p.id)
            prev = float(row.collect_value) if row and row.collect_value is not None else None

            if catch_up and counts.get(p.id, 0) < MIN_RECENT_ROWS:
                t = (now - timedelta(minutes=CATCH_UP_MINUTES)).replace(second=0, microsecond=0)
                while t < now - timedelta(seconds=30):
                    prev = _next_value(lo, hi, prev, cumulative)
                    rows.append(_row(p, prev, t))
                    t += timedelta(minutes=1)

            prev = _next_value(lo, hi, prev, cumulative)
            rows.append(_row(p, prev, now))

        session.add_all(rows)
        await session.commit()
        return len(rows)
