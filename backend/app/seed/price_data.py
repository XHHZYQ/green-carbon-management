"""电价与费用域示例数据（B5-2）：电价方案/时段/调整历史 + 费用统计。"""

from datetime import date, datetime, time, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cfg import CfgEnergyItem, CfgEnergyType
from app.models.dev import DevArea
from app.models.energy import EnergyFeeStat, EnergyPriceHistory, EnergyPricePeriod, EnergyPricePlan, EnergyStat
from app.models.sys import SysUser
from app.services.energy_service import HOUR_SHARE
from app.services.price_service import STANDARD_PERIODS, STANDARD_PRICES, hour_period

DAY_SPAN = 120

# 各时段小时集合
HOURS_BY_PERIOD: dict[str, list[int]] = {}
for _h in range(24):
    HOURS_BY_PERIOD.setdefault(hour_period(_h), []).append(_h)
PERIOD_WEIGHT = {pt: sum(HOUR_SHARE[h] for h in hs) for pt, hs in HOURS_BY_PERIOD.items()}


def _dt(d: date) -> datetime:
    return datetime.combine(d, time.min).astimezone()


def _add_months(d: date, n: int) -> date:
    y, m = d.year, d.month + n
    y += (m - 1) // 12
    m = (m - 1) % 12 + 1
    return date(y, m, 1)


async def _seed_plans(session: AsyncSession, operator_id: int | None) -> dict[str, int]:
    await session.execute(delete(EnergyPriceHistory))
    await session.execute(delete(EnergyPricePeriod))
    await session.execute(delete(EnergyFeeStat))
    await session.execute(delete(EnergyPricePlan))
    await session.commit()

    types = {t.type_code: t for t in (await session.execute(select(CfgEnergyType))).scalars().all()}

    plan_defs = [
        ("EP2025_GENERAL", "2025年一般工商业电价方案", "electricity", date(2025, 1, 1), date(2026, 12, 31), 1),
        ("EP2024_GENERAL", "2024年一般工商业电价方案", "electricity", date(2024, 1, 1), date(2024, 12, 31), 0),
        ("WP2025", "2025年自来水价格方案", "water", date(2025, 1, 1), date(2026, 12, 31), 1),
        ("GP2025", "2025年天然气价格方案", "gas", date(2025, 1, 1), date(2026, 12, 31), 1),
        ("PP2025", "光伏上网电价方案", "pv", date(2025, 1, 1), date(2026, 12, 31), 1),
    ]
    price_maps = {
        "EP2025_GENERAL": STANDARD_PRICES,
        "EP2024_GENERAL": {"sharp": "1.2900", "peak": "1.0300", "flat": "0.6500", "valley": "0.3000"},
    }
    plan_ids: dict[str, int] = {}
    for code, name, etype, eff, exp, status in plan_defs:
        plan = EnergyPricePlan(
            plan_code=code, plan_name=name, energy_type_id=types[etype].id,
            effective_date=eff, expire_date=exp, status=status, operator_id=operator_id,
        )
        session.add(plan)
        await session.commit()
        await session.refresh(plan)
        plan_ids[code] = plan.id

        if code in price_maps:
            for idx, (ptype, start, end) in enumerate(STANDARD_PERIODS, start=1):
                session.add(EnergyPricePeriod(
                    plan_id=plan.id, period_type=ptype, start_time=start, end_time=end,
                    day_type="workday", price=price_maps[code][ptype], sort_no=idx,
                ))
        else:
            flat_price = {"WP2025": "4.1000", "GP2025": "3.2000", "PP2025": "0.4200"}[code]
            session.add(EnergyPricePeriod(
                plan_id=plan.id, period_type="flat", start_time="00:00", end_time="24:00",
                day_type="workday", price=flat_price, sort_no=1,
            ))
        await session.commit()

    # 电价调整历史
    changes = [
        ("EP2025_GENERAL", "尖峰电价调整", "1.3200", "1.3520", date(2025, 7, 1)),
        ("EP2025_GENERAL", "低谷电价调整", "0.3000", "0.3200", date(2025, 7, 1)),
        ("EP2025_GENERAL", "方案生效", None, "2025年一般工商业电价方案", date(2025, 1, 1)),
        ("EP2024_GENERAL", "高峰电价调整", "0.9800", "1.0300", date(2024, 6, 1)),
    ]
    for code, desc, old, new, eff in changes:
        session.add(EnergyPriceHistory(
            plan_id=plan_ids[code], change_desc=desc, old_value=old, new_value=new,
            effective_date=eff, operator_id=operator_id,
        ))
    await session.commit()
    return plan_ids


async def seed_price_domain(session: AsyncSession) -> dict[str, int]:
    admin = (
        await session.execute(select(SysUser).where(SysUser.username == "admin"))
    ).scalars().first()
    operator_id = admin.id if admin else None

    plan_ids = await _seed_plans(session, operator_id)
    plan_id = plan_ids["EP2025_GENERAL"]

    types = {t.type_code: t for t in (await session.execute(select(CfgEnergyType))).scalars().all()}
    ele_id = types["electricity"].id

    # ---------- 日费用（园区级，按负荷曲线拆分到时段） ----------
    day_expr = func.to_char(EnergyStat.stat_time, "YYYY-MM-DD")
    day_rows = (
        await session.execute(
            select(day_expr, func.sum(EnergyStat.stat_value))
            .where(
                EnergyStat.stat_type == "day",
                EnergyStat.device_id.is_(None),
                EnergyStat.energy_type_id == ele_id,
            )
            .group_by(day_expr)
        )
    ).all()
    prices = {k: float(v) for k, v in STANDARD_PRICES.items()}

    day_count = 0
    month_acc: dict[tuple[str, str], list[float]] = {}   # (month, period) -> [usage, fee]
    for ds, total in day_rows:
        y, m, dd = int(ds[:4]), int(ds[5:7]), int(ds[8:10])
        d = date(y, m, dd)
        for ptype in ("sharp", "peak", "flat", "valley"):
            usage = float(total or 0) * PERIOD_WEIGHT.get(ptype, 0)
            fee = usage * prices[ptype]
            session.add(EnergyFeeStat(
                stat_type="day", stat_time=_dt(d), plan_id=plan_id, period_type=ptype,
                usage_value=round(usage, 4), fee_value=round(fee, 4),
            ))
            day_count += 1
            key = (f"{y:04d}-{m:02d}", ptype)
            acc = month_acc.setdefault(key, [0.0, 0.0])
            acc[0] += usage
            acc[1] += fee
    await session.commit()

    # ---------- 月费用（园区级） ----------
    month_count = 0
    for (mstr, ptype), (usage, fee) in month_acc.items():
        y, m = int(mstr[:4]), int(mstr[5:7])
        session.add(EnergyFeeStat(
            stat_type="month", stat_time=_dt(date(y, m, 1)), plan_id=plan_id, period_type=ptype,
            usage_value=round(usage, 4), fee_value=round(fee, 4),
        ))
        month_count += 1
    await session.commit()

    # ---------- 月费用（区域级） ----------
    area_month_expr = func.to_char(EnergyStat.stat_time, "YYYY-MM")
    area_rows = (
        await session.execute(
            select(
                area_month_expr,
                EnergyStat.area_id,
                func.sum(EnergyStat.stat_value),
            )
            .where(
                EnergyStat.stat_type == "day",
                EnergyStat.device_id.is_(None),
                EnergyStat.energy_type_id == ele_id,
                EnergyStat.area_id.is_not(None),
            )
            .group_by(area_month_expr, EnergyStat.area_id)
        )
    ).all()
    area_count = 0
    for mstr, area_id, total in area_rows:
        y, m = int(mstr[:4]), int(mstr[5:7])
        for ptype in ("sharp", "peak", "flat", "valley"):
            usage = float(total or 0) * PERIOD_WEIGHT.get(ptype, 0)
            session.add(EnergyFeeStat(
                stat_type="month", stat_time=_dt(date(y, m, 1)), plan_id=plan_id, period_type=ptype,
                area_id=area_id, usage_value=round(usage, 4), fee_value=round(usage * prices[ptype], 4),
            ))
            area_count += 1
    await session.commit()

    # ---------- 月费用（分项级） ----------
    item_month_expr = func.to_char(EnergyStat.stat_time, "YYYY-MM")
    item_rows = (
        await session.execute(
            select(
                item_month_expr,
                EnergyStat.energy_item_id,
                func.sum(EnergyStat.stat_value),
            )
            .where(
                EnergyStat.stat_type == "day",
                EnergyStat.device_id.is_(None),
                EnergyStat.energy_type_id == ele_id,
                EnergyStat.energy_item_id.is_not(None),
            )
            .group_by(item_month_expr, EnergyStat.energy_item_id)
        )
    ).all()
    item_count = 0
    for mstr, item_id, total in item_rows:
        y, m = int(mstr[:4]), int(mstr[5:7])
        for ptype in ("sharp", "peak", "flat", "valley"):
            usage = float(total or 0) * PERIOD_WEIGHT.get(ptype, 0)
            session.add(EnergyFeeStat(
                stat_type="month", stat_time=_dt(date(y, m, 1)), plan_id=plan_id, period_type=ptype,
                energy_item_id=item_id, usage_value=round(usage, 4), fee_value=round(usage * prices[ptype], 4),
            ))
            item_count += 1
    await session.commit()

    return {
        "电价方案": len(plan_ids),
        "费用日统计": day_count,
        "费用月统计": month_count,
        "费用区域统计": area_count,
        "费用分项统计": item_count,
    }
