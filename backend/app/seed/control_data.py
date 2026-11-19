"""控制域示例数据（B4-1）。

覆盖：控制指令记录（ctrl_command）、定时控制任务（ctrl_timed_task）。

用法：
    uv run python -m app.seed.run_seed
"""

import random
from datetime import datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ctrl import CtrlCommand, CtrlTimedTask
from app.models.dev import DevControlPoint, DevDevice
from app.models.sys import SysUser
from app.services.control_service import next_cron_time

random.seed(20260202)

# 定时任务模板：(任务名, 控制点编码, 目标值, cron, 说明, 启用)
TIMED_TASKS = [
    ("照明上班开启", "switch", "1", "0 8 * * 1-5", "工作日 08:00 开启", 1),
    ("照明下班关闭", "switch", "0", "30 18 * * 1-5", "工作日 18:30 关闭", 1),
    ("空调提前启动", "setpoint", "8", "0 7 * * *", "每天 07:00 预冷", 1),
    ("空调夜间关闭", "switch", "0", "0 22 * * *", "每天 22:00 关闭", 1),
    ("插座夜间断电", "switch", "0", "0 23 * * *", "每天 23:00 断电", 1),
    ("水泵夜间停机", "frequency", "0", "0 2 * * *", "每天 02:00 停机", 0),
]

FAIL_REASONS = ["设备未响应", "指令被拒绝", "控制点当前不可用", "通信超时，未在规定时间内收到响应"]


def _target_value(cp: DevControlPoint) -> str:
    if cp.point_type == "enum":
        return random.choice(["0", "1"])
    lo = float(cp.value_min or 0)
    hi = float(cp.value_max or 100)
    return str(round(random.uniform(lo, hi), 1))


async def seed_control_domain(session: AsyncSession) -> dict[str, int]:
    """写入控制域示例数据（先重置后写入）。"""
    await session.execute(delete(CtrlCommand))
    await session.execute(delete(CtrlTimedTask))
    await session.commit()

    now = datetime.now().astimezone()
    users = {u.username: u for u in (await session.execute(select(SysUser))).scalars().all()}
    admin_id = users["admin"].id if "admin" in users else None
    ops_id = users["ops"].id if "ops" in users else None

    devices = {d.id: d for d in (await session.execute(select(DevDevice))).scalars().all()}
    cps = [
        cp
        for cp in (await session.execute(select(DevControlPoint))).scalars().all()
        if cp.device_id in devices
    ]

    # ---------------- 控制指令记录 ----------------
    cmd_count = 0
    sources = ["manual"] * 6 + ["batch"] * 2 + ["timed", "scene"]
    for _ in range(48):
        cp = random.choice(cps)
        device = devices[cp.device_id]
        send_time = now - timedelta(
            days=random.randint(0, 6),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59),
            seconds=random.randint(0, 59),
        )
        roll = random.random()
        if roll < 0.76:
            status, fail_reason = "success", None
        elif roll < 0.92:
            status, fail_reason = "fail", random.choice(FAIL_REASONS)
        else:
            status, fail_reason = "timeout", FAIL_REASONS[-1]
        finish = send_time + timedelta(seconds=random.randint(1, 3))
        operator = random.choice([admin_id, ops_id])
        session.add(
            CtrlCommand(
                command_no=f"CMD{send_time:%Y%m%d%H%M%S}{random.randint(100, 999)}",
                device_id=device.id,
                point_key=cp.point_key,
                target_value=_target_value(cp),
                priority=random.choice(["normal", "normal", "high"]),
                exec_mode="timed" if random.random() < 0.15 else "immediate",
                timeout_sec=10,
                need_confirm=cp.dangerous,
                source=random.choice(sources),
                status=status,
                fail_reason=fail_reason,
                operator_id=operator,
                send_time=send_time,
                finish_time=finish,
                created_at=send_time,
            )
        )
        cmd_count += 1
    await session.flush()

    # ---------------- 定时控制任务 ----------------
    task_count = 0
    used: set[int] = set()
    for name, point_key, target_value, cron, desc, enable in TIMED_TASKS:
        candidates = [cp for cp in cps if cp.point_key == point_key and cp.device_id not in used]
        if not candidates:
            candidates = [cp for cp in cps if cp.point_key == point_key]
        if not candidates:
            continue
        cp = random.choice(candidates)
        used.add(cp.device_id)
        session.add(
            CtrlTimedTask(
                task_name=name,
                device_id=cp.device_id,
                point_key=point_key,
                target_value=target_value,
                cron_expr=cron,
                repeat_desc=desc,
                enable_status=enable,
                last_run_time=now - timedelta(days=1),
                next_run_time=next_cron_time(cron, now) if enable else None,
                operator_id=admin_id,
                created_at=now - timedelta(days=random.randint(10, 60)),
            )
        )
        task_count += 1
    await session.commit()
    return {"ctrl_commands": cmd_count, "ctrl_timed_tasks": task_count}
