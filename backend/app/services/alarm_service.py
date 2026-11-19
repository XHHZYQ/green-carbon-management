"""告警域服务（B6 告警中心：列表/详情/确认/处理/统计/转工单）。"""

from datetime import date, datetime, time, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BizException
from app.models.alarm import AlarmInfo, AlarmRule
from app.models.cfg import CfgSystemParam
from app.models.dev import DevDevice
from app.models.sys import SysUser
from app.models.wo import WoWorkOrder

# 告警等级 / 状态中文名（用于统计图例）
LEVEL_NAMES = {"critical": "紧急", "major": "重要", "minor": "次要", "info": "提示"}
STATUS_NAMES = {"pending": "待确认", "confirmed": "已确认", "handled": "已处理", "ignored": "已忽略"}


def _day_start(d: date) -> datetime:
    return datetime.combine(d, time.min).astimezone()


async def _device_names(session: AsyncSession) -> dict[int, str]:
    rows = (await session.execute(select(DevDevice))).scalars().all()
    return {d.id: d.device_name for d in rows}


async def _rule_names(session: AsyncSession) -> dict[int, str]:
    rows = (await session.execute(select(AlarmRule))).scalars().all()
    return {r.id: r.rule_name for r in rows}


async def _user_names(session: AsyncSession) -> dict[int, str]:
    rows = (await session.execute(select(SysUser))).scalars().all()
    return {u.id: (u.real_name or u.username) for u in rows}


def _to_dict(row: AlarmInfo, device_names: dict, rule_names: dict, user_names: dict | None = None) -> dict:
    item = row.model_dump()
    item["device_name"] = device_names.get(row.device_id)
    item["rule_name"] = rule_names.get(row.rule_id)
    if user_names is not None:
        item["confirm_user_name"] = user_names.get(row.confirm_by) if row.confirm_by else None
    return item


# ==================== 列表 / 详情 ====================


async def page_alarms(
    session: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    level: str | None = None,
    status: str | None = None,
    alarm_type: str | None = None,
    device_id: int | None = None,
    keyword: str | None = None,
) -> tuple[int, list[dict]]:
    conds = []
    if level:
        conds.append(AlarmInfo.alarm_level == level)
    if status:
        conds.append(AlarmInfo.status == status)
    if alarm_type:
        conds.append(AlarmInfo.alarm_type == alarm_type)
    if device_id:
        conds.append(AlarmInfo.device_id == device_id)
    if keyword:
        conds.append(or_(AlarmInfo.alarm_no.ilike(f"%{keyword}%"), AlarmInfo.content.ilike(f"%{keyword}%")))

    count_stmt = select(func.count(AlarmInfo.id))
    stmt = select(AlarmInfo)
    for c in conds:
        count_stmt = count_stmt.where(c)
        stmt = stmt.where(c)
    total = int((await session.execute(count_stmt)).scalar_one() or 0)
    rows = (
        await session.execute(
            stmt.order_by(AlarmInfo.alarm_time.desc(), AlarmInfo.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).scalars().all()

    device_names = await _device_names(session)
    rule_names = await _rule_names(session)
    items = [_to_dict(r, device_names, rule_names) for r in rows]
    return total, items


async def get_alarm(session: AsyncSession, alarm_id: int) -> dict:
    row = await session.get(AlarmInfo, alarm_id)
    if not row:
        raise BizException("告警不存在")
    return _to_dict(row, await _device_names(session), await _rule_names(session), await _user_names(session))


# ==================== 确认 / 处理 ====================


async def confirm_alarm(session: AsyncSession, alarm_id: int, user_id: int) -> dict:
    alarm = await session.get(AlarmInfo, alarm_id)
    if not alarm:
        raise BizException("告警不存在")
    if alarm.status == "pending":
        alarm.status = "confirmed"
        alarm.confirm_by = user_id
        alarm.confirm_time = datetime.now().astimezone()
        session.add(alarm)
        await session.commit()
        await session.refresh(alarm)

    # 紧急告警按系统参数自动转工单
    param = (
        await session.execute(select(CfgSystemParam).where(CfgSystemParam.param_key == "alarm.auto_work_order"))
    ).scalars().first()
    if param and (param.param_value or "").lower() == "true" and alarm.alarm_level == "critical":
        exists = (await session.execute(select(WoWorkOrder).where(WoWorkOrder.alarm_id == alarm.id))).scalars().first()
        if not exists:
            await create_work_order_from_alarm(session, alarm.id, user_id)
    return await get_alarm(session, alarm_id)


async def handle_alarm(session: AsyncSession, alarm_id: int, user_id: int) -> dict:
    alarm = await session.get(AlarmInfo, alarm_id)
    if not alarm:
        raise BizException("告警不存在")
    alarm.status = "handled"
    if not alarm.confirm_by:
        alarm.confirm_by = user_id
        alarm.confirm_time = datetime.now().astimezone()
    session.add(alarm)
    await session.commit()
    await session.refresh(alarm)
    return await get_alarm(session, alarm_id)


# ==================== 统计 ====================


async def alarm_statistics(session: AsyncSession) -> dict:
    today_start = _day_start(date.today())

    total = int((await session.execute(select(func.count(AlarmInfo.id)))).scalar_one() or 0)
    pending = int(
        (await session.execute(select(func.count(AlarmInfo.id)).where(AlarmInfo.status == "pending"))).scalar_one() or 0
    )
    today = int(
        (
            await session.execute(select(func.count(AlarmInfo.id)).where(AlarmInfo.alarm_time >= today_start))
        ).scalar_one()
        or 0
    )

    level_rows = (
        await session.execute(select(AlarmInfo.alarm_level, func.count(AlarmInfo.id)).group_by(AlarmInfo.alarm_level))
    ).all()
    level_map = {r[0]: int(r[1]) for r in level_rows}
    by_level = [{"name": LEVEL_NAMES[k], "value": level_map[k]} for k in LEVEL_NAMES if k in level_map]

    status_rows = (
        await session.execute(select(AlarmInfo.status, func.count(AlarmInfo.id)).group_by(AlarmInfo.status))
    ).all()
    status_map = {r[0]: int(r[1]) for r in status_rows}
    by_status = [{"name": STATUS_NAMES[k], "value": status_map[k]} for k in STATUS_NAMES if k in status_map]

    type_rows = (
        await session.execute(
            select(AlarmInfo.alarm_type, func.count(AlarmInfo.id))
            .group_by(AlarmInfo.alarm_type)
            .order_by(func.count(AlarmInfo.id).desc())
        )
    ).all()
    by_type = [{"name": r[0] or "其他", "value": int(r[1])} for r in type_rows]

    # 近 7 天每日新增告警
    start = date.today() - timedelta(days=6)
    dd_expr = func.to_char(AlarmInfo.alarm_time, "MM-DD")
    trend_rows = (
        await session.execute(
            select(dd_expr, func.count(AlarmInfo.id))
            .where(AlarmInfo.alarm_time >= _day_start(start))
            .group_by(dd_expr)
        )
    ).all()
    count_map = {r[0]: int(r[1]) for r in trend_rows}
    days, values = [], []
    for i in range(7):
        d = start + timedelta(days=i)
        key = d.strftime("%m-%d")
        days.append(key)
        values.append(count_map.get(key, 0))

    return {
        "total": total,
        "pending": pending,
        "today": today,
        "by_level": by_level,
        "by_status": by_status,
        "by_type": by_type,
        "trend": {"days": days, "values": values},
    }


# ==================== 告警转工单 ====================


async def create_work_order_from_alarm(session: AsyncSession, alarm_id: int, user_id: int) -> dict:
    alarm = await session.get(AlarmInfo, alarm_id)
    if not alarm:
        raise BizException("告警不存在")
    device_names = await _device_names(session)
    device_name = device_names.get(alarm.device_id)
    now = datetime.now().astimezone()
    title = alarm.content or f"{device_name or '设备'} 告警处理"
    wo = WoWorkOrder(
        order_no=f"WO{now:%Y%m%d%H%M%S}",
        title=title[:128],
        type="维修",
        source="alarm",
        alarm_id=alarm.id,
        device_id=alarm.device_id,
        level=alarm.alarm_level,
        status="pending",
        creator_id=user_id,
        content=alarm.content,
        create_time=now,
        created_at=now,
    )
    session.add(wo)
    await session.commit()
    await session.refresh(wo)
    item = wo.model_dump()
    item["device_name"] = device_name
    item["assignee_name"] = None
    return item
