"""费用域服务（B5-2 费用统计/对比/报表/导出）。"""

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dev import DevArea
from app.models.energy import EnergyFeeStat, EnergyPricePlan
from app.services.price_service import PERIOD_NAMES

PERIOD_ORDER = {"sharp": 0, "peak": 1, "flat": 2, "valley": 3}


def _month_str(d: date) -> str:
    return f"{d:%Y-%m}"


async def _area_names(session: AsyncSession) -> dict[int, str]:
    return {a.id: a.area_name for a in (await session.execute(select(DevArea))).scalars().all()}


def _base_stmt():
    return select(EnergyFeeStat).where(
        EnergyFeeStat.stat_type == "month",
        EnergyFeeStat.area_id.is_(None),
        EnergyFeeStat.energy_item_id.is_(None),
    )


async def stat(session: AsyncSession, dim: str = "period") -> dict:
    """费用统计：按分时/按月/按区域。"""
    total_usage = float(
        (await session.execute(select(func.coalesce(func.sum(EnergyFeeStat.usage_value), 0)).where(
            EnergyFeeStat.stat_type == "month",
            EnergyFeeStat.area_id.is_(None),
            EnergyFeeStat.energy_item_id.is_(None),
        ))).scalar_one() or 0
    )
    total_fee = float(
        (await session.execute(select(func.coalesce(func.sum(EnergyFeeStat.fee_value), 0)).where(
            EnergyFeeStat.stat_type == "month",
            EnergyFeeStat.area_id.is_(None),
            EnergyFeeStat.energy_item_id.is_(None),
        ))).scalar_one() or 0
    )

    if dim == "month":
        ym_expr = func.to_char(EnergyFeeStat.stat_time, "YYYY-MM")
        rows = (
            await session.execute(
                select(
                    ym_expr,
                    func.coalesce(func.sum(EnergyFeeStat.usage_value), 0),
                    func.coalesce(func.sum(EnergyFeeStat.fee_value), 0),
                )
                .where(
                    EnergyFeeStat.stat_type == "month",
                    EnergyFeeStat.area_id.is_(None),
                    EnergyFeeStat.energy_item_id.is_(None),
                )
                .group_by(ym_expr)
                .order_by(ym_expr)
            )
        ).all()
        items = [
            {"name": r[0], "usage": round(float(r[1]), 2), "fee": round(float(r[2]), 2)}
            for r in rows
        ]
    elif dim == "area":
        rows = (
            await session.execute(
                select(
                    EnergyFeeStat.area_id,
                    func.coalesce(func.sum(EnergyFeeStat.usage_value), 0),
                    func.coalesce(func.sum(EnergyFeeStat.fee_value), 0),
                )
                .where(EnergyFeeStat.stat_type == "month", EnergyFeeStat.area_id.is_not(None))
                .group_by(EnergyFeeStat.area_id)
            )
        ).all()
        names = await _area_names(session)
        items = [
            {"name": names.get(r[0], f"ID-{r[0]}"), "usage": round(float(r[1]), 2), "fee": round(float(r[2]), 2)}
            for r in rows
        ]
        items.sort(key=lambda x: x["fee"], reverse=True)
    else:
        rows = (
            await session.execute(
                select(
                    EnergyFeeStat.period_type,
                    func.coalesce(func.sum(EnergyFeeStat.usage_value), 0),
                    func.coalesce(func.sum(EnergyFeeStat.fee_value), 0),
                )
                .where(
                    EnergyFeeStat.stat_type == "month",
                    EnergyFeeStat.area_id.is_(None),
                    EnergyFeeStat.energy_item_id.is_(None),
                )
                .group_by(EnergyFeeStat.period_type)
            )
        ).all()
        items = [
            {
                "name": PERIOD_NAMES.get(r[0], r[0]),
                "period_type": r[0],
                "usage": round(float(r[1]), 2),
                "fee": round(float(r[2]), 2),
            }
            for r in rows
        ]
        items.sort(key=lambda x: PERIOD_ORDER.get(x["period_type"], 9))

    avg_price = round(total_fee / total_usage, 4) if total_usage else 0
    return {
        "summary": {
            "total_usage": round(total_usage, 2),
            "total_fee": round(total_fee, 2),
            "avg_price": avg_price,
        },
        "items": items,
    }


async def _month_fee(session: AsyncSession, d: date) -> float:
    stmt = select(func.coalesce(func.sum(EnergyFeeStat.fee_value), 0)).where(
        EnergyFeeStat.stat_type == "day",
        EnergyFeeStat.area_id.is_(None),
        EnergyFeeStat.energy_item_id.is_(None),
        func.to_char(EnergyFeeStat.stat_time, "YYYY-MM") == _month_str(d),
    )
    return float((await session.execute(stmt)).scalar_one() or 0)


async def _month_usage(session: AsyncSession, d: date) -> float:
    stmt = select(func.coalesce(func.sum(EnergyFeeStat.usage_value), 0)).where(
        EnergyFeeStat.stat_type == "day",
        EnergyFeeStat.area_id.is_(None),
        EnergyFeeStat.energy_item_id.is_(None),
        func.to_char(EnergyFeeStat.stat_time, "YYYY-MM") == _month_str(d),
    )
    return float((await session.execute(stmt)).scalar_one() or 0)


def _add_months(d: date, n: int) -> date:
    y, m = d.year, d.month + n
    y += (m - 1) // 12
    m = (m - 1) % 12 + 1
    return date(y, m, 1)


async def compare(session: AsyncSession) -> dict:
    """费用对比：环比 / 同比 / 分时对比。"""
    today = date.today()
    cur = today.replace(day=1)
    last = _add_months(cur, -1)
    same_last_year = _add_months(cur, -12)

    cur_fee = await _month_fee(session, cur)
    last_fee = await _month_fee(session, last)
    ly_fee = await _month_fee(session, same_last_year)

    def _rate(c: float, b: float) -> float | None:
        return round((c - b) / b * 100, 2) if b else None

    # 分时对比：本月各时段 vs 上月各时段
    async def _period_map(d: date) -> dict[str, float]:
        rows = (
            await session.execute(
                select(EnergyFeeStat.period_type, func.coalesce(func.sum(EnergyFeeStat.fee_value), 0))
                .where(
                    EnergyFeeStat.stat_type == "day",
                    EnergyFeeStat.area_id.is_(None),
                    EnergyFeeStat.energy_item_id.is_(None),
                    func.to_char(EnergyFeeStat.stat_time, "YYYY-MM") == _month_str(d),
                )
                .group_by(EnergyFeeStat.period_type)
            )
        ).all()
        return {r[0]: round(float(r[1]), 2) for r in rows}

    cur_map = await _period_map(cur)
    last_map = await _period_map(last)
    period_compare = []
    for ptype, name in PERIOD_NAMES.items():
        period_compare.append(
            {"name": name, "period_type": ptype, "current": cur_map.get(ptype, 0), "last": last_map.get(ptype, 0)}
        )
    period_compare.sort(key=lambda x: PERIOD_ORDER.get(x["period_type"], 9))

    return {
        "current": {"month": _month_str(cur), "usage": round(await _month_usage(session, cur), 2), "fee": round(cur_fee, 2)},
        "mom": {"month": _month_str(last), "fee": round(last_fee, 2), "rate": _rate(cur_fee, last_fee)},
        "yoy": {"month": _month_str(same_last_year), "fee": round(ly_fee, 2), "rate": _rate(cur_fee, ly_fee)},
        "period_compare": period_compare,
    }


async def report(session: AsyncSession, year: int | None = None) -> dict:
    """费用报表：按月汇总 + 分时构成。"""
    year = year or date.today().year
    ym_expr = func.to_char(EnergyFeeStat.stat_time, "YYYY-MM")
    rows = (
        await session.execute(
            select(
                ym_expr,
                func.coalesce(func.sum(EnergyFeeStat.usage_value), 0),
                func.coalesce(func.sum(EnergyFeeStat.fee_value), 0),
            )
            .where(
                EnergyFeeStat.stat_type == "month",
                EnergyFeeStat.area_id.is_(None),
                EnergyFeeStat.energy_item_id.is_(None),
                func.to_char(EnergyFeeStat.stat_time, "YYYY") == str(year),
            )
            .group_by(ym_expr)
            .order_by(ym_expr)
        )
    ).all()

    items = []
    for r in rows:
        usage = float(r[1])
        fee = float(r[2])
        items.append({
            "month": r[0],
            "usage": round(usage, 2),
            "fee": round(fee, 2),
            "avg_price": round(fee / usage, 4) if usage else 0,
        })

    total_usage = sum(x["usage"] for x in items)
    total_fee = sum(x["fee"] for x in items)
    return {
        "year": year,
        "rows": items,
        "summary": {
            "month_count": len(items),
            "total_usage": round(total_usage, 2),
            "total_fee": round(total_fee, 2),
            "avg_price": round(total_fee / total_usage, 4) if total_usage else 0,
        },
    }


async def export_report(session: AsyncSession, year: int | None = None) -> bytes:
    import io

    from openpyxl import Workbook

    data = await report(session, year)
    wb = Workbook()
    ws = wb.active
    ws.title = "费用报表"
    ws.append([f"{data['year']} 年度电费报表"])
    ws.append(["月份", "用电量(kWh)", "费用(元)", "平均电价(元/kWh)"])
    for x in data["rows"]:
        ws.append([x["month"], x["usage"], x["fee"], x["avg_price"]])
    ws.append(["合计", data["summary"]["total_usage"], data["summary"]["total_fee"], data["summary"]["avg_price"]])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


async def active_plans(session: AsyncSession) -> list[dict]:
    plans = (
        await session.execute(select(EnergyPricePlan).order_by(EnergyPricePlan.effective_date.desc().nullslast()))
    ).scalars().all()
    return [p.model_dump() for p in plans]
