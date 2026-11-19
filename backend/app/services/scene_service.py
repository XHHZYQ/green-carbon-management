"""场景与联动域服务（B4-2）。

负责：场景 CRUD 与场景动作、一键执行（逐条下发控制指令并留痕）、场景定时配置、
联动规则 CRUD；以及调度器驱动的场景定时执行与联动规则命中自动执行。
"""

from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BizException
from app.core.pagination import PageParams, paginate_query
from app.db.session import SessionLocal
from app.models.dev import DevControlPoint, DevData, DevDevice, DevPoint
from app.models.scene import SceneAction, SceneExecLog, SceneInfo, SceneLinkRule, SceneSchedule
from app.services.control_service import _new_command, next_cron_time

# 执行类型 / 结果中文
EXEC_TYPE_TEXT = {"scene": "场景执行", "link": "联动触发"}
RESULT_TEXT = {"success": "成功", "partial": "部分成功", "fail": "失败"}

# 联动规则命中后的冷却时长（秒），避免同一规则反复触发
LINK_COOLDOWN_SEC = 120
_link_cooldown: dict[int, datetime] = {}


def _now() -> datetime:
    return datetime.now().astimezone()


# ==================== 场景 ====================


async def _scene_dicts(session: AsyncSession, scenes: list[SceneInfo]) -> list[dict]:
    ids = [s.id for s in scenes]
    action_counts: dict[int, int] = {}
    schedules: dict[int, SceneSchedule] = {}
    if ids:
        rows = await session.execute(
            select(SceneAction.scene_id, func.count())
            .where(SceneAction.scene_id.in_(ids))
            .group_by(SceneAction.scene_id)
        )
        action_counts = {sid: cnt for sid, cnt in rows.all()}
        for sch in (
            await session.execute(select(SceneSchedule).where(SceneSchedule.scene_id.in_(ids)))
        ).scalars().all():
            schedules[sch.scene_id] = sch

    result = []
    for s in scenes:
        item = s.model_dump()
        item["action_count"] = action_counts.get(s.id, 0)
        sch = schedules.get(s.id)
        item["cron_expr"] = sch.cron_expr if sch else None
        item["repeat_desc"] = sch.repeat_desc if sch else None
        item["schedule_enable"] = sch.enable_status if sch else 0
        item["next_run_time"] = sch.next_run_time if sch else None
        result.append(item)
    return result


async def page_scenes(
    session: AsyncSession,
    params: PageParams,
    keyword: str | None = None,
    enable_status: int | None = None,
) -> dict:
    stmt = select(SceneInfo)
    if keyword:
        stmt = stmt.where(SceneInfo.scene_name.ilike(f"%{keyword}%"))
    if enable_status is not None:
        stmt = stmt.where(SceneInfo.enable_status == enable_status)
    stmt = stmt.order_by(SceneInfo.id)
    total, rows = await paginate_query(session, stmt, params)
    return {"total": total, "items": await _scene_dicts(session, rows)}


async def get_scene(session: AsyncSession, scene_id: int) -> dict:
    scene = await session.get(SceneInfo, scene_id)
    if not scene:
        raise BizException("场景不存在")
    data = (await _scene_dicts(session, [scene]))[0]
    data["actions"] = await list_actions(session, scene_id)
    return data


async def save_scene(session: AsyncSession, scene_id: int | None, data: dict, operator_id: int | None) -> dict:
    if scene_id:
        scene = await session.get(SceneInfo, scene_id)
        if not scene:
            raise BizException("场景不存在")
    else:
        scene = SceneInfo(scene_code="", scene_name="", operator_id=operator_id)
    dup = (
        await session.execute(
            select(SceneInfo).where(SceneInfo.scene_code == data.get("scene_code"), SceneInfo.id != scene_id)
        )
    ).scalars().first()
    if data.get("scene_code") and dup:
        raise BizException("场景编码已存在")

    for key, value in data.items():
        setattr(scene, key, value)
    scene.updated_at = _now()
    session.add(scene)
    await session.commit()
    await session.refresh(scene)
    return (await _scene_dicts(session, [scene]))[0]


async def delete_scene(session: AsyncSession, scene_id: int) -> None:
    scene = await session.get(SceneInfo, scene_id)
    if not scene:
        raise BizException("场景不存在")
    await session.execute(update(SceneExecLog).where(SceneExecLog.scene_id == scene_id).values(scene_id=None))
    await session.execute(
        update(SceneLinkRule).where(SceneLinkRule.target_scene_id == scene_id).values(target_scene_id=None)
    )
    await session.execute(SceneAction.__table__.delete().where(SceneAction.scene_id == scene_id))
    await session.execute(SceneSchedule.__table__.delete().where(SceneSchedule.scene_id == scene_id))
    await session.delete(scene)
    await session.commit()


async def set_scene_enable(session: AsyncSession, scene_id: int, enable_status: int) -> dict:
    scene = await session.get(SceneInfo, scene_id)
    if not scene:
        raise BizException("场景不存在")
    scene.enable_status = enable_status
    scene.updated_at = _now()
    session.add(scene)
    await session.commit()
    return {"id": scene_id, "enable_status": enable_status}


# ==================== 场景动作 ====================


async def list_actions(session: AsyncSession, scene_id: int) -> list[dict]:
    actions = (
        await session.execute(
            select(SceneAction).where(SceneAction.scene_id == scene_id).order_by(SceneAction.sort_no, SceneAction.id)
        )
    ).scalars().all()
    device_ids = [a.device_id for a in actions if a.device_id]
    devs = {
        d.id: d
        for d in (await session.execute(select(DevDevice).where(DevDevice.id.in_(device_ids)))).scalars().all()
    } if device_ids else {}
    items = []
    for a in actions:
        item = a.model_dump()
        dev = devs.get(a.device_id)
        item["device_name"] = dev.device_name if dev else None
        items.append(item)
    return items


async def _check_action(session: AsyncSession, device_id: int, point_key: str) -> None:
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


async def save_action(session: AsyncSession, scene_id: int, action_id: int | None, data: dict) -> dict:
    if action_id:
        action = await session.get(SceneAction, action_id)
        if not action:
            raise BizException("场景动作不存在")
    else:
        if not await session.get(SceneInfo, scene_id):
            raise BizException("场景不存在")
        action = SceneAction(scene_id=scene_id)

    device_id = data.get("device_id", action.device_id)
    point_key = data.get("point_key", action.point_key)
    await _check_action(session, device_id, point_key)

    for key, value in data.items():
        setattr(action, key, value)
    action.target_value = str(action.target_value) if action.target_value is not None else None
    session.add(action)
    await session.commit()
    await session.refresh(action)
    return action.model_dump()


async def delete_action(session: AsyncSession, action_id: int) -> None:
    action = await session.get(SceneAction, action_id)
    if not action:
        raise BizException("场景动作不存在")
    await session.delete(action)
    await session.commit()


# ==================== 场景执行 ====================


async def _dispatch_scene(session: AsyncSession, scene: SceneInfo, operator_id: int | None, now: datetime) -> tuple[int, int, int]:
    """按动作逐条下发控制指令，任一失败不影响其余。返回 (总数, 成功, 失败)。"""
    actions = (
        await session.execute(
            select(SceneAction).where(SceneAction.scene_id == scene.id).order_by(SceneAction.sort_no, SceneAction.id)
        )
    ).scalars().all()
    total = success = fail = 0
    for a in actions:
        total += 1
        if not a.device_id or not a.point_key:
            fail += 1
            continue
        cp = (
            await session.execute(
                select(DevControlPoint).where(
                    DevControlPoint.device_id == a.device_id, DevControlPoint.point_key == a.point_key
                )
            )
        ).scalars().first()
        if not cp:
            fail += 1
            continue
        session.add(_new_command(a.device_id, a.point_key, a.target_value or "", operator_id, now, source="scene"))
        success += 1
    return total, success, fail


async def exec_scene(
    session: AsyncSession, scene_id: int, operator_id: int | None, trigger_source: str = "手动执行"
) -> dict:
    scene = await session.get(SceneInfo, scene_id)
    if not scene:
        raise BizException("场景不存在")
    now = _now()
    total, success, fail = await _dispatch_scene(session, scene, operator_id, now)
    scene.last_exec_time = now
    scene.updated_at = now
    session.add(scene)
    log = SceneExecLog(
        exec_type="scene",
        scene_id=scene_id,
        trigger_source=trigger_source,
        total_count=total,
        success_count=success,
        fail_count=fail,
        result="success" if fail == 0 else "partial",
        exec_time=now,
    )
    session.add(log)
    await session.commit()
    await session.refresh(log)
    return {"total_count": total, "success_count": success, "fail_count": fail, "result": log.result}


# 供接口调用的别名（一键执行）
async def execute_scene(session: AsyncSession, scene_id: int, operator_id: int | None) -> dict:
    return await exec_scene(session, scene_id, operator_id, "手动执行")


# ==================== 场景定时 ====================


async def save_schedule(session: AsyncSession, scene_id: int, data: dict) -> dict:
    if not await session.get(SceneInfo, scene_id):
        raise BizException("场景不存在")
    sch = (
        await session.execute(select(SceneSchedule).where(SceneSchedule.scene_id == scene_id))
    ).scalars().first()
    if not sch:
        sch = SceneSchedule(scene_id=scene_id)
    for key, value in data.items():
        setattr(sch, key, value)
    sch.next_run_time = next_cron_time(sch.cron_expr, _now()) if sch.enable_status == 1 else None
    session.add(sch)
    await session.commit()
    await session.refresh(sch)
    return sch.model_dump()


# ==================== 联动规则 ====================


async def page_link_rules(
    session: AsyncSession,
    params: PageParams,
    keyword: str | None = None,
    enable_status: int | None = None,
) -> dict:
    stmt = select(SceneLinkRule)
    if keyword:
        stmt = stmt.where(SceneLinkRule.rule_name.ilike(f"%{keyword}%"))
    if enable_status is not None:
        stmt = stmt.where(SceneLinkRule.enable_status == enable_status)
    stmt = stmt.order_by(SceneLinkRule.id.desc())
    total, rows = await paginate_query(session, stmt, params)

    scene_ids = [r.target_scene_id for r in rows if r.target_scene_id]
    device_ids = [r.target_device_id for r in rows if r.target_device_id]
    scenes = {
        s.id: s.scene_name
        for s in (await session.execute(select(SceneInfo).where(SceneInfo.id.in_(scene_ids)))).scalars().all()
    } if scene_ids else {}
    devs = {
        d.id: d.device_name
        for d in (await session.execute(select(DevDevice).where(DevDevice.id.in_(device_ids)))).scalars().all()
    } if device_ids else {}

    items = []
    for r in rows:
        item = r.model_dump()
        item["target_scene_name"] = scenes.get(r.target_scene_id)
        item["target_device_name"] = devs.get(r.target_device_id)
        items.append(item)
    return {"total": total, "items": items}


async def save_link_rule(session: AsyncSession, rule_id: int | None, data: dict, operator_id: int | None) -> dict:
    if rule_id:
        rule = await session.get(SceneLinkRule, rule_id)
        if not rule:
            raise BizException("联动规则不存在")
    else:
        rule = SceneLinkRule(rule_name="", operator_id=operator_id)
    for key, value in data.items():
        setattr(rule, key, value)
    session.add(rule)
    await session.commit()
    await session.refresh(rule)
    return rule.model_dump()


async def delete_link_rule(session: AsyncSession, rule_id: int) -> None:
    rule = await session.get(SceneLinkRule, rule_id)
    if not rule:
        raise BizException("联动规则不存在")
    await session.delete(rule)
    await session.commit()


async def set_rule_enable(session: AsyncSession, rule_id: int, enable_status: int) -> dict:
    rule = await session.get(SceneLinkRule, rule_id)
    if not rule:
        raise BizException("联动规则不存在")
    rule.enable_status = enable_status
    session.add(rule)
    await session.commit()
    return {"id": rule_id, "enable_status": enable_status}


# ==================== 执行记录 ====================


async def page_exec_logs(
    session: AsyncSession,
    params: PageParams,
    exec_type: str | None = None,
    scene_id: int | None = None,
    result: str | None = None,
) -> dict:
    stmt = select(SceneExecLog)
    if exec_type:
        stmt = stmt.where(SceneExecLog.exec_type == exec_type)
    if scene_id:
        stmt = stmt.where(SceneExecLog.scene_id == scene_id)
    if result:
        stmt = stmt.where(SceneExecLog.result == result)
    stmt = stmt.order_by(SceneExecLog.id.desc())
    total, rows = await paginate_query(session, stmt, params)

    scene_ids = [r.scene_id for r in rows if r.scene_id]
    rule_ids = [r.rule_id for r in rows if r.rule_id]
    scenes = {
        s.id: s.scene_name
        for s in (await session.execute(select(SceneInfo).where(SceneInfo.id.in_(scene_ids)))).scalars().all()
    } if scene_ids else {}
    rules = {
        r.id: r.rule_name
        for r in (await session.execute(select(SceneLinkRule).where(SceneLinkRule.id.in_(rule_ids)))).scalars().all()
    } if rule_ids else {}

    items = []
    for r in rows:
        item = r.model_dump()
        item["exec_type_text"] = EXEC_TYPE_TEXT.get(r.exec_type or "", r.exec_type)
        item["result_text"] = RESULT_TEXT.get(r.result or "", r.result)
        item["scene_name"] = scenes.get(r.scene_id)
        item["rule_name"] = rules.get(r.rule_id)
        items.append(item)
    return {"total": total, "items": items}


# ==================== 调度器驱动 ====================


async def run_due_scene_schedules() -> int:
    """调度任务：场景定时任务到点则执行场景。"""
    async with SessionLocal() as session:
        now = _now()
        schedules = (
            await session.execute(
                select(SceneSchedule).where(
                    SceneSchedule.enable_status == 1,
                    SceneSchedule.next_run_time.is_not(None),
                    SceneSchedule.next_run_time <= now,
                )
            )
        ).scalars().all()
        count = 0
        for sch in schedules:
            scene = await session.get(SceneInfo, sch.scene_id) if sch.scene_id else None
            if scene and scene.enable_status == 1:
                total, success, fail = await _dispatch_scene(session, scene, scene.operator_id, now)
                scene.last_exec_time = now
                session.add(scene)
                session.add(
                    SceneExecLog(
                        exec_type="scene",
                        scene_id=scene.id,
                        trigger_source="定时执行",
                        total_count=total,
                        success_count=success,
                        fail_count=fail,
                        result="success" if fail == 0 else "partial",
                        exec_time=now,
                    )
                )
                count += 1
            sch.next_run_time = next_cron_time(sch.cron_expr, now)
            session.add(sch)
        await session.commit()
        return count


def _compare(value: float, operator: str, threshold) -> bool:
    if threshold is None:
        return False
    try:
        target = float(threshold)
    except (TypeError, ValueError):
        return False
    return {
        ">": value > target,
        ">=": value >= target,
        "<": value < target,
        "<=": value <= target,
        "==": value == target,
        "!=": value != target,
    }.get(operator, False)


async def _run_link_action(session: AsyncSession, rule: SceneLinkRule, now: datetime) -> None:
    """执行联动动作并写入执行记录。"""
    if rule.action_type == "scene" and rule.target_scene_id:
        scene = await session.get(SceneInfo, rule.target_scene_id)
        if not scene:
            return
        total, success, fail = await _dispatch_scene(session, scene, rule.operator_id, now)
        scene.last_exec_time = now
        session.add(scene)
        session.add(
            SceneExecLog(
                exec_type="link",
                rule_id=rule.id,
                scene_id=scene.id,
                trigger_source="联动触发",
                total_count=total,
                success_count=success,
                fail_count=fail,
                result="success" if fail == 0 else "partial",
                exec_time=now,
            )
        )
    elif rule.action_type == "control" and rule.target_device_id and rule.target_point_key:
        session.add(
            _new_command(
                rule.target_device_id,
                rule.target_point_key,
                rule.target_value or "",
                rule.operator_id,
                now,
                source="link",
            )
        )
        session.add(
            SceneExecLog(
                exec_type="link",
                rule_id=rule.id,
                trigger_source="联动触发",
                total_count=1,
                success_count=1,
                fail_count=0,
                result="success",
                exec_time=now,
            )
        )


async def evaluate_link_rules() -> int:
    """调度任务：评估联动规则，命中则自动执行。"""
    async with SessionLocal() as session:
        now = _now()
        rules = (
            await session.execute(select(SceneLinkRule).where(SceneLinkRule.enable_status == 1))
        ).scalars().all()
        count = 0
        for rule in rules:
            cond = rule.condition_json or {}
            device_id = cond.get("device_id")
            point_code = cond.get("point_code")
            if not device_id or not point_code:
                continue
            point = (
                await session.execute(
                    select(DevPoint).where(DevPoint.device_id == device_id, DevPoint.point_code == point_code)
                )
            ).scalars().first()
            if not point:
                continue
            latest = (
                await session.execute(
                    select(DevData)
                    .where(DevData.device_id == device_id, DevData.point_id == point.id)
                    .order_by(DevData.collect_time.desc().nullslast(), DevData.id.desc())
                )
            ).scalars().first()
            if not latest or latest.collect_value is None:
                continue
            if not _compare(float(latest.collect_value), cond.get("operator", ""), cond.get("threshold")):
                continue
            last = _link_cooldown.get(rule.id)
            if last and (now - last).total_seconds() < LINK_COOLDOWN_SEC:
                continue
            _link_cooldown[rule.id] = now
            await _run_link_action(session, rule, now)
            count += 1
        await session.commit()
        return count
