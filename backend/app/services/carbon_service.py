"""碳排放域服务（B5-3 碳排总览/核算/明细/报告/减排对比）。"""

import io
from datetime import date, datetime, time

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BizException
from app.models.carbon import CarbonEmission, CarbonReport
from app.models.cfg import CfgCarbonFactor, CfgEnergyType
from app.models.dev import DevArea
from app.models.energy import EnergyStat

# 碳因子 scope 使用中文（见 cfg_carbon_factor.scope）
SCOPE_KEYS = {"范围一": "scope1", "范围二": "scope2", "范围三": "scope3"}
REDUCTION_SCOPE = "减排量"


def _dt(d: date) -> datetime:
    return datetime.combine(d, time.min).astimezone()


def _add_months(d: date, n: int) -> date:
    y, m = d.year, d.month + n
    y += (m - 1) // 12
    m = (m - 1) % 12 + 1
    return date(y, m, 1)


async def _maps(session: AsyncSession) -> dict[int, str]:
    return {t.id: t.type_name for t in (await session.execute(select(CfgEnergyType))).scalars().all()}


async def _active_factors(session: AsyncSession) -> dict[int, CfgCarbonFactor]:
    """按能源类型取当前生效的碳因子（排除减排量类型）。"""
    today = date.today()
    rows = (
        await session.execute(
            select(CfgCarbonFactor).where(
                CfgCarbonFactor.status == 1,
                (CfgCarbonFactor.effective_date.is_(None)) | (CfgCarbonFactor.effective_date <= today),
                (CfgCarbonFactor.expire_date.is_(None)) | (CfgCarbonFactor.expire_date >= today),
            )
        )
    ).scalars().all()
    result: dict[int, CfgCarbonFactor] = {}
    for f in rows:
        if f.scope == REDUCTION_SCOPE:
            continue
        result.setdefault(f.energy_type_id, f)
    return result


def _to_ton(energy: float, factor: float) -> float:
    """能耗值 × 碳因子(kgCO2e/单位) 换算为 tCO2e。"""
    return round(energy * factor / 1000, 2)


# ==================== 核算 ====================


async def calc(session: AsyncSession, period_type: str = "month", period_value: str | None = None) -> dict:
    """按能耗数据 × 碳因子重新核算碳排放（先清后建）。"""
    factors = await _active_factors(session)
    if not factors:
        raise BizException("未配置生效的碳因子，无法核算")

    await session.execute(delete(CarbonEmission).where(CarbonEmission.period_type == period_type))
    await session.commit()

    today = date.today()
    if period_value:
        months = [datetime.strptime(period_value, "%Y-%m").date().replace(day=1)]
    else:
        months = [_add_months(today.replace(day=1), -i) for i in range(11, -1, -1)]

    inserted = 0
    for m in months:
        m_start, m_end = _dt(m), _dt(_add_months(m, 1))
        pv = f"{m:%Y-%m}"
        for et_id, factor in factors.items():
            rows = (
                await session.execute(
                    select(EnergyStat.area_id, func.coalesce(func.sum(EnergyStat.stat_value), 0))
                    .where(
                        EnergyStat.stat_type == "day",
                        EnergyStat.device_id.is_(None),
                        EnergyStat.energy_type_id == et_id,
                        EnergyStat.stat_time >= m_start,
                        EnergyStat.stat_time < m_end,
                    )
                    .group_by(EnergyStat.area_id)
                )
            ).all()
            total_energy = float(sum(float(r[1]) for r in rows) or 0)
            if total_energy <= 0:
                continue
            session.add(
                CarbonEmission(
                    period_type=period_type,
                    period_value=pv,
                    energy_type_id=et_id,
                    area_id=None,
                    scope=factor.scope,
                    energy_value=round(total_energy, 2),
                    factor_id=factor.id,
                    factor_value=factor.factor_value,
                    emission_value=_to_ton(total_energy, float(factor.factor_value)),
                    unit="tCO2e",
                )
            )
            inserted += 1
            for r in rows:
                if r[0] is None or float(r[1]) <= 0:
                    continue
                session.add(
                    CarbonEmission(
                        period_type=period_type,
                        period_value=pv,
                        energy_type_id=et_id,
                        area_id=r[0],
                        scope=factor.scope,
                        energy_value=round(float(r[1]), 2),
                        factor_id=factor.id,
                        factor_value=factor.factor_value,
                        emission_value=_to_ton(float(r[1]), float(factor.factor_value)),
                        unit="tCO2e",
                    )
                )
                inserted += 1
    await session.commit()
    return {"period_type": period_type, "periods": len(months), "inserted": inserted}


# ==================== 总览 ====================


async def overview(session: AsyncSession, year: int | None = None) -> dict:
    year = year or date.today().year
    type_names = await _maps(session)

    async def _year_rows(y: int):
        return (
            await session.execute(
                select(CarbonEmission).where(
                    CarbonEmission.period_type == "month",
                    CarbonEmission.area_id.is_(None),
                    CarbonEmission.period_value.like(f"{y}-%"),
                )
            )
        ).scalars().all()

    year_rows = await _year_rows(year)
    last_rows = await _year_rows(year - 1)

    total = sum(float(r.emission_value) for r in year_rows)
    last_total = sum(float(r.emission_value) for r in last_rows)

    scope: dict[str, float] = {}
    for r in year_rows:
        scope[r.scope] = scope.get(r.scope, 0.0) + float(r.emission_value)

    monthly: dict[str, float] = {}
    for r in year_rows:
        monthly[r.period_value] = monthly.get(r.period_value, 0.0) + float(r.emission_value)
    months_sorted = sorted(monthly.keys())

    by_type: dict[int, float] = {}
    for r in year_rows:
        by_type[r.energy_type_id] = by_type.get(r.energy_type_id, 0.0) + float(r.emission_value)

    def _scope(key: str) -> float:
        for name, k in SCOPE_KEYS.items():
            if k == key:
                return round(scope.get(name, 0.0), 2)
        return 0.0

    rate = round((total - last_total) / last_total * 100, 2) if last_total else None
    return {
        "cards": {
            "year": year,
            "total": round(total, 2),
            "last_year_total": round(last_total, 2),
            "yoy_rate": rate,
            "scope1": _scope("scope1"),
            "scope2": _scope("scope2"),
            "scope3": _scope("scope3"),
        },
        "scope_ratio": [{"name": k, "value": round(v, 2)} for k, v in scope.items()],
        "type_ratio": [{"name": type_names.get(k, "-"), "value": round(v, 2)} for k, v in by_type.items()],
        "trend": {"months": months_sorted, "values": [round(monthly[k], 2) for k in months_sorted]},
    }


async def page_emissions(
    session: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    period_type: str | None = None,
    area_id: int | None = None,
) -> tuple[int, list[dict]]:
    conds = []
    if period_type:
        conds.append(CarbonEmission.period_type == period_type)
    if area_id is not None:
        conds.append(CarbonEmission.area_id == area_id)

    count_stmt = select(func.count(CarbonEmission.id))
    stmt = select(CarbonEmission)
    for c in conds:
        count_stmt = count_stmt.where(c)
        stmt = stmt.where(c)
    total = int((await session.execute(count_stmt)).scalar_one() or 0)
    stmt = (
        stmt.order_by(CarbonEmission.period_value.desc(), CarbonEmission.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = (await session.execute(stmt)).scalars().all()

    type_names = await _maps(session)
    area_names = {a.id: a.area_name for a in (await session.execute(select(DevArea))).scalars().all()}
    factor_names = {f.id: f.factor_name for f in (await session.execute(select(CfgCarbonFactor))).scalars().all()}

    items = []
    for r in rows:
        item = r.model_dump()
        item["energy_type_name"] = type_names.get(r.energy_type_id)
        item["area_name"] = area_names.get(r.area_id) if r.area_id else "全园区"
        item["factor_name"] = factor_names.get(r.factor_id) if r.factor_id else None
        item["factor_value"] = float(r.factor_value) if r.factor_value is not None else None
        item["energy_value"] = float(r.energy_value) if r.energy_value is not None else 0
        item["emission_value"] = float(r.emission_value) if r.emission_value is not None else 0
        items.append(item)
    return total, items


# ==================== 报告 ====================


async def page_reports(session: AsyncSession, page: int = 1, page_size: int = 20) -> tuple[int, list[dict]]:
    total = int((await session.execute(select(func.count(CarbonReport.id)))).scalar_one() or 0)
    rows = (
        await session.execute(
            select(CarbonReport)
            .order_by(CarbonReport.period_start.desc(), CarbonReport.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).scalars().all()
    items = []
    for r in rows:
        item = r.model_dump()
        item["period_start"] = r.period_start.strftime("%Y-%m-%d") if r.period_start else None
        item["period_end"] = r.period_end.strftime("%Y-%m-%d") if r.period_end else None
        for k in ("total_emission", "reduction_value", "reduction_rate"):
            if item.get(k) is not None:
                item[k] = float(item[k])
        items.append(item)
    return total, items


async def create_report(session: AsyncSession, data: dict) -> dict:
    start, end = data["period_start"], data["period_end"]
    rows = (
        await session.execute(
            select(CarbonEmission).where(
                CarbonEmission.period_type == "month",
                CarbonEmission.area_id.is_(None),
                CarbonEmission.period_value >= f"{start:%Y-%m}",
                CarbonEmission.period_value <= f"{end:%Y-%m}",
            )
        )
    ).scalars().all()
    if not rows:
        raise BizException("该周期内暂无可核算的碳排放数据，请先执行核算")

    total = sum(float(r.emission_value) for r in rows)
    type_names = await _maps(session)
    by_type: dict[str, float] = {}
    by_period: dict[str, float] = {}
    scope_sum: dict[str, float] = {}
    for r in rows:
        name = type_names.get(r.energy_type_id, "-")
        by_type[name] = by_type.get(name, 0.0) + float(r.emission_value)
        by_period[r.period_value] = by_period.get(r.period_value, 0.0) + float(r.emission_value)
        scope_sum[r.scope] = scope_sum.get(r.scope, 0.0) + float(r.emission_value)

    def _s(name: str) -> float:
        return round(scope_sum.get(name, 0.0), 2)

    content = {
        "summary": {
            "total_emission": round(total, 2),
            "scope1": _s("范围一"),
            "scope2": _s("范围二"),
            "scope3": _s("范围三"),
            "unit": "tCO2e",
        },
        "by_period": [{"period": k, "value": round(v, 2)} for k, v in sorted(by_period.items())],
        "by_energy_type": [{"name": k, "value": round(v, 2)} for k, v in by_type.items()],
        "conclusion": f"报告期内共排放 {round(total, 2)} tCO2e，其中范围二（外购电力）占比最高，"
                      f"建议持续加强用能监测与节能改造。",
    }

    report = CarbonReport(
        report_no=f"CR{datetime.now():%Y%m%d%H%M%S}",
        report_name=data["report_name"],
        report_type=data.get("report_type", "month"),
        period_start=start,
        period_end=end,
        total_emission=round(total, 2),
        content_json=content,
    )
    session.add(report)
    await session.commit()
    await session.refresh(report)
    result = report.model_dump()
    for k in ("total_emission", "reduction_value", "reduction_rate"):
        if result.get(k) is not None:
            result[k] = float(result[k])
    result["period_start"] = start.strftime("%Y-%m-%d")
    result["period_end"] = end.strftime("%Y-%m-%d")
    return result


async def export_report(session: AsyncSession, report_id: int) -> tuple[bytes, str]:
    report = await session.get(CarbonReport, report_id)
    if not report:
        raise BizException("报告不存在")

    from openpyxl import Workbook

    content = report.content_json or {}
    summary = content.get("summary", {})
    wb = Workbook()
    ws = wb.active
    ws.title = "碳排放报告"
    ws.append([report.report_name])
    ws.append(["报告周期", f"{report.period_start} ~ {report.period_end}"])
    ws.append(["总排放量(tCO2e)", float(report.total_emission or 0)])
    ws.append(["范围一(tCO2e)", summary.get("scope1", 0)])
    ws.append(["范围二(tCO2e)", summary.get("scope2", 0)])
    ws.append(["范围三(tCO2e)", summary.get("scope3", 0)])
    ws.append([])
    ws.append(["分期排放明细"])
    ws.append(["周期", "排放量(tCO2e)"])
    for x in content.get("by_period", []):
        ws.append([x["period"], x["value"]])
    ws.append([])
    ws.append(["按能源类型"])
    ws.append(["能源类型", "排放量(tCO2e)"])
    for x in content.get("by_energy_type", []):
        ws.append([x["name"], x["value"]])
    ws.append([])
    ws.append(["结论", content.get("conclusion", "")])

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue(), report.report_name


async def reduction_compare(session: AsyncSession) -> dict:
    """减排对比：同比 + 光伏替代减排 + 分能源类型对比。"""
    year = date.today().year

    async def _year_total(y: int) -> float:
        stmt = select(func.coalesce(func.sum(CarbonEmission.emission_value), 0)).where(
            CarbonEmission.period_type == "month",
            CarbonEmission.area_id.is_(None),
            CarbonEmission.period_value.like(f"{y}-%"),
        )
        return float((await session.execute(stmt)).scalar_one() or 0)

    cur_total = await _year_total(year)
    last_total = await _year_total(year - 1)

    # 光伏发电量（当年）× 光伏减排因子
    pv_type = (await session.execute(select(CfgEnergyType).where(CfgEnergyType.type_code == "pv"))).scalars().first()
    pv_factor_row = (
        await session.execute(
            select(CfgCarbonFactor).where(CfgCarbonFactor.scope == REDUCTION_SCOPE, CfgCarbonFactor.status == 1)
        )
    ).scalars().first()
    pv_factor = float(pv_factor_row.factor_value) if pv_factor_row else 0.0
    pv_energy = 0.0
    if pv_type:
        pv_energy = float(
            (
                await session.execute(
                    select(func.coalesce(func.sum(EnergyStat.stat_value), 0)).where(
                        EnergyStat.stat_type == "day",
                        EnergyStat.device_id.is_(None),
                        EnergyStat.energy_type_id == pv_type.id,
                        EnergyStat.stat_time >= _dt(date(year, 1, 1)),
                    )
                )
            ).scalar_one()
            or 0
        )

    type_names = await _maps(session)

    async def _by_type(y: int) -> dict[int, float]:
        rows = (
            await session.execute(
                select(CarbonEmission.energy_type_id, func.coalesce(func.sum(CarbonEmission.emission_value), 0))
                .where(
                    CarbonEmission.period_type == "month",
                    CarbonEmission.area_id.is_(None),
                    CarbonEmission.period_value.like(f"{y}-%"),
                )
                .group_by(CarbonEmission.energy_type_id)
            )
        ).all()
        return {r[0]: round(float(r[1]), 2) for r in rows}

    cur_by_type = await _by_type(year)
    last_by_type = await _by_type(year - 1)
    keys = set(cur_by_type) | set(last_by_type)
    type_compare = [
        {"name": type_names.get(k, "-"), "current": cur_by_type.get(k, 0), "last": last_by_type.get(k, 0)}
        for k in keys
    ]

    return {
        "current_year": year,
        "current_total": round(cur_total, 2),
        "last_year_total": round(last_total, 2),
        "yoy_rate": round((cur_total - last_total) / last_total * 100, 2) if last_total else None,
        "reduction": round(abs(cur_total - last_total), 2),
        "pv_energy": round(pv_energy, 2),
        "pv_reduction": round(pv_energy * pv_factor / 1000, 2),
        "type_compare": type_compare,
    }
