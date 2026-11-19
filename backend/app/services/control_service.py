"""控制域服务（B4-1 设备控制）。

负责：控制面板数据、单台/批量下发、控制记录、定时任务管理；
以及调度器驱动的异步状态流转（待下发→下发中→成功/失败/超时）与定时到点下发。
"""

import random
from datetime import datetime

from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BizException
from app.core.pagination import PageParams, paginate_query
from app.db.session import SessionLocal
from app.models.ctrl import CtrlCommand, CtrlTimedTask
from app.models.dev import DevArea, DevControlPoint, DevData, DevDevice, DevPoint

CRON_TZ = "Asia/Shanghai"

# 控制点 -> 可映射的测点编码（用于下发成功后同步写入采集数据，按优先级取第一个存在的测点）
CTRL_TO_POINT: dict[str, list[str]] = {
    "switch": ["RunStatus", "Power", "ActivePower"],
    "brightness_set": ["Brightness"],
    "setpoint": ["SupplyTemp"],
    "frequency": ["FanSpeed", "Flow"],
}

# 状态中文
STATUS_TEXT = {"pending": "待下发", "sending": "下发中", "success": "执行成功", "fail": "执行失败", "timeout": "超时"}

# 下发中 -> 结果 的模拟等待时长（秒）
SENDING_SECONDS = 1.5


def _now() -> datetime:
    return datetime.now().astimezone()


def _gen_no(now: datetime) -> str:
    return f"CMD{now:%Y%m%d%H%M%S}{random.randint(100, 999)}"


def next_cron_time(cron_expr: str | None, base: datetime) -> datetime | None:
    """按 5 段 cron 表达式计算下次执行时间。"""
    if not cron_expr:
        return None
    try:
        trigger = CronTrigger.from_crontab(cron_expr, timezone=CRON_TZ)
        return trigger.get_next_fire_time(None, base)
    except Exception:  # noqa: BLE001
        return None


def _to_number(target_value: str | None) -> float | None:
    if target_value is None:
        return None
    try:
        return float(target_value)
    except ValueError:
        mapping = {"on": 1.0, "open": 1.0, "start": 1.0, "off": 0.0, "close": 0.0, "stop": 0.0}
        return mapping.get(str(target_value).lower())


# ==================== 控制面板 ====================


async def _latest_values(session: AsyncSession, device_ids: list[int]) -> dict[tuple[int, str], str]:
    """取每个设备+控制点最近一次成功下发的目标值。"""
    if not device_ids:
        return {}
    stmt = (
        select(CtrlCommand)
        .where(
            CtrlCommand.device_id.in_(device_ids),
            CtrlCommand.status == "success",
            CtrlCommand.point_key.is_not(None),
        )
        .distinct(CtrlCommand.device_id, CtrlCommand.point_key)
        .order_by(
            CtrlCommand.device_id,
            CtrlCommand.point_key,
            CtrlCommand.send_time.desc().nullslast(),
            CtrlCommand.id.desc(),
        )
    )
    rows = (await session.execute(stmt)).scalars().all()
    return {(r.device_id, r.point_key): r.target_value for r in rows}


async def control_points(
    session: AsyncSession,
    device_id: int | None = None,
    area_id: int | None = None,
    keyword: str | None = None,
) -> list[dict]:
    """返回「设备 + 其可控点」列表，供控制面板渲染。"""
    ctrl_dev_ids = (await session.execute(select(DevControlPoint.device_id).distinct())).scalars().all()
    ctrl_dev_ids = [i for i in ctrl_dev_ids if i]
    if not ctrl_dev_ids:
        return []

    stmt = select(DevDevice).where(DevDevice.id.in_(ctrl_dev_ids))
    if device_id:
        stmt = stmt.where(DevDevice.id == device_id)
    if area_id:
        stmt = stmt.where(DevDevice.area_id == area_id)
    if keyword:
        stmt = stmt.where(DevDevice.device_name.ilike(f"%{keyword}%"))
    devices = (await session.execute(stmt.order_by(DevDevice.id))).scalars().all()
    if not devices:
        return []

    dev_ids = [d.id for d in devices]
    points = (
        await session.execute(
            select(DevControlPoint)
            .where(DevControlPoint.device_id.in_(dev_ids), DevControlPoint.status == 1)
            .order_by(DevControlPoint.device_id, DevControlPoint.sort_no)
        )
    ).scalars().all()
    latest = await _latest_values(session, dev_ids)
    area_names = {a.id: a.area_name for a in (await session.execute(select(DevArea))).scalars().all()}

    grouped: dict[int, list[dict]] = {}
    for p in points:
        grouped.setdefault(p.device_id, []).append(
            {
                "point_key": p.point_key,
                "point_name": p.point_name,
                "point_type": p.point_type,
                "value_min": float(p.value_min) if p.value_min is not None else None,
                "value_max": float(p.value_max) if p.value_max is not None else None,
                "enum_options": p.enum_options,
                "dangerous": p.dangerous,
                "current_value": latest.get((p.device_id, p.point_key)),
            }
        )

    return [
        {
            "device_id": d.id,
            "device_code": d.device_code,
            "device_name": d.device_name,
            "area_name": area_names.get(d.area_id),
            "online_status": d.online_status,
            "points": grouped.get(d.id, []),
        }
        for d in devices
    ]


# ==================== 下发 ====================


async def _check_device_point(session: AsyncSession, device_id: int, point_key: str) -> None:
    device = await session.get(DevDevice, device_id)
    if not device:
        raise BizException(f"设备不存在（ID={device_id}）")
    exists = (
        await session.execute(
            select(DevControlPoint).where(
                DevControlPoint.device_id == device_id, DevControlPoint.point_key == point_key
            )
        )
    ).scalars().first()
    if not exists:
        raise BizException(f"设备 {device.device_name} 不存在控制点 {point_key}")


def _new_command(
    device_id: int,
    point_key: str,
    target_value: str,
    operator_id: int | None,
    now: datetime,
    priority: str = "normal",
    exec_mode: str = "immediate",
    schedule_time: datetime | None = None,
    timeout_sec: int = 10,
    need_confirm: bool = False,
    source: str = "manual",
) -> CtrlCommand:
    return CtrlCommand(
        command_no=_gen_no(now),
        device_id=device_id,
        point_key=point_key,
        target_value=str(target_value),
        priority=priority,
        exec_mode=exec_mode,
        schedule_time=schedule_time,
        timeout_sec=timeout_sec,
        need_confirm=need_confirm,
        source=source,
        status="pending",
        operator_id=operator_id,
    )


async def send_command(session: AsyncSession, payload, operator_id: int | None) -> dict:
    await _check_device_point(session, payload.device_id, payload.point_key)
    now = _now()
    cmd = _new_command(
        payload.device_id,
        payload.point_key,
        payload.target_value,
        operator_id,
        now,
        priority=payload.priority,
        exec_mode=payload.exec_mode,
        schedule_time=payload.schedule_time,
        timeout_sec=payload.timeout_sec,
        need_confirm=payload.need_confirm,
        source=payload.source,
    )
    session.add(cmd)
    await session.commit()
    await session.refresh(cmd)
    return _command_dict(cmd)


async def send_batch(session: AsyncSession, payload, operator_id: int | None) -> dict:
    if not payload.items:
        raise BizException("请至少选择一个控制点")
    now = _now()
    for item in payload.items:
        await _check_device_point(session, item.device_id, item.point_key)
        session.add(
            _new_command(
                item.device_id, item.point_key, item.target_value, operator_id, now,
                priority=payload.priority, need_confirm=payload.need_confirm, source="batch",
            )
        )
    await session.commit()
    return {"count": len(payload.items)}


# ==================== 控制记录 ====================


def _command_dict(cmd: CtrlCommand) -> dict:
    data = cmd.model_dump()
    data["status_text"] = STATUS_TEXT.get(cmd.status, cmd.status)
    return data


async def page_commands(
    session: AsyncSession,
    params: PageParams,
    keyword: str | None = None,
    device_id: int | None = None,
    status: str | None = None,
    source: str | None = None,
) -> dict:
    stmt = select(CtrlCommand)
    if device_id:
        stmt = stmt.where(CtrlCommand.device_id == device_id)
    if status:
        stmt = stmt.where(CtrlCommand.status == status)
    if source:
        stmt = stmt.where(CtrlCommand.source == source)
    if keyword:
        stmt = stmt.where(CtrlCommand.command_no.ilike(f"%{keyword}%"))
    stmt = stmt.order_by(CtrlCommand.id.desc())
    total, rows = await paginate_query(session, stmt, params)

    device_ids = [r.device_id for r in rows if r.device_id]
    devs = {
        d.id: d
        for d in (await session.execute(select(DevDevice).where(DevDevice.id.in_(device_ids)))).scalars().all()
    } if device_ids else {}

    items = []
    for r in rows:
        item = _command_dict(r)
        dev = devs.get(r.device_id)
        item["device_name"] = dev.device_name if dev else None
        item["device_code"] = dev.device_code if dev else None
        items.append(item)
    return {"total": total, "items": items}


async def get_command(session: AsyncSession, command_id: int) -> dict:
    cmd = await session.get(CtrlCommand, command_id)
    if not cmd:
        raise BizException("控制记录不存在")
    return _command_dict(cmd)


# ==================== 定时任务 ====================


async def page_timed_tasks(
    session: AsyncSession,
    params: PageParams,
    keyword: str | None = None,
    device_id: int | None = None,
) -> dict:
    stmt = select(CtrlTimedTask)
    if device_id:
        stmt = stmt.where(CtrlTimedTask.device_id == device_id)
    if keyword:
        stmt = stmt.where(CtrlTimedTask.task_name.ilike(f"%{keyword}%"))
    stmt = stmt.order_by(CtrlTimedTask.id.desc())
    total, rows = await paginate_query(session, stmt, params)

    device_ids = [r.device_id for r in rows if r.device_id]
    devs = {
        d.id: d
        for d in (await session.execute(select(DevDevice).where(DevDevice.id.in_(device_ids)))).scalars().all()
    } if device_ids else {}

    items = []
    for r in rows:
        item = r.model_dump()
        dev = devs.get(r.device_id)
        item["device_name"] = dev.device_name if dev else None
        items.append(item)
    return {"total": total, "items": items}


async def save_timed_task(session: AsyncSession, task_id: int | None, data: dict, operator_id: int | None) -> dict:
    if task_id:
        task = await session.get(CtrlTimedTask, task_id)
        if not task:
            raise BizException("定时任务不存在")
    else:
        task = CtrlTimedTask(task_name="", operator_id=operator_id)

    for key, value in data.items():
        setattr(task, key, value)
    if task.enable_status == 1:
        task.next_run_time = next_cron_time(task.cron_expr, _now())
    else:
        task.next_run_time = None
    session.add(task)
    await session.commit()
    await session.refresh(task)
    return task.model_dump()


async def delete_timed_task(session: AsyncSession, task_id: int) -> None:
    task = await session.get(CtrlTimedTask, task_id)
    if not task:
        raise BizException("定时任务不存在")
    await session.delete(task)
    await session.commit()


# ==================== 调度器驱动 ====================


async def _write_control_data(session: AsyncSession, device_id: int, point_key: str, target_value: str, now: datetime) -> None:
    """下发成功后，把目标值同步写入对应测点的采集数据。"""
    candidates = CTRL_TO_POINT.get(point_key or "")
    if not candidates:
        return
    pts = (
        await session.execute(
            select(DevPoint).where(DevPoint.device_id == device_id, DevPoint.point_code.in_(candidates))
        )
    ).scalars().all()
    if not pts:
        return
    by_code = {p.point_code: p for p in pts}
    point = next((by_code[c] for c in candidates if c in by_code), None)
    if not point:
        return
    value = _to_number(target_value)
    session.add(
        DevData(
            device_id=device_id,
            point_id=point.id,
            collect_value=value if value is not None else 1,
            unit=point.unit,
            data_quality="normal",
            collect_time=now,
        )
    )


async def _finalize(session: AsyncSession, cmd: CtrlCommand, now: datetime) -> None:
    """下发中 -> 结果（成功/失败/超时）。"""
    roll = random.random()
    if roll < 0.9:
        cmd.status = "success"
        cmd.fail_reason = None
        await _write_control_data(session, cmd.device_id, cmd.point_key, cmd.target_value, now)
    elif roll < 0.96:
        cmd.status = "fail"
        cmd.fail_reason = random.choice(["设备未响应", "指令被拒绝", "控制点当前不可用"])
    else:
        cmd.status = "timeout"
        cmd.fail_reason = "通信超时，未在规定时间内收到响应"
    cmd.finish_time = now
    session.add(cmd)


async def drive_commands() -> int:
    """调度任务：推进控制指令状态（待下发→下发中→结果）。"""
    async with SessionLocal() as session:
        now = _now()
        pending = (await session.execute(select(CtrlCommand).where(CtrlCommand.status == "pending"))).scalars().all()
        for cmd in pending:
            if cmd.exec_mode == "timed" and cmd.schedule_time and cmd.schedule_time > now:
                continue
            cmd.status = "sending"
            cmd.send_time = now
            session.add(cmd)

        sending = (await session.execute(select(CtrlCommand).where(CtrlCommand.status == "sending"))).scalars().all()
        finished = 0
        for cmd in sending:
            if cmd.send_time and (now - cmd.send_time).total_seconds() < SENDING_SECONDS:
                continue
            await _finalize(session, cmd, now)
            finished += 1

        await session.commit()
        return finished


async def run_due_timed_tasks() -> int:
    """调度任务：定时任务到点则生成一条控制指令。"""
    async with SessionLocal() as session:
        now = _now()
        tasks = (
            await session.execute(
                select(CtrlTimedTask).where(
                    CtrlTimedTask.enable_status == 1,
                    CtrlTimedTask.next_run_time.is_not(None),
                    CtrlTimedTask.next_run_time <= now,
                )
            )
        ).scalars().all()
        for task in tasks:
            session.add(
                _new_command(
                    task.device_id, task.point_key, task.target_value, task.operator_id, now,
                    exec_mode="timed", source="timed",
                )
            )
            task.last_run_time = now
            task.next_run_time = next_cron_time(task.cron_expr, now)
            session.add(task)
        await session.commit()
        return len(tasks)
