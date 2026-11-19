"""电价与费用域服务（B5-2 电价方案/时段/调整历史）。"""

from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BizException
from app.models.cfg import CfgEnergyType
from app.models.energy import EnergyPriceHistory, EnergyPricePeriod, EnergyPricePlan
from app.models.sys import SysUser

# 标准分时时段（一般工商业，用于默认电价方案与能耗峰谷分类）
STANDARD_PERIODS: list[tuple[str, str, str]] = [
    ("sharp", "11:00", "13:00"),
    ("peak", "08:00", "11:00"),
    ("peak", "18:00", "21:00"),
    ("flat", "07:00", "08:00"),
    ("flat", "13:00", "18:00"),
    ("flat", "21:00", "23:00"),
    ("valley", "23:00", "07:00"),
]

# 标准分时电价（元/kWh）
STANDARD_PRICES: dict[str, str] = {"sharp": "1.3520", "peak": "1.0800", "flat": "0.6800", "valley": "0.3200"}

PERIOD_NAMES: dict[str, str] = {"sharp": "尖峰", "peak": "高峰", "flat": "平段", "valley": "低谷"}
DAY_TYPE_NAMES: dict[str, str] = {"workday": "工作日", "weekend": "周末", "holiday": "节假日"}


def hour_period(hour: int) -> str:
    """按标准分时时段返回某小时所属时段类型（sharp/peak/flat/valley）。"""
    for ptype, start, end in STANDARD_PERIODS:
        s, e = int(start[:2]), int(end[:2])
        if s < e:
            if s <= hour < e:
                return ptype
        elif hour >= s or hour < e:  # 跨零点
            return ptype
    return "flat"


async def _energy_type_names(session: AsyncSession) -> dict[int, str]:
    rows = (await session.execute(select(CfgEnergyType))).scalars().all()
    return {t.id: t.type_name for t in rows}


def _plan_dict(plan: EnergyPricePlan, type_names: dict[int, str]) -> dict:
    data = plan.model_dump()
    data["energy_type_name"] = type_names.get(plan.energy_type_id) if plan.energy_type_id else None
    data["status_text"] = "启用" if plan.status == 1 else "停用"
    return data


async def page_plans(session: AsyncSession, keyword: str | None = None, status: int | None = None) -> list[dict]:
    """电价方案列表（方案数量少，直接全量返回）。"""
    stmt = select(EnergyPricePlan)
    if status is not None:
        stmt = stmt.where(EnergyPricePlan.status == status)
    if keyword:
        stmt = stmt.where(EnergyPricePlan.plan_name.ilike(f"%{keyword}%"))
    stmt = stmt.order_by(EnergyPricePlan.effective_date.desc().nullslast(), EnergyPricePlan.id.desc())
    plans = (await session.execute(stmt)).scalars().all()
    type_names = await _energy_type_names(session)

    period_counts = dict(
        (await session.execute(
            select(EnergyPricePeriod.plan_id, func.count(EnergyPricePeriod.id)).group_by(EnergyPricePeriod.plan_id)
        )).all()
    )
    items = []
    for p in plans:
        item = _plan_dict(p, type_names)
        item["period_count"] = period_counts.get(p.id, 0)
        items.append(item)
    return items


async def get_plan(session: AsyncSession, plan_id: int) -> EnergyPricePlan:
    plan = await session.get(EnergyPricePlan, plan_id)
    if not plan:
        raise BizException("电价方案不存在")
    return plan


async def save_plan(
    session: AsyncSession, plan_id: int | None, data: dict, operator_id: int | None
) -> dict:
    if plan_id:
        plan = await get_plan(session, plan_id)
    else:
        plan = EnergyPricePlan(plan_code="", plan_name="")
    for key, value in data.items():
        setattr(plan, key, value)
    session.add(plan)
    await session.commit()
    await session.refresh(plan)

    if plan_id:  # 编辑时记录变更留痕
        session.add(
            EnergyPriceHistory(
                plan_id=plan.id,
                change_desc="方案信息调整",
                old_value=None,
                new_value=plan.plan_name,
                effective_date=plan.effective_date,
                operator_id=operator_id,
            )
        )
        await session.commit()

    type_names = await _energy_type_names(session)
    return _plan_dict(plan, type_names)


async def delete_plan(session: AsyncSession, plan_id: int) -> None:
    plan = await get_plan(session, plan_id)
    periods = (
        await session.execute(select(EnergyPricePeriod).where(EnergyPricePeriod.plan_id == plan_id))
    ).scalars().all()
    for p in periods:
        await session.delete(p)
    history = (
        await session.execute(select(EnergyPriceHistory).where(EnergyPriceHistory.plan_id == plan_id))
    ).scalars().all()
    for h in history:
        h.plan_id = None
        session.add(h)
    await session.delete(plan)
    await session.commit()


async def get_period(session: AsyncSession, period_id: int) -> EnergyPricePeriod:
    period = await session.get(EnergyPricePeriod, period_id)
    if not period:
        raise BizException("时段不存在")
    return period


async def list_periods(session: AsyncSession, plan_id: int) -> list[dict]:
    periods = (
        await session.execute(
            select(EnergyPricePeriod)
            .where(EnergyPricePeriod.plan_id == plan_id)
            .order_by(EnergyPricePeriod.sort_no, EnergyPricePeriod.id)
        )
    ).scalars().all()
    result = []
    for p in periods:
        item = p.model_dump()
        item["period_name"] = PERIOD_NAMES.get(p.period_type, p.period_type)
        item["day_type_name"] = DAY_TYPE_NAMES.get(p.day_type, p.day_type)
        result.append(item)
    return result


async def save_period(
    session: AsyncSession, plan_id: int, period_id: int | None, data: dict, operator_id: int | None
) -> dict:
    await get_plan(session, plan_id)
    if period_id:
        period = await get_period(session, period_id)
        old_price = str(period.price)
    else:
        period = EnergyPricePeriod(plan_id=plan_id)
        old_price = None

    for key, value in data.items():
        setattr(period, key, value)
    period.plan_id = plan_id
    session.add(period)
    await session.commit()
    await session.refresh(period)

    if old_price is not None and str(period.price) != old_price:
        session.add(
            EnergyPriceHistory(
                plan_id=plan_id,
                change_desc=f"{PERIOD_NAMES.get(period.period_type, period.period_type)}电价调整",
                old_value=old_price,
                new_value=str(period.price),
                effective_date=date.today(),
                operator_id=operator_id,
            )
        )
        await session.commit()

    item = period.model_dump()
    item["period_name"] = PERIOD_NAMES.get(period.period_type, period.period_type)
    item["day_type_name"] = DAY_TYPE_NAMES.get(period.day_type, period.day_type)
    return item


async def delete_period(session: AsyncSession, period_id: int) -> None:
    period = await get_period(session, period_id)
    await session.delete(period)
    await session.commit()


async def list_history(session: AsyncSession, plan_id: int | None = None) -> list[dict]:
    stmt = select(EnergyPriceHistory)
    if plan_id:
        stmt = stmt.where(EnergyPriceHistory.plan_id == plan_id)
    stmt = stmt.order_by(EnergyPriceHistory.changed_at.desc(), EnergyPriceHistory.id.desc())
    rows = (await session.execute(stmt)).scalars().all()
    type_plan = {
        p.id: p.plan_name
        for p in (await session.execute(select(EnergyPricePlan))).scalars().all()
    }
    user_names = {
        u.id: u.real_name
        for u in (await session.execute(select(SysUser))).scalars().all()
    }
    items = []
    for h in rows:
        item = h.model_dump()
        item["plan_name"] = type_plan.get(h.plan_id) if h.plan_id else None
        item["operator_name"] = user_names.get(h.operator_id) if h.operator_id else None
        items.append(item)
    return items


async def active_electricity_periods(session: AsyncSession, at: datetime | None = None) -> list[dict]:
    """取当前生效的电力方案时段（用于能耗峰谷分类）。"""
    at_date = (at or datetime.now().astimezone()).date()
    stmt = (
        select(EnergyPricePeriod)
        .join(EnergyPricePlan, EnergyPricePlan.id == EnergyPricePeriod.plan_id)
        .join(CfgEnergyType, CfgEnergyType.id == EnergyPricePlan.energy_type_id)
        .where(
            CfgEnergyType.type_code == "electricity",
            EnergyPricePlan.status == 1,
            (EnergyPricePlan.effective_date.is_(None)) | (EnergyPricePlan.effective_date <= at_date),
            (EnergyPricePlan.expire_date.is_(None)) | (EnergyPricePlan.expire_date >= at_date),
        )
        .order_by(EnergyPricePeriod.sort_no)
    )
    periods = (await session.execute(stmt)).scalars().all()
    return [
        {
            "period_type": p.period_type,
            "period_name": PERIOD_NAMES.get(p.period_type, p.period_type),
            "start_time": p.start_time,
            "end_time": p.end_time,
            "price": float(p.price) if p.price is not None else 0.0,
        }
        for p in periods
    ]
