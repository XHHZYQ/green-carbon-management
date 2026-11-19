"""告警与工单域示例数据（B6）。

覆盖：告警规则（alarm_rule）、告警记录（alarm_info）、工单（wo_work_order）。
依赖设备域（dev_device / dev_point / cfg_device_type）与系统用户（sys_user / sys_role）。

用法：
    uv run python -m app.seed.run_seed
"""

import random
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alarm import AlarmInfo, AlarmRule
from app.models.cfg import CfgDeviceType
from app.models.dev import DevDevice, DevPoint
from app.models.notify import NotifyRule
from app.models.sys import SysRole, SysUser, SysUserRole
from app.models.wo import WoWorkOrder

random.seed(20260303)

# 告警规则定义：(规则名, 规则类型, 比较符, 阈值, 持续时长秒, 告警等级)
RULE_DEFS = [
    ("配电柜电流越限告警", "越限", "gt", 480, 30, "critical"),
    ("空调机组回风温度过高", "越限", "gt", 28, 60, "major"),
    ("冷冻水供水温度过低", "越限", "lt", 5, 60, "major"),
    ("生产车间用电负荷突增", "越限", "gt", 800, 10, "minor"),
    ("机房环境湿度超上限", "越限", "gt", 75, 120, "minor"),
    ("采集设备离线告警", "离线", "eq", 0, 300, "critical"),
    ("储能电池 SOC 过低", "越限", "lt", 20, 60, "major"),
    ("光伏逆变器效率异常", "故障", "lt", 92, 120, "minor"),
    ("水泵运行温度越界", "越限", "range", 90, 60, "major"),
    ("采集网关通信中断", "通信", "eq", 0, 180, "info"),
]

# 工单处理结果文案
HANDLE_RESULTS = [
    "已现场排查并复位设备，告警消除。",
    "更换故障部件后运行正常，已恢复监测。",
    "调整运行参数并复核，指标回到正常区间。",
    "完成清洁保养，设备运行平稳。",
]


def _alarm_value(operator: str | None, threshold: float) -> float:
    if operator == "gt":
        return round(threshold + random.uniform(0.05, 0.3) * max(abs(threshold), 1), 2)
    if operator == "lt":
        return round(max(threshold - random.uniform(0.05, 0.3) * max(abs(threshold), 1), 0), 2)
    return round(threshold, 2)


async def seed_alarm_domain(session: AsyncSession) -> dict[str, int]:
    """写入告警与工单域示例数据（先重置后写入）。"""
    await session.execute(delete(WoWorkOrder))
    await session.execute(delete(AlarmInfo))
    await session.execute(delete(AlarmRule))
    await session.commit()

    now = datetime.now().astimezone()

    devices = (await session.execute(select(DevDevice))).scalars().all()
    points = (await session.execute(select(DevPoint))).scalars().all()
    device_names = {d.id: d.device_name for d in devices}
    point_map = {p.id: p for p in points}
    points_by_device: dict[int, list[DevPoint]] = {}
    for p in points:
        if p.device_id:
            points_by_device.setdefault(p.device_id, []).append(p)

    notify_ids = [r.id for r in (await session.execute(select(NotifyRule))).scalars().all()]

    # ops 角色用户（工单处理人）
    ops_role = (await session.execute(select(SysRole).where(SysRole.role_code == "ops"))).scalars().first()
    ops_ids: list[int] = []
    if ops_role:
        ops_ids = [
            ur.user_id
            for ur in (
                await session.execute(select(SysUserRole).where(SysUserRole.role_id == ops_role.id))
            ).scalars().all()
            if ur.user_id
        ]
    if not ops_ids:
        ops_ids = [u.id for u in (await session.execute(select(SysUser))).scalars().all()]
    admin = (await session.execute(select(SysUser).where(SysUser.username == "admin"))).scalars().first()
    creator_id = admin.id if admin else (ops_ids[0] if ops_ids else None)

    # ---------------- 告警规则 ----------------
    rules: list[AlarmRule] = []
    pool = list(devices)
    random.shuffle(pool)
    for idx, (name, rtype, operator, threshold, duration, level) in enumerate(RULE_DEFS):
        dev = pool[idx % len(pool)] if pool else None
        dev_points = points_by_device.get(dev.id, []) if dev else []
        pt = random.choice(dev_points) if dev_points else None
        rule = AlarmRule(
            rule_name=name,
            rule_type=rtype,
            device_id=dev.id if dev else None,
            device_type_id=dev.device_type_id if dev else None,
            point_id=pt.id if pt else None,
            operator=operator,
            threshold=Decimal(str(threshold)),
            duration_sec=duration,
            alarm_level=level,
            notify_rule_id=random.choice(notify_ids) if notify_ids else None,
            enable_status=1 if idx < 8 else 0,
            created_at=now - timedelta(days=random.randint(30, 90)),
        )
        session.add(rule)
        rules.append(rule)
    await session.flush()

    # ---------------- 告警记录 ----------------
    status_pool = ["pending"] * 14 + ["confirmed"] * 10 + ["handled"] * 12 + ["ignored"] * 4
    alarm_count = 0
    for i in range(40):
        rule = random.choice(rules)
        dev_id = rule.device_id
        pt_id = rule.point_id
        pt = point_map.get(pt_id) if pt_id else None
        unit = (pt.unit if pt and pt.unit else "") or ""
        threshold = float(rule.threshold or 0)
        value = _alarm_value(rule.operator, threshold)
        alarm_time = now - timedelta(
            days=random.randint(0, 59),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59),
            seconds=random.randint(0, 59),
        )
        status = random.choice(status_pool)
        rtype = rule.rule_type or "越限"

        confirm_by = confirm_time = None
        if status in ("confirmed", "handled") and ops_ids:
            confirm_by = random.choice(ops_ids)
            confirm_time = alarm_time + timedelta(minutes=random.randint(5, 240))

        session.add(
            AlarmInfo(
                alarm_no=f"AL{alarm_time:%Y%m%d%H%M%S}{i:03d}",
                rule_id=rule.id,
                device_id=dev_id,
                point_id=pt_id,
                alarm_type=rtype,
                alarm_level=rule.alarm_level,
                alarm_value=Decimal(str(value)),
                threshold=rule.threshold,
                content=f"{device_names.get(dev_id, '设备')} {(pt.point_name if pt else '监测点')}"
                        f"{rtype}，当前值 {value}{unit}，阈值 {threshold}{unit}"[:255],
                status=status,
                confirm_by=confirm_by,
                confirm_time=confirm_time,
                alarm_time=alarm_time,
                created_at=alarm_time,
            )
        )
        alarm_count += 1
    await session.flush()

    # ---------------- 工单 ----------------
    alarms = (await session.execute(select(AlarmInfo))).scalars().all()
    wo_status_pool = ["pending"] * 6 + ["processing"] * 6 + ["finished"] * 9 + ["closed"] * 4
    wo_types = ["维修", "巡检", "保养"]
    wo_count = 0
    for i in range(25):
        create_time = now - timedelta(
            days=random.randint(0, 59),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59),
            seconds=random.randint(0, 59),
        )
        status = random.choice(wo_status_pool)
        wtype = random.choice(wo_types)
        level = random.choice(["critical", "major", "minor", "info"])
        assignee = random.choice(ops_ids) if ops_ids else None

        if i < 15 and alarms:
            alarm = random.choice(alarms)
            source = "alarm"
            alarm_id = alarm.id
            device_id = alarm.device_id
            level = alarm.alarm_level or level
            title = (alarm.content or f"{device_names.get(device_id, '设备')} 告警处理")
            content = alarm.content
        else:
            source = "manual"
            alarm_id = None
            dev = random.choice(devices) if devices else None
            device_id = dev.id if dev else None
            title = f"{wtype}任务：{device_names.get(device_id, '园区设备')}"
            content = f"例行{wtype}作业，对设备运行状况进行现场检查与处理。"

        handle_result = None
        finish_time = None
        if status in ("finished", "closed"):
            handle_result = random.choice(HANDLE_RESULTS)
            finish_time = create_time + timedelta(hours=random.randint(2, 48))

        session.add(
            WoWorkOrder(
                order_no=f"WO{create_time:%Y%m%d%H%M%S}{i:02d}",
                title=str(title)[:128],
                type=wtype,
                source=source,
                alarm_id=alarm_id,
                device_id=device_id,
                level=level,
                status=status,
                assignee_id=assignee,
                creator_id=creator_id,
                content=content,
                handle_result=handle_result,
                create_time=create_time,
                finish_time=finish_time,
                created_at=create_time,
            )
        )
        wo_count += 1
    await session.commit()

    return {"告警规则": len(rules), "告警记录": alarm_count, "工单": wo_count}
