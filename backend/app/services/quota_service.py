"""节能定额域服务（B6 定额/监控/考核）。"""

from datetime import date, datetime, time

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cfg import CfgEnergyType
from app.models.dev import DevArea, DevDevice
from app.models.energy import EnergyStat
from app.models.notify import NotifyMessage
from app.models.quota import EnergyQuota, QuotaAssess, QuotaMonitor
from app.models.sys import SysUser


def _dt(d: date, hour: int = 0) -> datetime:
    return datetime.combine(d, time(hour=hour)).astimezone()


def _current_month() -> str:
    return f"{date.today():%Y-%m}"


def _period_range(period_value: str) -> tuple[datetime, datetime]:
    """把 'YYYY-MM' 转为 [月初, 次月初) 的时间区间。"""
    year, month = int(period_value[:4]), int(period_value[5:7])
    start = _dt(date(year, month, 1))
    end = _dt(date(year + 1, 1, 1)) if month == 12 else _dt(date(year, month + 1, 1))
    return start, end


async def _energy_type_names(session: AsyncSession) -> dict[int, str]:
    return {t.id: t.type_name for t in (await session.execute(select(CfgEnergyType))).scalars().all()}


async def _target_maps(session: AsyncSession) -> tuple[dict[int, str], dict[int, str]]:
    area_names = {a.id: a.area_name for a in (await session.execute(select(DevArea))).scalars().all()}
    device_names = {d.id: d.device_name for d in (await session.execute(select(DevDevice))).scalars().all()}
    return area_names, device_names


def _resolve_target_name(
    quota: EnergyQuota, area_names: dict[int, str], device_names: dict[int, str]
) -> str | None:
    """按定额类型解析考核/展示对象名称。"""
    if quota.quota_type == "area":
        return "全园区" if quota.target_id is None else area_names.get(quota.target_id)
    if quota.quota_type == "device":
        return device_names.get(quota.target_id)
    return None


async def _quota_actual(session: AsyncSession, quota: EnergyQuota, start: datetime, end: datetime) -> float:
    """按定额维度聚合 EnergyStat 得到实际值（仅日统计）。"""
    conds = [EnergyStat.stat_type == "day", EnergyStat.stat_time >= start, EnergyStat.stat_time < end]
    if quota.energy_type_id is not None:
        conds.append(EnergyStat.energy_type_id == quota.energy_type_id)
    if quota.quota_type == "device":
        conds.append(EnergyStat.device_id == quota.target_id)
    else:
        # 区域维度取设备为空的总表；分项维度再按分项过滤
        conds.append(EnergyStat.device_id.is_(None))
        if quota.quota_type == "item":
            conds.append(EnergyStat.energy_item_id == quota.target_id)
        elif quota.quota_type == "area" and quota.target_id is not None:
            conds.append(EnergyStat.area_id == quota.target_id)
    stmt = select(func.coalesce(func.sum(EnergyStat.stat_value), 0)).where(*conds)
    return float((await session.execute(stmt)).scalar_one() or 0)


# ==================== 定额 ====================


async def page_quotas(
    session: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    quota_type: str | None = None,
    energy_type_id: int | None = None,
    period_type: str | None = None,
    keyword: str | None = None,
) -> tuple[int, list[dict]]:
    conds = []
    if quota_type:
        conds.append(EnergyQuota.quota_type == quota_type)
    if energy_type_id is not None:
        conds.append(EnergyQuota.energy_type_id == energy_type_id)
    if period_type:
        conds.append(EnergyQuota.period_type == period_type)
    if keyword:
        conds.append(EnergyQuota.quota_name.ilike(f"%{keyword}%"))

    count_stmt = select(func.count(EnergyQuota.id))
    stmt = select(EnergyQuota)
    for c in conds:
        count_stmt = count_stmt.where(c)
        stmt = stmt.where(c)
    total = int((await session.execute(count_stmt)).scalar_one() or 0)
    rows = (
        await session.execute(stmt.order_by(EnergyQuota.id).offset((page - 1) * page_size).limit(page_size))
    ).scalars().all()

    type_names = await _energy_type_names(session)
    area_names, device_names = await _target_maps(session)
    parent_names = {
        q.id: q.quota_name for q in (await session.execute(select(EnergyQuota))).scalars().all()
    }

    items = []
    for r in rows:
        item = r.model_dump()
        item["energy_type_name"] = type_names.get(r.energy_type_id) if r.energy_type_id else None
        item["target_name"] = _resolve_target_name(r, area_names, device_names)
        item["parent_name"] = parent_names.get(r.parent_id) if r.parent_id else None
        item["quota_value"] = float(r.quota_value) if r.quota_value is not None else None
        items.append(item)
    return total, items


async def quota_tree(session: AsyncSession) -> list[dict]:
    """按 parent_id 组装定额树：园区总定额 → 区域/设备子定额。"""
    quotas = (await session.execute(select(EnergyQuota).order_by(EnergyQuota.id))).scalars().all()
    type_names = await _energy_type_names(session)
    area_names, device_names = await _target_maps(session)

    nodes = {}
    for q in quotas:
        item = q.model_dump()
        item["energy_type_name"] = type_names.get(q.energy_type_id) if q.energy_type_id else None
        item["target_name"] = _resolve_target_name(q, area_names, device_names)
        item["quota_value"] = float(q.quota_value) if q.quota_value is not None else None
        item["children"] = []
        nodes[q.id] = item

    tree: list[dict] = []
    for q in quotas:
        node = nodes[q.id]
        parent = nodes.get(q.parent_id) if q.parent_id else None
        if parent:
            parent["children"].append(node)
        else:
            tree.append(node)
    return tree


# ==================== 监控 ====================


async def refresh_monitor(
    session: AsyncSession, period_value: str | None = None, user_id: int | None = None
) -> dict:
    """按周期重算各定额实际值，写入监控记录（先清后建，保证幂等）。"""
    period_value = period_value or _current_month()
    start, end = _period_range(period_value)
    quotas = (await session.execute(select(EnergyQuota))).scalars().all()

    await session.execute(delete(QuotaMonitor).where(QuotaMonitor.period_value == period_value))
    await session.commit()

    admin = (await session.execute(select(SysUser).where(SysUser.username == "admin"))).scalars().first()
    now = datetime.now().astimezone()
    monitor_count = 0
    exceed_count = 0
    for q in quotas:
        actual = await _quota_actual(session, q, start, end)
        quota_value = float(q.quota_value or 0)
        rate = round(actual / quota_value * 100, 4) if quota_value > 0 else 0.0
        deviation = round((actual - quota_value) / quota_value * 100, 4) if quota_value > 0 else 0.0
        if rate <= 100:
            warn_status = "normal"
        elif rate <= 110:
            warn_status = "warning"
        else:
            warn_status = "exceed"

        session.add(
            QuotaMonitor(
                quota_id=q.id,
                period_value=period_value,
                actual_value=round(actual, 4),
                complete_rate=rate,
                deviation=deviation,
                warn_status=warn_status,
                stat_time=now,
            )
        )
        monitor_count += 1

        # 超定额 → 向 admin 写入预警通知（仅在超标时生成，避免重复刷屏）
        if warn_status == "exceed":
            exceed_count += 1
            if admin:
                session.add(
                    NotifyMessage(
                        title="定额超标预警",
                        content=(
                            f"定额「{q.quota_name}」在 {period_value} 实际值 {round(actual, 2)}{q.unit or ''}，"
                            f"超出定额 {quota_value}{q.unit or ''}，偏差 {deviation}%，请及时处理。"
                        ),
                        msg_type="internal",
                        level="warning",
                        receiver_id=admin.id,
                        send_time=now,
                    )
                )
    await session.commit()
    return {"monitor_count": monitor_count, "exceed_count": exceed_count, "notified": exceed_count if admin else 0}


async def page_monitors(
    session: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    warn_status: str | None = None,
    period_value: str | None = None,
) -> tuple[int, list[dict]]:
    conds = []
    if warn_status:
        conds.append(QuotaMonitor.warn_status == warn_status)
    if period_value:
        conds.append(QuotaMonitor.period_value == period_value)

    count_stmt = select(func.count(QuotaMonitor.id))
    stmt = select(QuotaMonitor)
    for c in conds:
        count_stmt = count_stmt.where(c)
        stmt = stmt.where(c)
    total = int((await session.execute(count_stmt)).scalar_one() or 0)
    rows = (
        await session.execute(
            stmt.order_by(QuotaMonitor.period_value.desc(), QuotaMonitor.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).scalars().all()

    quota_map = {q.id: q for q in (await session.execute(select(EnergyQuota))).scalars().all()}
    items = []
    for r in rows:
        q = quota_map.get(r.quota_id)
        item = r.model_dump()
        item["quota_name"] = q.quota_name if q else None
        item["quota_type"] = q.quota_type if q else None
        item["unit"] = q.unit if q else None
        item["quota_value"] = float(q.quota_value) if q and q.quota_value is not None else None
        item["actual_value"] = float(r.actual_value) if r.actual_value is not None else 0
        item["complete_rate"] = float(r.complete_rate) if r.complete_rate is not None else 0
        item["deviation"] = float(r.deviation) if r.deviation is not None else 0
        items.append(item)
    return total, items


# ==================== 考核 ====================


async def generate_assess(session: AsyncSession, period_value: str, user_id: int | None = None) -> dict:
    """按周期对每条定额生成考核结果（先清后建）。"""
    start, end = _period_range(period_value)
    await session.execute(delete(QuotaAssess).where(QuotaAssess.period_value == period_value))
    await session.commit()

    quotas = (await session.execute(select(EnergyQuota))).scalars().all()
    area_names, device_names = await _target_maps(session)
    now = datetime.now().astimezone()

    count = 0
    for q in quotas:
        actual = await _quota_actual(session, q, start, end)
        quota_value = float(q.quota_value or 0)
        over = (actual - quota_value) / quota_value * 100 if quota_value > 0 else 0.0
        score = max(0.0, min(100.0, round(100 - max(over, 0.0), 2)))
        if score >= 90:
            grade, assess_result = "A", "优秀"
        elif score >= 80:
            grade, assess_result = "B", "合格"
        elif score >= 70:
            grade, assess_result = "C", "预警"
        else:
            grade, assess_result = "D", "超标"

        session.add(
            QuotaAssess(
                assess_name=f"{q.quota_name}({period_value})考核",
                target_id=q.target_id,
                target_name=_resolve_target_name(q, area_names, device_names),
                period_value=period_value,
                quota_value=q.quota_value,
                actual_value=round(actual, 4),
                score=score,
                grade=grade,
                assess_result=assess_result,
                assess_time=now,
                operator_id=user_id,
            )
        )
        count += 1
    await session.commit()
    return {"count": count}


def _assess_item(r: QuotaAssess) -> dict:
    item = r.model_dump()
    for k in ("quota_value", "actual_value", "score"):
        item[k] = float(item[k]) if item.get(k) is not None else None
    item["assess_time"] = r.assess_time.strftime("%Y-%m-%d %H:%M:%S") if r.assess_time else None
    item["created_at"] = r.created_at.strftime("%Y-%m-%d %H:%M:%S") if r.created_at else None
    return item


async def page_assess(
    session: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    period_value: str | None = None,
) -> tuple[int, list[dict]]:
    conds = []
    if period_value:
        conds.append(QuotaAssess.period_value == period_value)

    count_stmt = select(func.count(QuotaAssess.id))
    stmt = select(QuotaAssess)
    for c in conds:
        count_stmt = count_stmt.where(c)
        stmt = stmt.where(c)
    total = int((await session.execute(count_stmt)).scalar_one() or 0)
    rows = (
        await session.execute(
            stmt.order_by(QuotaAssess.period_value.desc(), QuotaAssess.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).scalars().all()
    return total, [_assess_item(r) for r in rows]


async def assess_report(session: AsyncSession, year: int | None = None) -> dict:
    """考核报表：统计卡片 + 等级分布 + 评分趋势 + 明细列表。"""
    year = year or date.today().year
    rows = (
        await session.execute(
            select(QuotaAssess)
            .where(QuotaAssess.period_value.like(f"{year}-%"))
            .order_by(QuotaAssess.period_value, QuotaAssess.id)
        )
    ).scalars().all()

    scores = [float(r.score or 0) for r in rows]
    avg_score = round(sum(scores) / len(scores), 2) if scores else 0

    grade_counts = {"A": 0, "B": 0, "C": 0, "D": 0}
    period_scores: dict[str, list[float]] = {}
    exceed_count = 0
    for r in rows:
        if r.grade in grade_counts:
            grade_counts[r.grade] += 1
        period_scores.setdefault(r.period_value or "", []).append(float(r.score or 0))
        if r.assess_result == "超标":
            exceed_count += 1

    periods = sorted(period_scores.keys())
    values = [round(sum(period_scores[p]) / len(period_scores[p]), 2) for p in periods]

    return {
        "cards": {
            "avg_score": avg_score,
            "a_count": grade_counts["A"],
            "exceed_count": exceed_count,
            "assess_count": len(rows),
        },
        "grade_ratio": [{"name": g, "value": grade_counts[g]} for g in ("A", "B", "C", "D")],
        "score_trend": {"periods": periods, "values": values},
        "list": [_assess_item(r) for r in reversed(rows)],
    }
