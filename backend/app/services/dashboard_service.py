"""数据驾驶舱服务（B7）：指标卡与图表聚合（只读总览）。"""

from datetime import date, datetime, time, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alarm import AlarmInfo
from app.models.carbon import CarbonEmission
from app.models.cfg import CfgCarbonFactor, CfgEnergyItem, CfgEnergyType
from app.models.dev import DevArea, DevDevice
from app.models.energy import EnergyFeeStat, EnergyStat
from app.models.quota import QuotaMonitor

# 电力的默认碳因子（kgCO2e/kWh），当配置缺失时兜底
DEFAULT_ELE_FACTOR = 0.5703


def _dt(d: date) -> datetime:
    return datetime.combine(d, time.min).astimezone()


def _month_range(d: date) -> tuple[date, date]:
    """所在月区间（左闭右开）。"""
    first = d.replace(day=1)
    nxt = (first + timedelta(days=32)).replace(day=1)
    return first, nxt


async def _energy_type_id(session: AsyncSession, code: str) -> int | None:
    row = (
        await session.execute(select(CfgEnergyType).where(CfgEnergyType.type_code == code))
    ).scalars().first()
    return row.id if row else None


async def _ele_factor(session: AsyncSession, ele_id: int | None) -> float:
    """电力碳因子（kgCO2e/kWh）。"""
    if ele_id is not None:
        row = (
            await session.execute(
                select(CfgCarbonFactor).where(
                    CfgCarbonFactor.energy_type_id == ele_id, CfgCarbonFactor.status == 1
                )
            )
        ).scalars().first()
        if row and row.factor_value is not None:
            return float(row.factor_value)
    return DEFAULT_ELE_FACTOR


async def _sum_energy(
    session: AsyncSession, ele_id: int | None, start: datetime, end: datetime
) -> float:
    """园区级电力能耗（日统计，device_id 为空）。"""
    stmt = select(func.coalesce(func.sum(EnergyStat.stat_value), 0)).where(
        EnergyStat.stat_type == "day",
        EnergyStat.device_id.is_(None),
        EnergyStat.stat_time >= start,
        EnergyStat.stat_time < end,
    )
    if ele_id is not None:
        stmt = stmt.where(EnergyStat.energy_type_id == ele_id)
    return float((await session.execute(stmt)).scalar_one() or 0)


async def _sum_fee(session: AsyncSession, start: datetime, end: datetime) -> float:
    """园区级电力费用（日统计）。"""
    return float(
        (
            await session.execute(
                select(func.coalesce(func.sum(EnergyFeeStat.fee_value), 0)).where(
                    EnergyFeeStat.stat_type == "day",
                    EnergyFeeStat.area_id.is_(None),
                    EnergyFeeStat.energy_item_id.is_(None),
                    EnergyFeeStat.stat_time >= start,
                    EnergyFeeStat.stat_time < end,
                )
            )
        ).scalar_one()
        or 0
    )


async def _month_carbon(session: AsyncSession, ym: str) -> float:
    """指定月份园区碳排（tCO2e，来自 carbon_emission 月统计）。"""
    return float(
        (
            await session.execute(
                select(func.coalesce(func.sum(CarbonEmission.emission_value), 0)).where(
                    CarbonEmission.period_type == "month",
                    CarbonEmission.area_id.is_(None),
                    CarbonEmission.period_value == ym,
                )
            )
        ).scalar_one()
        or 0
    )


async def overview(session: AsyncSession) -> dict:
    """顶部指标卡：设备、在线、能耗、碳排、告警、费用、定额。"""
    today = date.today()
    ele = await _energy_type_id(session, "electricity")
    factor = await _ele_factor(session, ele)
    m_start, m_end = _month_range(today)
    t_start = _dt(today)
    t_end = t_start + timedelta(days=1)

    device_total = int((await session.execute(select(func.count(DevDevice.id)))).scalar_one() or 0)
    device_online = int(
        (
            await session.execute(
                select(func.count(DevDevice.id)).where(DevDevice.online_status == "online")
            )
        ).scalar_one()
        or 0
    )

    today_energy = await _sum_energy(session, ele, t_start, t_end)
    month_energy = await _sum_energy(session, ele, _dt(m_start), _dt(m_end))
    month_carbon = await _month_carbon(session, today.strftime("%Y-%m"))
    # 今日碳排：暂无日级碳排数据，按当日电量 × 电力碳因子折算（tCO2e）
    today_carbon = today_energy * factor / 1000

    pending_alarm = int(
        (
            await session.execute(
                select(func.count(AlarmInfo.id)).where(AlarmInfo.status == "pending")
            )
        ).scalar_one()
        or 0
    )
    month_fee = await _sum_fee(session, _dt(m_start), _dt(m_end))

    period_value = today.strftime("%Y-%m")
    quota_rows = (
        await session.execute(
            select(QuotaMonitor.complete_rate, QuotaMonitor.warn_status).where(
                QuotaMonitor.period_value == period_value
            )
        )
    ).all()
    quota_total = len(quota_rows)
    quota_exceed = sum(1 for r in quota_rows if r[1] == "exceed")
    quota_rate = (
        round(sum(float(r[0] or 0) for r in quota_rows) / quota_total, 2) if quota_total else 0.0
    )

    return {
        "device_total": device_total,
        "device_online": device_online,
        "online_rate": round(device_online / device_total * 100, 1) if device_total else 0.0,
        "today_energy": round(today_energy, 2),
        "month_energy": round(month_energy, 2),
        "today_carbon": round(today_carbon, 3),
        "month_carbon": round(month_carbon, 2),
        "pending_alarm": pending_alarm,
        "month_fee": round(month_fee, 2),
        "quota_rate": quota_rate,
        "quota_exceed": quota_exceed,
    }


async def energy_trend(session: AsyncSession, days: int = 7) -> dict:
    """近 N 日电力能耗与碳排趋势。"""
    today = date.today()
    ele = await _energy_type_id(session, "electricity")
    factor = await _ele_factor(session, ele)
    dates, energies, carbons = [], [], []
    for i in range(days - 1, -1, -1):
        d = today - timedelta(days=i)
        s = _dt(d)
        e = s + timedelta(days=1)
        val = await _sum_energy(session, ele, s, e)
        dates.append(d.strftime("%m-%d"))
        energies.append(round(val, 2))
        carbons.append(round(val * factor / 1000, 3))
    return {"dates": dates, "energy": energies, "carbon": carbons}


async def energy_item_ratio(
    session: AsyncSession, start: date | None = None, end: date | None = None
) -> list[dict]:
    """各分项用电占比（默认本月）。"""
    m_start, m_end = _month_range(end or date.today())
    start_dt, end_dt = _dt(start or m_start), _dt(m_end)
    ele = await _energy_type_id(session, "electricity")

    stmt = (
        select(CfgEnergyItem.item_name, func.coalesce(func.sum(EnergyStat.stat_value), 0))
        .join(CfgEnergyItem, CfgEnergyItem.id == EnergyStat.energy_item_id)
        .where(
            EnergyStat.stat_type == "day",
            EnergyStat.device_id.is_(None),
            EnergyStat.energy_item_id.is_not(None),
            EnergyStat.stat_time >= start_dt,
            EnergyStat.stat_time < end_dt,
        )
        .group_by(CfgEnergyItem.item_name)
        .order_by(func.sum(EnergyStat.stat_value).desc())
    )
    if ele is not None:
        stmt = stmt.where(EnergyStat.energy_type_id == ele)
    rows = (await session.execute(stmt)).all()
    total = sum(float(r[1] or 0) for r in rows) or 1.0
    return [
        {"name": r[0], "value": round(float(r[1] or 0), 2), "ratio": round(float(r[1] or 0) / total * 100, 1)}
        for r in rows
    ]


async def area_rank(
    session: AsyncSession, start: date | None = None, end: date | None = None, limit: int = 8
) -> list[dict]:
    """各区域用电排名（默认本月）。"""
    m_start, m_end = _month_range(end or date.today())
    start_dt, end_dt = _dt(start or m_start), _dt(m_end)
    ele = await _energy_type_id(session, "electricity")

    stmt = (
        select(DevArea.area_name, func.coalesce(func.sum(EnergyStat.stat_value), 0))
        .join(DevArea, DevArea.id == EnergyStat.area_id)
        .where(
            EnergyStat.stat_type == "day",
            EnergyStat.device_id.is_(None),
            EnergyStat.area_id.is_not(None),
            EnergyStat.stat_time >= start_dt,
            EnergyStat.stat_time < end_dt,
        )
        .group_by(DevArea.area_name)
        .order_by(func.sum(EnergyStat.stat_value).desc())
        .limit(limit)
    )
    if ele is not None:
        stmt = stmt.where(EnergyStat.energy_type_id == ele)
    rows = (await session.execute(stmt)).all()
    return [{"name": r[0], "value": round(float(r[1] or 0), 2)} for r in rows]


async def carbon_overview(session: AsyncSession, year: int | None = None) -> dict:
    """年度碳排总览：总量 + 范围占比 + 月度趋势。"""
    year = year or date.today().year
    prefix = f"{year}-"
    rows = (
        await session.execute(
            select(CarbonEmission.period_value, CarbonEmission.scope, CarbonEmission.emission_value).where(
                CarbonEmission.period_type == "month",
                CarbonEmission.area_id.is_(None),
                CarbonEmission.period_value.like(f"{prefix}%"),
            )
        )
    ).all()

    total = sum(float(r[2] or 0) for r in rows)
    by_scope: dict[str, float] = {}
    by_month: dict[str, float] = {}
    for pv, scope, emission in rows:
        by_scope[scope or "未分类"] = by_scope.get(scope or "未分类", 0.0) + float(emission or 0)
        by_month[pv] = by_month.get(pv, 0.0) + float(emission or 0)
    months = sorted(by_month)
    return {
        "year": year,
        "total": round(total, 2),
        "scopes": [
            {"name": k, "value": round(v, 2), "ratio": round(v / total * 100, 1) if total else 0}
            for k, v in by_scope.items()
        ],
        "trend": {"months": months, "values": [round(by_month[m], 2) for m in months]},
    }


async def device_status(session: AsyncSession) -> dict:
    """设备在线状态与运行状态分布。"""
    online_rows = (
        await session.execute(
            select(DevDevice.online_status, func.count(DevDevice.id)).group_by(DevDevice.online_status)
        )
    ).all()
    status_rows = (
        await session.execute(
            select(DevDevice.status, func.count(DevDevice.id)).group_by(DevDevice.status)
        )
    ).all()
    name_map = {"online": "在线", "offline": "离线", "abnormal": "异常"}
    status_map = {"normal": "正常", "disabled": "停用", "repair": "维修", "scrapped": "报废"}
    return {
        "online": [{"name": name_map.get(r[0], r[0] or "未知"), "value": int(r[1] or 0)} for r in online_rows],
        "status": [{"name": status_map.get(r[0], r[0] or "未知"), "value": int(r[1] or 0)} for r in status_rows],
    }


async def latest_alarms(session: AsyncSession, limit: int = 10) -> list[dict]:
    """最新告警（驾驶舱滚动展示）。"""
    rows = (
        await session.execute(
            select(AlarmInfo, DevDevice.device_name)
            .join(DevDevice, DevDevice.id == AlarmInfo.device_id, isouter=True)
            .order_by(AlarmInfo.alarm_time.desc())
            .limit(limit)
        )
    ).all()
    return [
        {
            "id": alarm.id,
            "alarm_no": alarm.alarm_no,
            "device_name": device_name or "-",
            "alarm_level": alarm.alarm_level,
            "content": alarm.content,
            "status": alarm.status,
            "alarm_time": alarm.alarm_time,
        }
        for alarm, device_name in rows
    ]


async def fee_quota(session: AsyncSession) -> dict:
    """费用与定额概览：本月费用、环比、定额完成与超限数。"""
    today = date.today()
    m_start, m_end = _month_range(today)
    prev_start = (m_start - timedelta(days=1)).replace(day=1)
    prev_end = m_start

    cur_fee = await _sum_fee(session, _dt(m_start), _dt(m_end))
    prev_fee = await _sum_fee(session, _dt(prev_start), _dt(prev_end))
    mom = round((cur_fee - prev_fee) / prev_fee * 100, 2) if prev_fee else 0.0

    period_value = today.strftime("%Y-%m")
    rows = (
        await session.execute(
            select(QuotaMonitor.complete_rate, QuotaMonitor.warn_status).where(
                QuotaMonitor.period_value == period_value
            )
        )
    ).all()
    total = len(rows)
    exceed = sum(1 for r in rows if r[1] == "exceed")
    warning = sum(1 for r in rows if r[1] == "warning")
    rate = round(sum(float(r[0] or 0) for r in rows) / total, 2) if total else 0.0

    return {
        "month_fee": round(cur_fee, 2),
        "prev_fee": round(prev_fee, 2),
        "fee_mom": mom,
        "quota_total": total,
        "quota_rate": rate,
        "quota_warning": warning,
        "quota_exceed": exceed,
    }
