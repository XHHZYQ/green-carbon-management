"""能耗域服务（B5-1 能耗管理：总览/分析/分项/峰谷/排名/成本/导出）。"""

from datetime import date, datetime, time, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.carbon import CarbonEmission
from app.models.cfg import CfgEnergyItem, CfgEnergyType
from app.models.dev import DevArea, DevDevice
from app.models.energy import EnergyFeeStat, EnergyStat
from app.services.price_service import PERIOD_NAMES, hour_period

# 24 小时负荷权重（用于小时级分布与峰谷拆分，代码内归一化）
HOUR_WEIGHTS = [
    0.012, 0.010, 0.009, 0.009, 0.009, 0.010, 0.015, 0.028,
    0.048, 0.058, 0.060, 0.062, 0.045, 0.050, 0.058, 0.060,
    0.058, 0.052, 0.040, 0.035, 0.032, 0.028, 0.020, 0.015,
]
HOUR_SHARE = [w / sum(HOUR_WEIGHTS) for w in HOUR_WEIGHTS]


def _dt(d: date) -> datetime:
    """日期 -> 当日 00:00:00（带本地时区）。"""
    return datetime.combine(d, time.min).astimezone()


def _month_start(d: date) -> date:
    return d.replace(day=1)


def _add_months(d: date, n: int) -> date:
    y, m = d.year, d.month + n
    y += (m - 1) // 12
    m = (m - 1) % 12 + 1
    return date(y, m, 1)


def _bounds(start: date | None, end: date | None) -> tuple[datetime, datetime, date, date]:
    """归一化时间范围，返回 [start_dt, end_dt) 与起止日期（含）。"""
    today = date.today()
    end = end or today
    start = start or _month_start(end)
    return _dt(start), _dt(end + timedelta(days=1)), start, end


async def _maps(session: AsyncSession) -> tuple[dict[str, int], dict[int, str], dict[int, str], dict[int, str]]:
    types = (await session.execute(select(CfgEnergyType))).scalars().all()
    items = (await session.execute(select(CfgEnergyItem))).scalars().all()
    areas = (await session.execute(select(DevArea))).scalars().all()
    type_ids = {t.type_code: t.id for t in types}
    item_names = {i.id: i.item_name for i in items}
    area_names = {a.id: a.area_name for a in areas}
    type_names = {t.id: t.type_name for t in types}
    return type_ids, item_names, area_names, type_names


def _sum_value(session: AsyncSession, start_dt, end_dt, energy_type_id=None, stat_type="day"):
    stmt = select(func.coalesce(func.sum(EnergyStat.stat_value), 0)).where(
        EnergyStat.stat_type == stat_type,
        EnergyStat.device_id.is_(None),
        EnergyStat.stat_time >= start_dt,
        EnergyStat.stat_time < end_dt,
    )
    if energy_type_id is not None:
        stmt = stmt.where(EnergyStat.energy_type_id == energy_type_id)
    return stmt


async def _scalar(session: AsyncSession, stmt) -> float:
    return float((await session.execute(stmt)).scalar_one() or 0)


# ==================== 总览 ====================


async def overview(session: AsyncSession) -> dict:
    type_ids, _, area_names, type_names = await _maps(session)
    ele = type_ids.get("electricity")
    today = date.today()
    tm_start, tm_end, _, _ = _bounds(_month_start(today), today)
    lm_start, lm_end, _, _ = _bounds(_add_months(_month_start(today), -1), _month_start(today) - timedelta(days=1))
    ly_start, ly_end, _, _ = _bounds(_add_months(_month_start(today), -12), _add_months(_month_start(today), -11) - timedelta(days=1))
    td_start, td_end, _, _ = _bounds(today, today)

    month_energy = await _scalar(session, _sum_value(session, tm_start, tm_end, ele))
    last_month_energy = await _scalar(session, _sum_value(session, lm_start, lm_end, ele))
    last_year_energy = await _scalar(session, _sum_value(session, ly_start, ly_end, ele))
    today_energy = await _scalar(session, _sum_value(session, td_start, td_end, ele))

    month_fee = await _scalar(
        session,
        select(func.coalesce(func.sum(EnergyFeeStat.fee_value), 0)).where(
            EnergyFeeStat.stat_type == "month",
            EnergyFeeStat.area_id.is_(None),
            EnergyFeeStat.energy_item_id.is_(None),
        ),
    )
    month_carbon = await _scalar(
        session,
        select(func.coalesce(func.sum(CarbonEmission.emission_value), 0)).where(
            CarbonEmission.period_type == "month",
            CarbonEmission.area_id.is_(None),
            CarbonEmission.period_value == f"{today:%Y-%m}",
        ),
    )

    # 近 30 天日趋势
    t_start, t_end, _, _ = _bounds(today - timedelta(days=29), today)
    mmdd_expr = func.to_char(EnergyStat.stat_time, "MM-DD")
    trend_rows = (
        await session.execute(
            select(
                mmdd_expr,
                func.coalesce(func.sum(EnergyStat.stat_value), 0),
            )
            .where(
                EnergyStat.stat_type == "day",
                EnergyStat.device_id.is_(None),
                EnergyStat.energy_type_id == ele,
                EnergyStat.stat_time >= t_start,
                EnergyStat.stat_time < t_end,
            )
            .group_by(mmdd_expr, EnergyStat.stat_time)
            .order_by(EnergyStat.stat_time)
        )
    ).all()

    # 当月能源类型构成
    type_rows = (
        await session.execute(
            select(
                CfgEnergyType.type_name,
                func.coalesce(func.sum(EnergyStat.stat_value), 0),
            )
            .join(CfgEnergyType, CfgEnergyType.id == EnergyStat.energy_type_id)
            .where(
                EnergyStat.stat_type == "day",
                EnergyStat.device_id.is_(None),
                EnergyStat.stat_time >= tm_start,
                EnergyStat.stat_time < tm_end,
            )
            .group_by(CfgEnergyType.type_name)
        )
    ).all()

    # 当月区域排名（电量）
    area_rows = (
        await session.execute(
            select(
                EnergyStat.area_id,
                func.coalesce(func.sum(EnergyStat.stat_value), 0),
            )
            .where(
                EnergyStat.stat_type == "day",
                EnergyStat.device_id.is_(None),
                EnergyStat.energy_type_id == ele,
                EnergyStat.area_id.is_not(None),
                EnergyStat.stat_time >= tm_start,
                EnergyStat.stat_time < tm_end,
            )
            .group_by(EnergyStat.area_id)
        )
    ).all()
    area_rank = sorted(
        [{"name": area_names.get(r[0], "-"), "value": round(float(r[1]), 2)} for r in area_rows],
        key=lambda x: x["value"],
        reverse=True,
    )

    def _rate(cur: float, base: float) -> float | None:
        if not base:
            return None
        return round((cur - base) / base * 100, 2)

    return {
        "cards": {
            "month_energy": round(month_energy, 2),
            "month_fee": round(month_fee, 2),
            "month_carbon": round(month_carbon, 2),
            "today_energy": round(today_energy, 2),
            "mom_rate": _rate(month_energy, last_month_energy),
            "yoy_rate": _rate(month_energy, last_year_energy),
        },
        "trend": {
            "dates": [r[0] for r in trend_rows],
            "values": [round(float(r[1]), 2) for r in trend_rows],
        },
        "type_ratio": [
            {"name": r[0], "value": round(float(r[1]), 2)} for r in type_rows if float(r[1]) > 0
        ],
        "area_rank": area_rank[:8],
    }


# ==================== 分析（区域/分项/设备） ====================


async def analysis(session: AsyncSession, dim: str = "area", start: date | None = None, end: date | None = None) -> list[dict]:
    type_ids, item_names, area_names, _ = await _maps(session)
    ele = type_ids.get("electricity")
    start_dt, end_dt, _, _ = _bounds(start, end)

    if dim == "item":
        col = EnergyStat.energy_item_id
        name_map = item_names
        extra = EnergyStat.energy_item_id.is_not(None)
    elif dim == "device":
        col = EnergyStat.device_id
        extra = EnergyStat.device_id.is_not(None)
        name_map = {
            d.id: d.device_name
            for d in (await session.execute(select(DevDevice))).scalars().all()
        }
    else:
        col = EnergyStat.area_id
        name_map = area_names
        extra = EnergyStat.area_id.is_not(None)

    stmt = (
        select(col, func.coalesce(func.sum(EnergyStat.stat_value), 0))
        .where(
            EnergyStat.stat_type == "day",
            EnergyStat.stat_time >= start_dt,
            EnergyStat.stat_time < end_dt,
            extra,
        )
        .group_by(col)
    )
    if dim != "device":
        stmt = stmt.where(EnergyStat.device_id.is_(None), EnergyStat.energy_type_id == ele)

    rows = (await session.execute(stmt)).all()
    data = [{"name": name_map.get(r[0], f"ID-{r[0]}"), "value": round(float(r[1]), 2)} for r in rows]
    data.sort(key=lambda x: x["value"], reverse=True)
    total = sum(x["value"] for x in data) or 1
    for x in data:
        x["ratio"] = round(x["value"] / total * 100, 2)
    return data


async def item_ratio(session: AsyncSession, start: date | None = None, end: date | None = None) -> list[dict]:
    type_ids, item_names, _, _ = await _maps(session)
    ele = type_ids.get("electricity")
    start_dt, end_dt, _, _ = _bounds(start, end)
    rows = (
        await session.execute(
            select(EnergyStat.energy_item_id, func.coalesce(func.sum(EnergyStat.stat_value), 0))
            .where(
                EnergyStat.stat_type == "day",
                EnergyStat.device_id.is_(None),
                EnergyStat.energy_type_id == ele,
                EnergyStat.energy_item_id.is_not(None),
                EnergyStat.stat_time >= start_dt,
                EnergyStat.stat_time < end_dt,
            )
            .group_by(EnergyStat.energy_item_id)
        )
    ).all()
    data = [{"name": item_names.get(r[0], "-"), "value": round(float(r[1]), 2)} for r in rows]
    data.sort(key=lambda x: x["value"], reverse=True)
    total = sum(x["value"] for x in data) or 1
    for x in data:
        x["ratio"] = round(x["value"] / total * 100, 2)
    return data


async def peak_valley(session: AsyncSession, start: date | None = None, end: date | None = None) -> list[dict]:
    """按最高效方式：用日统计 × 负荷曲线拆分到峰谷时段，避免依赖小时数据。"""
    type_ids, _, _, _ = await _maps(session)
    ele = type_ids.get("electricity")
    start_dt, end_dt, _, _ = _bounds(start, end)
    total_energy = await _scalar(session, _sum_value(session, start_dt, end_dt, ele))

    # 汇总电价（标准分时价，来自生效方案）
    from app.services.price_service import STANDARD_PRICES

    buckets: dict[str, dict] = {}
    for hour in range(24):
        ptype = hour_period(hour)
        b = buckets.setdefault(ptype, {"usage": 0.0, "weight": 0.0})
        b["weight"] += HOUR_SHARE[hour]

    result = []
    for ptype, b in buckets.items():
        usage = total_energy * b["weight"]
        price = float(STANDARD_PRICES.get(ptype, 0))
        result.append(
            {
                "period_type": ptype,
                "period_name": PERIOD_NAMES.get(ptype, ptype),
                "usage": round(usage, 2),
                "price": price,
                "fee": round(usage * price, 2),
            }
        )
    order = {"sharp": 0, "peak": 1, "flat": 2, "valley": 3}
    result.sort(key=lambda x: order.get(x["period_type"], 9))
    total_fee = sum(x["fee"] for x in result) or 1
    for x in result:
        x["fee_ratio"] = round(x["fee"] / total_fee * 100, 2)
    return result


async def rank(session: AsyncSession, dim: str = "area", start: date | None = None, end: date | None = None, limit: int = 10) -> list[dict]:
    data = await analysis(session, dim, start, end)
    data = data[:limit]
    for idx, x in enumerate(data, start=1):
        x["rank"] = idx
    return data


async def cost(session: AsyncSession, months: int = 6) -> dict:
    """能耗成本：按月趋势 + 分时费用构成。"""
    today = date.today()
    start = _add_months(_month_start(today), -(months - 1))
    start_dt, end_dt, _, _ = _bounds(start, today)
    ym_expr = func.to_char(EnergyStat.stat_time, "YYYY-MM")

    rows = (
        await session.execute(
            select(
                ym_expr,
                func.coalesce(func.sum(EnergyStat.stat_value), 0),
            )
            .join(CfgEnergyType, CfgEnergyType.id == EnergyStat.energy_type_id)
            .where(
                EnergyStat.stat_type == "day",
                EnergyStat.device_id.is_(None),
                CfgEnergyType.type_code == "electricity",
                EnergyStat.stat_time >= start_dt,
                EnergyStat.stat_time < end_dt,
            )
            .group_by(ym_expr)
            .order_by(ym_expr)
        )
    ).all()

    from app.services.price_service import STANDARD_PRICES

    avg_price = float(STANDARD_PRICES["flat"])
    trend = {
        "months": [r[0] for r in rows],
        "energy": [round(float(r[1]), 2) for r in rows],
        "fee": [round(float(r[1]) * avg_price, 2) for r in rows],
    }

    # 分时费用构成（最近一个月）
    pv = await peak_valley(session, _month_start(today), today)
    period_fee = [{"name": x["period_name"], "value": x["fee"]} for x in pv]
    return {"trend": trend, "period_fee": period_fee}


# ==================== 导出 ====================


async def export_energy(session: AsyncSession, start: date | None = None, end: date | None = None) -> bytes:
    import io

    from openpyxl import Workbook

    type_ids, item_names, area_names, type_names = await _maps(session)
    start_dt, end_dt, s_d, e_d = _bounds(start, end)
    rows = (
        await session.execute(
            select(EnergyStat)
            .where(
                EnergyStat.stat_type == "day",
                EnergyStat.device_id.is_(None),
                EnergyStat.stat_time >= start_dt,
                EnergyStat.stat_time < end_dt,
            )
            .order_by(EnergyStat.stat_time, EnergyStat.area_id)
            .limit(20000)
        )
    ).scalars().all()

    wb = Workbook()
    ws = wb.active
    ws.title = "能耗明细"
    ws.append(["日期", "能源类型", "分项", "区域", "能耗值", "单位"])
    for r in rows:
        ws.append([
            r.stat_time.strftime("%Y-%m-%d") if r.stat_time else "",
            type_names.get(r.energy_type_id, ""),
            item_names.get(r.energy_item_id, "") if r.energy_item_id else "",
            area_names.get(r.area_id, "") if r.area_id else "全园区",
            float(r.stat_value) if r.stat_value is not None else 0,
            r.unit or "",
        ])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
