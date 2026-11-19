"""能耗域示例数据（B5-1）：按区域/分项/时间生成贴近真实的能耗统计。"""

import random
from datetime import date, datetime, time, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cfg import CfgEnergyItem, CfgEnergyType
from app.models.dev import DevArea, DevDevice
from app.models.energy import EnergyStat
from app.services.energy_service import HOUR_SHARE

# 各区域分项日用电基线（kWh/日）
ELECTRIC_BASE = {
    ("AREA_F1", "lighting"): 120, ("AREA_F1", "hvac"): 50, ("AREA_F1", "elevator"): 45,
    ("AREA_F1", "office"): 80, ("AREA_F1", "power"): 180, ("AREA_F1", "socket"): 55,
    ("AREA_F3", "lighting"): 60, ("AREA_F3", "hvac"): 760, ("AREA_F3", "office"): 30,
    ("AREA_F3", "power"): 110, ("AREA_F3", "socket"): 20,
    ("AREA_SHOP_A", "lighting"): 170, ("AREA_SHOP_A", "hvac"): 240, ("AREA_SHOP_A", "office"): 40,
    ("AREA_SHOP_A", "power"): 900, ("AREA_SHOP_A", "socket"): 80,
    ("AREA_SHOP_B", "lighting"): 140, ("AREA_SHOP_B", "hvac"): 190, ("AREA_SHOP_B", "elevator"): 40,
    ("AREA_SHOP_B", "office"): 45, ("AREA_SHOP_B", "power"): 680, ("AREA_SHOP_B", "socket"): 70,
}
# 空调季节系数
HVAC_MONTH_FACTOR = {1: 1.30, 2: 1.15, 3: 0.90, 4: 0.70, 5: 0.85, 6: 1.15,
                     7: 1.40, 8: 1.45, 9: 1.10, 10: 0.75, 11: 0.95, 12: 1.25}
PARK_WATER = {"domestic_water": 120.0, "fire_water": 8.0}
PARK_GAS = {"boiler_gas": 260.0, "canteen_gas": 90.0}
PV_BASE = 1650.0          # 光伏日发电量（kWh）
AIR_BASE = 3200.0         # 空压机日产气量（m³）
CONSUME_AREAS = ["AREA_F1", "AREA_F3", "AREA_SHOP_A", "AREA_SHOP_B"]
DAY_SPAN = 120
DEVICE_DAY_SPAN = 30
HOUR_SPAN = 7


def _dt(d: date, hour: int = 0) -> datetime:
    return datetime.combine(d, time(hour=hour)).astimezone()


def _weekend_factor(d: date) -> float:
    return 0.55 if d.weekday() >= 5 else 1.0


def _season(icode: str, d: date) -> float:
    return HVAC_MONTH_FACTOR[d.month] if icode == "hvac" else 1.0


async def seed_energy_domain(session: AsyncSession) -> dict[str, int]:
    await session.execute(delete(EnergyStat))
    await session.commit()

    types = {t.type_code: t for t in (await session.execute(select(CfgEnergyType))).scalars().all()}
    items = {i.item_code: i for i in (await session.execute(select(CfgEnergyItem))).scalars().all()}
    areas = {a.area_code: a for a in (await session.execute(select(DevArea))).scalars().all()}
    devices = (await session.execute(select(DevDevice))).scalars().all()

    rnd = random.Random(20261118)
    today = date.today()
    ele_id = types["electricity"].id

    # ---------- 1. 日统计 ----------
    rows: list[EnergyStat] = []
    for i in range(DAY_SPAN):
        d = today - timedelta(days=i)
        wf = _weekend_factor(d)
        for (acode, icode), base in ELECTRIC_BASE.items():
            val = base * _season(icode, d) * wf * rnd.uniform(0.92, 1.08)
            rows.append(EnergyStat(
                stat_type="day", stat_time=_dt(d), energy_type_id=ele_id,
                energy_item_id=items[icode].id, area_id=areas[acode].id,
                stat_value=round(val, 2), unit="kWh",
            ))
        for icode, base in {**PARK_WATER, **PARK_GAS}.items():
            etype = "water" if icode in PARK_WATER else "gas"
            val = base * wf * rnd.uniform(0.90, 1.10)
            rows.append(EnergyStat(
                stat_type="day", stat_time=_dt(d), energy_type_id=types[etype].id,
                energy_item_id=items[icode].id, area_id=areas["AREA_ROOT"].id,
                stat_value=round(val, 2), unit="m³",
            ))
        pv = PV_BASE * (1.0 if d.month in (4, 5, 6, 7, 8, 9) else 0.7) * rnd.uniform(0.90, 1.10)
        rows.append(EnergyStat(
            stat_type="day", stat_time=_dt(d), energy_type_id=types["pv"].id,
            energy_item_id=items["pv_generation"].id, area_id=areas["AREA_PV"].id,
            stat_value=round(pv, 2), unit="kWh",
        ))
        air = AIR_BASE * wf * rnd.uniform(0.92, 1.08)
        rows.append(EnergyStat(
            stat_type="day", stat_time=_dt(d), energy_type_id=types["compressed_air"].id,
            energy_item_id=items["ac_air"].id, area_id=areas["AREA_SHOP_A"].id,
            stat_value=round(air, 2), unit="m³",
        ))
    session.add_all(rows)
    await session.commit()
    day_count = len(rows)

    # ---------- 2. 月统计（由日统计聚合） ----------
    month_expr = func.to_char(EnergyStat.stat_time, "YYYY-MM")
    month_rows = (
        await session.execute(
            select(
                month_expr,
                EnergyStat.energy_type_id,
                EnergyStat.energy_item_id,
                EnergyStat.area_id,
                func.sum(EnergyStat.stat_value),
                func.max(EnergyStat.unit),
            )
            .where(EnergyStat.stat_type == "day")
            .group_by(
                month_expr,
                EnergyStat.energy_type_id,
                EnergyStat.energy_item_id,
                EnergyStat.area_id,
            )
        )
    ).all()
    month_count = 0
    for m, et, item_id, area_id, total, unit in month_rows:
        y, mm = int(m[:4]), int(m[5:7])
        session.add(EnergyStat(
            stat_type="month", stat_time=_dt(date(y, mm, 1)), energy_type_id=et,
            energy_item_id=item_id, area_id=area_id,
            stat_value=round(float(total), 2), unit=unit,
        ))
        month_count += 1
    await session.commit()

    # ---------- 3. 小时统计（近 7 天，园区级，按负荷曲线拆分） ----------
    hour_count = 0
    for i in range(HOUR_SPAN):
        d = today - timedelta(days=i)
        item_day = (
            await session.execute(
                select(EnergyStat.energy_item_id, func.sum(EnergyStat.stat_value))
                .where(
                    EnergyStat.stat_type == "day",
                    EnergyStat.energy_type_id == ele_id,
                    EnergyStat.energy_item_id.is_not(None),
                    func.to_char(EnergyStat.stat_time, "YYYY-MM-DD") == f"{d:%Y-%m-%d}",
                )
                .group_by(EnergyStat.energy_item_id)
            )
        ).all()
        for item_id, total in item_day:
            total = float(total or 0)
            for hour in range(24):
                session.add(EnergyStat(
                    stat_type="hour", stat_time=_dt(d, hour), energy_type_id=ele_id,
                    energy_item_id=item_id, area_id=areas["AREA_ROOT"].id,
                    stat_value=round(total * HOUR_SHARE[hour], 4), unit="kWh",
                ))
                hour_count += 1
    await session.commit()

    # ---------- 4. 设备级日统计（近 30 天，用于设备排名） ----------
    by_area: dict[int, list] = {}
    for dev in devices:
        by_area.setdefault(dev.area_id, []).append(dev)
    area_total_base = {
        acode: sum(base for (a, _), base in ELECTRIC_BASE.items() if a == acode)
        for acode in CONSUME_AREAS
    }
    device_count = 0
    for i in range(DEVICE_DAY_SPAN):
        d = today - timedelta(days=i)
        wf = _weekend_factor(d)
        for acode in CONSUME_AREAS:
            devs = by_area.get(areas[acode].id, [])
            if not devs:
                continue
            for dev in devs:
                val = area_total_base[acode] / len(devs) * wf * rnd.uniform(0.85, 1.15)
                session.add(EnergyStat(
                    stat_type="day", stat_time=_dt(d), energy_type_id=ele_id,
                    energy_item_id=items["power"].id, area_id=areas[acode].id, device_id=dev.id,
                    stat_value=round(val, 2), unit="kWh",
                ))
                device_count += 1
    await session.commit()

    return {
        "能耗日统计": day_count,
        "能耗月统计": month_count,
        "能耗小时统计": hour_count,
        "设备能耗统计": device_count,
    }
