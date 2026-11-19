"""场景与联动域示例数据（B4-2）。

覆盖：场景（scene_info）、场景动作（scene_action）、场景定时（scene_schedule）、
联动规则（scene_link_rule）、执行记录（scene_exec_log）。

用法：
    uv run python -m app.seed.run_seed
"""

import random
from datetime import datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dev import DevControlPoint, DevDevice, DevPoint
from app.models.scene import SceneAction, SceneExecLog, SceneInfo, SceneLinkRule, SceneSchedule
from app.models.sys import SysUser
from app.services.control_service import next_cron_time

random.seed(20260203)

# 场景模板：(编码, 名称, 图标, 说明, 启用, 动作列表[(控制点编码, 目标值)])
SCENES = [
    ("SCENE_WORK", "上班模式", "Sunrise", "工作日早晨自动开启照明与空调，营造舒适办公环境", 1,
     [("switch", "1"), ("brightness_set", "80"), ("setpoint", "24")]),
    ("SCENE_OFFWORK", "下班模式", "Moon", "下班后统一关闭照明、空调与插座，避免能源浪费", 1,
     [("switch", "0"), ("switch", "0"), ("brightness_set", "0")]),
    ("SCENE_MEETING", "会议模式", "Present", "会议期间调节照明亮度与空调温度", 1,
     [("brightness_set", "60"), ("setpoint", "23")]),
    ("SCENE_NOON", "午休模式", "Coffee", "午休时段调暗照明并适度升温", 0,
     [("brightness_set", "20"), ("setpoint", "26")]),
    ("SCENE_SAVING", "节能模式", "TrendCharts", "非高峰时段上调空调温度、关闭非必要照明", 1,
     [("setpoint", "26"), ("brightness_set", "0"), ("frequency", "20")]),
    ("SCENE_SECURITY", "安防模式", "Lock", "夜间关闭照明与插座并切断非必要电源", 1,
     [("switch", "0"), ("switch", "0"), ("frequency", "0")]),
]

# 场景定时：(场景编码, cron, 说明)
SCHEDULES = [
    ("SCENE_WORK", "0 8 * * 1-5", "工作日 08:00"),
    ("SCENE_OFFWORK", "30 18 * * 1-5", "工作日 18:30"),
    ("SCENE_SAVING", "0 12 * * 1-5", "工作日 12:00"),
]

FAIL_REASONS = ["设备离线未响应", "控制点当前不可用", "通信超时，未在规定时间内收到响应"]


def _pick_cp(cps_by_key: dict[str, list[DevControlPoint]], point_key: str, used: set[int]) -> DevControlPoint | None:
    pool = [cp for cp in cps_by_key.get(point_key, []) if cp.device_id not in used]
    if not pool:
        pool = cps_by_key.get(point_key, [])
    if not pool:
        return None
    cp = random.choice(pool)
    used.add(cp.device_id)
    return cp


async def seed_scene_domain(session: AsyncSession) -> dict[str, int]:
    """写入场景与联动域示例数据（先重置后写入）。"""
    await session.execute(delete(SceneExecLog))
    await session.execute(delete(SceneLinkRule))
    await session.execute(delete(SceneSchedule))
    await session.execute(delete(SceneAction))
    await session.execute(delete(SceneInfo))
    await session.commit()

    now = datetime.now().astimezone()
    users = {u.username: u for u in (await session.execute(select(SysUser))).scalars().all()}
    admin_id = users["admin"].id if "admin" in users else None
    ops_id = users["ops"].id if "ops" in users else None

    devices = {d.id: d for d in (await session.execute(select(DevDevice))).scalars().all()}
    cps = [
        cp for cp in (await session.execute(select(DevControlPoint))).scalars().all()
        if cp.device_id in devices and cp.status == 1
    ]
    cps_by_key: dict[str, list[DevControlPoint]] = {}
    for cp in cps:
        cps_by_key.setdefault(cp.point_key or "", []).append(cp)

    points = [
        p for p in (await session.execute(select(DevPoint))).scalars().all() if p.device_id in devices
    ]

    # ---------------- 场景 + 动作 ----------------
    scenes: dict[str, SceneInfo] = {}
    action_count = 0
    for idx, (code, name, icon, desc, enable, action_defs) in enumerate(SCENES):
        scene = SceneInfo(
            scene_code=code,
            scene_name=name,
            icon=icon,
            description=desc,
            enable_status=enable,
            last_exec_time=now - timedelta(hours=random.randint(2, 20)),
            operator_id=admin_id,
            created_at=now - timedelta(days=random.randint(20, 90)),
        )
        session.add(scene)
        await session.flush()
        scenes[code] = scene

        used: set[int] = set()
        for sort_no, (point_key, target_value) in enumerate(action_defs):
            cp = _pick_cp(cps_by_key, point_key, used)
            if not cp:
                continue
            session.add(
                SceneAction(
                    scene_id=scene.id,
                    device_id=cp.device_id,
                    point_key=point_key,
                    target_value=target_value,
                    delay_sec=sort_no * 2,
                    sort_no=sort_no,
                )
            )
            action_count += 1
    await session.flush()

    # ---------------- 场景定时 ----------------
    schedule_count = 0
    for code, cron, desc in SCHEDULES:
        scene = scenes.get(code)
        if not scene:
            continue
        session.add(
            SceneSchedule(
                scene_id=scene.id,
                cron_expr=cron,
                repeat_desc=desc,
                enable_status=1,
                next_run_time=next_cron_time(cron, now),
            )
        )
        schedule_count += 1

    # ---------------- 联动规则 ----------------
    def _first_device_by_point(point_code: str) -> int | None:
        for p in points:
            if p.point_code == point_code:
                return p.device_id
        return None

    co2_dev = _first_device_by_point("CO2")
    temp_dev = _first_device_by_point("Temperature")
    power_pt_dev = _first_device_by_point("Power")
    switch_cps = cps_by_key.get("switch", [])
    ac_cp = switch_cps[0] if switch_cps else None
    socket_cp = switch_cps[1] if len(switch_cps) > 1 else ac_cp

    rule_defs = [
        ("CO₂ 超标自动开启新风", "CO₂ 浓度 > 1000 ppm",
         {"device_id": co2_dev, "point_code": "CO2", "operator": ">", "threshold": 1000},
         "control", None, ac_cp.device_id if ac_cp else None, "switch", "1", 1),
        ("高温自动开启空调制冷", "环境温度 > 28 ℃",
         {"device_id": temp_dev, "point_code": "Temperature", "operator": ">", "threshold": 28},
         "control", None, ac_cp.device_id if ac_cp else None, "switch", "1", 1),
        ("低温自动关闭空调", "环境温度 < 18 ℃",
         {"device_id": temp_dev, "point_code": "Temperature", "operator": "<", "threshold": 18},
         "control", None, socket_cp.device_id if socket_cp else None, "switch", "0", 1),
        ("功率超限触发节能场景", "回路功率 > 2 kW",
         {"device_id": power_pt_dev, "point_code": "Power", "operator": ">", "threshold": 2},
         "scene", scenes["SCENE_SAVING"].id, None, None, None, 1),
        ("夜间自动进入安防场景", "用电功率 > 1.5 kW",
         {"device_id": power_pt_dev, "point_code": "Power", "operator": ">", "threshold": 1.5},
         "scene", scenes["SCENE_SECURITY"].id, None, None, None, 0),
    ]

    rule_count = 0
    rules: list[SceneLinkRule] = []
    for name, cond_text, cond_json, action_type, target_scene, target_dev, tgt_key, tgt_val, enable in rule_defs:
        if cond_json.get("device_id") is None:
            continue
        rule = SceneLinkRule(
            rule_name=name,
            condition_text=cond_text,
            condition_json=cond_json,
            action_type=action_type,
            target_scene_id=target_scene,
            target_device_id=target_dev,
            target_point_key=tgt_key,
            target_value=tgt_val,
            enable_status=enable,
            operator_id=admin_id,
            created_at=now - timedelta(days=random.randint(5, 40)),
        )
        session.add(rule)
        rules.append(rule)
        rule_count += 1
    await session.flush()

    # ---------------- 执行记录 ----------------
    log_count = 0
    scene_list = list(scenes.values())
    for _ in range(30):
        exec_time = now - timedelta(
            days=random.randint(0, 6),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59),
            seconds=random.randint(0, 59),
        )
        is_link = random.random() < 0.35 and rules
        roll = random.random()
        if roll < 0.8:
            result = "success"
        elif roll < 0.94:
            result = "partial"
        else:
            result = "fail"
        total = random.randint(2, 5)
        if result == "success":
            success, fail = total, 0
        elif result == "partial":
            success = random.randint(1, total - 1)
            fail = total - success
        else:
            success, fail = 0, total
        if is_link:
            rule = random.choice(rules)
            session.add(
                SceneExecLog(
                    exec_type="link",
                    rule_id=rule.id,
                    scene_id=rule.target_scene_id,
                    trigger_source="联动触发",
                    total_count=total,
                    success_count=success,
                    fail_count=fail,
                    result=result,
                    exec_time=exec_time,
                )
            )
        else:
            scene = random.choice(scene_list)
            session.add(
                SceneExecLog(
                    exec_type="scene",
                    scene_id=scene.id,
                    trigger_source=random.choice(["手动执行", "手动执行", "定时执行"]),
                    total_count=total,
                    success_count=success,
                    fail_count=fail,
                    result=result,
                    exec_time=exec_time,
                )
            )
        log_count += 1
    await session.commit()
    return {
        "scene_info": len(scenes),
        "scene_action": action_count,
        "scene_schedule": schedule_count,
        "scene_link_rule": rule_count,
        "scene_exec_log": log_count,
    }
