"""节能定额域示例数据（B6）：定额 + 近 12 个月监控 + 近 6 个月考核。"""

from datetime import date

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cfg import CfgEnergyType
from app.models.dev import DevArea
from app.models.quota import EnergyQuota, QuotaAssess, QuotaMonitor
from app.models.sys import SysUser
from app.services import quota_service as svc


def _recent_months(n: int) -> list[str]:
    """返回最近 n 个月的 'YYYY-MM'（含当月，按时间升序）。"""
    today = date.today()
    y, m = today.year, today.month
    result: list[str] = []
    for _ in range(n):
        result.append(f"{y:04d}-{m:02d}")
        m -= 1
        if m == 0:
            m, y = 12, y - 1
    return list(reversed(result))


async def seed_quota_domain(session: AsyncSession) -> dict[str, int]:
    await session.execute(delete(QuotaAssess))
    await session.execute(delete(QuotaMonitor))
    await session.execute(delete(EnergyQuota))
    await session.commit()

    types = {t.type_code: t for t in (await session.execute(select(CfgEnergyType))).scalars().all()}
    areas = {a.area_code: a for a in (await session.execute(select(DevArea))).scalars().all()}
    admin = (await session.execute(select(SysUser).where(SysUser.username == "admin"))).scalars().first()
    operator_id = admin.id if admin else None

    ele, water = types.get("electricity"), types.get("water")

    # 园区级总定额（园区整体用电，月度）
    park = EnergyQuota(
        quota_name="园区月度综合用电总定额",
        quota_type="area",
        target_id=None,
        energy_type_id=ele.id if ele else None,
        period_type="month",
        period_value=None,
        quota_value=105000,
        unit="kWh",
        parent_id=None,
        operator_id=operator_id,
    )
    session.add(park)
    await session.flush()
    park_id = park.id
    quota_count = 1

    # 区域 × 电/水 子定额（部分定额略低于实际，用于体现预警/超标场景）
    area_plan = [
        ("AREA_F1", 15000, 3000),
        ("AREA_F3", 25000, 3200),
        ("AREA_SHOP_A", 34000, 4200),
        ("AREA_SHOP_B", 32000, 3800),
    ]
    for code, ele_value, water_value in area_plan:
        area = areas.get(code)
        if not area:
            continue
        if ele:
            session.add(
                EnergyQuota(
                    quota_name=f"{area.area_name}月度用电定额", quota_type="area", target_id=area.id,
                    energy_type_id=ele.id, period_type="month", period_value=None,
                    quota_value=ele_value, unit="kWh", parent_id=park_id, operator_id=operator_id,
                )
            )
            quota_count += 1
        if water:
            session.add(
                EnergyQuota(
                    quota_name=f"{area.area_name}月度用水定额", quota_type="area", target_id=area.id,
                    energy_type_id=water.id, period_type="month", period_value=None,
                    quota_value=water_value, unit="m³", parent_id=park_id, operator_id=operator_id,
                )
            )
            quota_count += 1
    await session.commit()

    # 最近 12 个月监控
    monitor_count = 0
    for period_value in _recent_months(12):
        result = await svc.refresh_monitor(session, period_value, operator_id)
        monitor_count += result["monitor_count"]

    # 最近 6 个月考核
    assess_count = 0
    for period_value in _recent_months(6):
        result = await svc.generate_assess(session, period_value, operator_id)
        assess_count += result["count"]

    return {"能耗定额": quota_count, "定额监控": monitor_count, "定额考核": assess_count}
