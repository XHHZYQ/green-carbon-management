"""实时监控域服务。"""

from datetime import datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BizException
from app.core.pagination import PageParams, paginate_query
from app.models.dev import DevArea, DevData, DevDevice, DevPoint
from app.models.mon import MonTopology, MonTopologyNode


def _now() -> datetime:
    return datetime.now().astimezone()


def _num(value) -> float | None:
    return float(value) if value is not None else None


async def _latest_by_point(session: AsyncSession, point_ids: list[int]) -> dict[int, DevData]:
    """取每个测点最新一条采集数据（PostgreSQL DISTINCT ON）。"""
    if not point_ids:
        return {}
    stmt = (
        select(DevData)
        .where(DevData.point_id.in_(point_ids))
        .distinct(DevData.point_id)
        .order_by(DevData.point_id, DevData.collect_time.desc())
    )
    rows = (await session.execute(stmt)).scalars().all()
    return {r.point_id: r for r in rows}


async def realtime(
    session: AsyncSession,
    device_id: int | None = None,
    area_id: int | None = None,
    keyword: str | None = None,
    limit: int = 60,
) -> list[dict]:
    """按设备返回各测点最新值（实时监控总览/平面图用）。"""
    stmt = select(DevDevice)
    if device_id:
        stmt = stmt.where(DevDevice.id == device_id)
    if area_id:
        stmt = stmt.where(DevDevice.area_id == area_id)
    if keyword:
        stmt = stmt.where(DevDevice.device_name.ilike(f"%{keyword}%"))
    devices = (await session.execute(stmt.order_by(DevDevice.id).limit(limit))).scalars().all()
    if not devices:
        return []

    dev_ids = [d.id for d in devices]
    points = (
        await session.execute(
            select(DevPoint).where(DevPoint.device_id.in_(dev_ids)).order_by(DevPoint.device_id, DevPoint.sort_no)
        )
    ).scalars().all()
    latest = await _latest_by_point(session, [p.id for p in points])
    area_names = {a.id: a.area_name for a in (await session.execute(select(DevArea))).scalars().all()}

    grouped: dict[int, list[dict]] = {}
    for p in points:
        row = latest.get(p.id)
        grouped.setdefault(p.device_id, []).append(
            {
                "point_id": p.id,
                "point_name": p.point_name,
                "unit": p.unit,
                "value": _num(row.collect_value) if row else None,
                "collect_time": row.collect_time if row else None,
                "data_quality": row.data_quality if row else None,
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


async def curve(session: AsyncSession, point_id: int, hours: int = 1) -> list[dict]:
    """某测点最近 N 小时的实时曲线。"""
    since = _now() - timedelta(hours=hours)
    stmt = (
        select(DevData)
        .where(DevData.point_id == point_id, DevData.collect_time >= since)
        .order_by(DevData.collect_time)
    )
    rows = (await session.execute(stmt)).scalars().all()
    return [
        {"collect_time": r.collect_time, "collect_value": _num(r.collect_value), "data_quality": r.data_quality}
        for r in rows
    ]


# ==================== 组态图 / 平面图 ====================


async def page_topologies(
    session: AsyncSession,
    params: PageParams,
    keyword: str | None = None,
    topo_type: str | None = None,
) -> dict:
    stmt = select(MonTopology)
    if keyword:
        stmt = stmt.where(MonTopology.topo_name.ilike(f"%{keyword}%"))
    if topo_type:
        stmt = stmt.where(MonTopology.topo_type == topo_type)
    total, rows = await paginate_query(session, stmt.order_by(MonTopology.id), params)
    return {"total": total, "items": [r.model_dump() for r in rows]}


async def get_topology(session: AsyncSession, topo_id: int) -> dict:
    topo = await session.get(MonTopology, topo_id)
    if not topo:
        raise BizException("组态图不存在")
    nodes = (
        await session.execute(
            select(MonTopologyNode).where(MonTopologyNode.topo_id == topo_id).order_by(MonTopologyNode.id)
        )
    ).scalars().all()

    point_ids = [n.point_id for n in nodes if n.point_id]
    device_ids = [n.device_id for n in nodes if n.device_id]
    latest = await _latest_by_point(session, point_ids)
    pts = {
        p.id: p
        for p in (await session.execute(select(DevPoint).where(DevPoint.id.in_(point_ids)))).scalars().all()
    } if point_ids else {}
    devs = {
        d.id: d
        for d in (await session.execute(select(DevDevice).where(DevDevice.id.in_(device_ids)))).scalars().all()
    } if device_ids else {}

    node_list = []
    for n in nodes:
        item = n.model_dump()
        row = latest.get(n.point_id) if n.point_id else None
        point = pts.get(n.point_id) if n.point_id else None
        device = devs.get(n.device_id) if n.device_id else None
        item.update(
            {
                "device_name": device.device_name if device else None,
                "point_name": point.point_name if point else None,
                "unit": point.unit if point else None,
                "value": _num(row.collect_value) if row else None,
                "collect_time": row.collect_time if row else None,
            }
        )
        node_list.append(item)

    data = topo.model_dump()
    data["nodes"] = node_list
    return data


async def _save_nodes(session: AsyncSession, topo_id: int, nodes: list) -> None:
    for node in nodes:
        session.add(MonTopologyNode(topo_id=topo_id, **node.model_dump(exclude={"id"})))
    await session.flush()


async def create_topology(session: AsyncSession, payload) -> dict:
    topo = MonTopology(**payload.model_dump(exclude={"nodes"}))
    session.add(topo)
    await session.flush()
    await _save_nodes(session, topo.id, payload.nodes)
    await session.commit()
    return await get_topology(session, topo.id)


async def update_topology(session: AsyncSession, topo_id: int, payload) -> dict:
    topo = await session.get(MonTopology, topo_id)
    if not topo:
        raise BizException("组态图不存在")
    for key, value in payload.model_dump(exclude_unset=True, exclude={"nodes"}).items():
        setattr(topo, key, value)
    session.add(topo)
    if payload.nodes is not None:
        await session.execute(delete(MonTopologyNode).where(MonTopologyNode.topo_id == topo_id))
        await _save_nodes(session, topo_id, payload.nodes)
    await session.commit()
    return await get_topology(session, topo_id)


async def delete_topology(session: AsyncSession, topo_id: int) -> None:
    topo = await session.get(MonTopology, topo_id)
    if not topo:
        raise BizException("组态图不存在")
    await session.execute(delete(MonTopologyNode).where(MonTopologyNode.topo_id == topo_id))
    await session.delete(topo)
    await session.commit()
