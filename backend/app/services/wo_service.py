"""工单域服务（B6 工单管理：列表/详情/新建/编辑/指派/处理/完成/删除）。"""

from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BizException
from app.models.dev import DevDevice
from app.models.sys import SysUser
from app.models.wo import WoWorkOrder

# 允许写入的字段
EDITABLE = ("title", "type", "level", "device_id", "content", "assignee_id")


async def _maps(session: AsyncSession) -> tuple[dict[int, str], dict[int, str]]:
    device_names = {
        d.id: d.device_name for d in (await session.execute(select(DevDevice))).scalars().all()
    }
    user_names = {
        u.id: (u.real_name or u.username) for u in (await session.execute(select(SysUser))).scalars().all()
    }
    return device_names, user_names


def _to_dict(row: WoWorkOrder, device_names: dict, user_names: dict) -> dict:
    item = row.model_dump()
    item["device_name"] = device_names.get(row.device_id)
    item["assignee_name"] = user_names.get(row.assignee_id) if row.assignee_id else None
    return item


async def page_work_orders(
    session: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    status: str | None = None,
    source: str | None = None,
    level: str | None = None,
    type: str | None = None,
    assignee_id: int | None = None,
    keyword: str | None = None,
) -> tuple[int, list[dict]]:
    conds = []
    if status:
        conds.append(WoWorkOrder.status == status)
    if source:
        conds.append(WoWorkOrder.source == source)
    if level:
        conds.append(WoWorkOrder.level == level)
    if type:
        conds.append(WoWorkOrder.type == type)
    if assignee_id:
        conds.append(WoWorkOrder.assignee_id == assignee_id)
    if keyword:
        conds.append(
            or_(
                WoWorkOrder.order_no.ilike(f"%{keyword}%"),
                WoWorkOrder.title.ilike(f"%{keyword}%"),
                WoWorkOrder.content.ilike(f"%{keyword}%"),
            )
        )

    count_stmt = select(func.count(WoWorkOrder.id))
    stmt = select(WoWorkOrder)
    for c in conds:
        count_stmt = count_stmt.where(c)
        stmt = stmt.where(c)
    total = int((await session.execute(count_stmt)).scalar_one() or 0)
    rows = (
        await session.execute(
            stmt.order_by(WoWorkOrder.create_time.desc(), WoWorkOrder.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).scalars().all()

    device_names, user_names = await _maps(session)
    items = [_to_dict(r, device_names, user_names) for r in rows]
    return total, items


async def get_work_order(session: AsyncSession, work_order_id: int) -> dict:
    row = await session.get(WoWorkOrder, work_order_id)
    if not row:
        raise BizException("工单不存在")
    device_names, user_names = await _maps(session)
    return _to_dict(row, device_names, user_names)


async def create_work_order(session: AsyncSession, data: dict, creator_id: int) -> dict:
    now = datetime.now().astimezone()
    payload = {k: v for k, v in data.items() if k in EDITABLE and v is not None}
    wo = WoWorkOrder(
        order_no=f"WO{now:%Y%m%d%H%M%S}",
        title=str(payload.get("title") or "未命名工单")[:128],
        type=payload.get("type"),
        level=payload.get("level"),
        device_id=payload.get("device_id"),
        content=payload.get("content"),
        assignee_id=payload.get("assignee_id"),
        source="manual",
        status="pending",
        creator_id=creator_id,
        create_time=now,
        created_at=now,
    )
    session.add(wo)
    await session.commit()
    await session.refresh(wo)
    return await get_work_order(session, wo.id)


async def update_work_order(session: AsyncSession, work_order_id: int, data: dict) -> dict:
    wo = await session.get(WoWorkOrder, work_order_id)
    if not wo:
        raise BizException("工单不存在")
    for key, value in data.items():
        if key in EDITABLE and value is not None:
            setattr(wo, key, value)
    session.add(wo)
    await session.commit()
    await session.refresh(wo)
    return await get_work_order(session, work_order_id)


async def assign_work_order(session: AsyncSession, work_order_id: int, assignee_id: int) -> dict:
    wo = await session.get(WoWorkOrder, work_order_id)
    if not wo:
        raise BizException("工单不存在")
    if wo.status == "pending":
        wo.status = "processing"
    wo.assignee_id = assignee_id
    session.add(wo)
    await session.commit()
    await session.refresh(wo)
    return await get_work_order(session, work_order_id)


async def handle_work_order(session: AsyncSession, work_order_id: int, handle_result: str) -> dict:
    wo = await session.get(WoWorkOrder, work_order_id)
    if not wo:
        raise BizException("工单不存在")
    wo.handle_result = handle_result
    wo.status = "processing"
    session.add(wo)
    await session.commit()
    await session.refresh(wo)
    return await get_work_order(session, work_order_id)


async def finish_work_order(session: AsyncSession, work_order_id: int, handle_result: str | None = None) -> dict:
    wo = await session.get(WoWorkOrder, work_order_id)
    if not wo:
        raise BizException("工单不存在")
    if handle_result:
        wo.handle_result = handle_result
    wo.status = "finished"
    wo.finish_time = datetime.now().astimezone()
    session.add(wo)
    await session.commit()
    await session.refresh(wo)
    return await get_work_order(session, work_order_id)


async def delete_work_order(session: AsyncSession, work_order_id: int) -> None:
    wo = await session.get(WoWorkOrder, work_order_id)
    if not wo:
        raise BizException("工单不存在")
    await session.delete(wo)
    await session.commit()
