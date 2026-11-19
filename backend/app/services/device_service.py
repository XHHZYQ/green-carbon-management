"""设备域业务逻辑：区域、设备台账、接入、测点与数据。"""

import csv
import io
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BizException
from app.core.pagination import PageParams, paginate_query
from app.models.cfg import CfgDeviceType, CfgProtocol, CfgProtocolParam
from app.models.dev import (
    DevAccessLog,
    DevArea,
    DevCollectTask,
    DevData,
    DevDataPatch,
    DevDevice,
    DevDeviceConn,
    DevPoint,
    DevPointTemplate,
    DevPointTemplateItem,
)
from app.schemas.device import (
    DataPatchRequest,
    DeviceCreate,
    DeviceUpdate,
    TestConnectionRequest,
)

# ==================== 区域 ====================


async def build_area_tree(session: AsyncSession) -> list[dict]:
    rows = list((await session.execute(select(DevArea).order_by(DevArea.sort_no, DevArea.id))).scalars().all())
    nodes = {a.id: {**a.model_dump(), "children": []} for a in rows}
    tree: list[dict] = []
    for a in rows:
        node = nodes[a.id]
        parent = nodes.get(a.parent_id) if a.parent_id else None
        if parent:
            parent["children"].append(node)
        else:
            tree.append(node)
    return tree


async def _name_map(session: AsyncSession, model, ids: set[int]) -> dict[int, str]:
    ids = {i for i in ids if i}
    if not ids:
        return {}
    label = "type_name" if model is CfgDeviceType else "protocol_name"
    rows = (await session.execute(select(model.id, getattr(model, label)).where(model.id.in_(ids)))).all()
    return {r[0]: r[1] for r in rows}


def _area_flat_map(areas: list[DevArea]) -> dict[int, str]:
    return {a.id: a.area_name for a in areas}


async def page_devices(
    session: AsyncSession,
    params: PageParams,
    keyword: str | None = None,
    area_id: int | None = None,
    device_type_id: int | None = None,
    online_status: str | None = None,
    status: str | None = None,
) -> dict:
    stmt = select(DevDevice)
    if keyword:
        stmt = stmt.where(or_(DevDevice.device_code.ilike(f"%{keyword}%"), DevDevice.device_name.ilike(f"%{keyword}%")))
    if area_id:
        stmt = stmt.where(DevDevice.area_id == area_id)
    if device_type_id:
        stmt = stmt.where(DevDevice.device_type_id == device_type_id)
    if online_status:
        stmt = stmt.where(DevDevice.online_status == online_status)
    if status:
        stmt = stmt.where(DevDevice.status == status)
    total, rows = await paginate_query(session, stmt.order_by(DevDevice.id.desc()), params)

    type_map = await _name_map(session, CfgDeviceType, {d.device_type_id for d in rows})
    proto_map = await _name_map(session, CfgProtocol, {d.protocol_id for d in rows})
    areas = list((await session.execute(select(DevArea))).scalars().all())
    area_map = _area_flat_map(areas)

    items = []
    for d in rows:
        data = d.model_dump()
        data["type_name"] = type_map.get(d.device_type_id, "-")
        data["protocol_name"] = proto_map.get(d.protocol_id, "-")
        data["area_name"] = area_map.get(d.area_id, "-")
        items.append(data)
    return {"total": total, "items": items}


async def get_device_detail(session: AsyncSession, device_id: int) -> dict:
    device = await session.get(DevDevice, device_id)
    if not device:
        raise BizException("设备不存在")
    conns = list(
        (await session.execute(select(DevDeviceConn).where(DevDeviceConn.device_id == device_id))).scalars().all()
    )
    points = list(
        (await session.execute(select(DevPoint).where(DevPoint.device_id == device_id).order_by(DevPoint.sort_no))).scalars().all()
    )
    tasks = list(
        (await session.execute(select(DevCollectTask).where(DevCollectTask.device_id == device_id))).scalars().all()
    )
    data = device.model_dump()
    type_map = await _name_map(session, CfgDeviceType, {device.device_type_id})
    proto_map = await _name_map(session, CfgProtocol, {device.protocol_id})
    area = await session.get(DevArea, device.area_id) if device.area_id else None
    data["type_name"] = type_map.get(device.device_type_id, "-")
    data["protocol_name"] = proto_map.get(device.protocol_id, "-")
    data["area_name"] = area.area_name if area else "-"
    data["params"] = [c.model_dump() for c in conns]
    data["points"] = [p.model_dump() for p in points]
    data["tasks"] = [t.model_dump() for t in tasks]
    return data


async def create_device(session: AsyncSession, payload: DeviceCreate, operator_id: int | None) -> DevDevice:
    exists = (await session.execute(select(DevDevice).where(DevDevice.device_code == payload.device_code))).scalars().first()
    if exists:
        raise BizException(f"设备编号 {payload.device_code} 已存在")

    device = DevDevice(
        device_code=payload.device_code,
        device_name=payload.device_name,
        device_type_id=payload.device_type_id,
        area_id=payload.area_id,
        protocol_id=payload.protocol_id,
        install_location=payload.install_location,
        remark=payload.remark,
        status="normal",
        online_status="online" if payload.enable_online else "offline",
        access_time=datetime.now().astimezone(),
        last_online_time=datetime.now().astimezone() if payload.enable_online else None,
    )
    session.add(device)
    await session.flush()

    for key, value in payload.params.items():
        session.add(DevDeviceConn(device_id=device.id, param_key=key, param_value=str(value)))

    # 按测点模板生成测点
    if payload.point_template_id:
        items = list(
            (
                await session.execute(
                    select(DevPointTemplateItem)
                    .where(DevPointTemplateItem.template_id == payload.point_template_id)
                    .order_by(DevPointTemplateItem.sort_no)
                )
            ).scalars().all()
        )
        for it in items:
            session.add(
                DevPoint(
                    device_id=device.id,
                    point_code=it.point_code,
                    point_name=it.point_name,
                    data_type=it.data_type,
                    unit=it.unit,
                    range_min=it.range_min,
                    range_max=it.range_max,
                    sort_no=it.sort_no,
                )
            )

    session.add(
        DevAccessLog(
            device_id=device.id,
            action="接入",
            result="成功",
            message="设备接入并上线成功" if payload.enable_online else "设备接入成功（未上线）",
            operator_id=operator_id,
            cost_ms=0,
        )
    )
    await session.commit()
    await session.refresh(device)
    return device


async def update_device(session: AsyncSession, device_id: int, payload: DeviceUpdate, operator_id: int | None) -> DevDevice:
    device = await session.get(DevDevice, device_id)
    if not device:
        raise BizException("设备不存在")
    for field in ("device_name", "device_type_id", "area_id", "protocol_id", "install_location", "remark"):
        value = getattr(payload, field)
        if value is not None:
            setattr(device, field, value)
    device.updated_at = datetime.now().astimezone()
    if payload.params is not None:
        existing = list(
            (await session.execute(select(DevDeviceConn).where(DevDeviceConn.device_id == device_id))).scalars().all()
        )
        for c in existing:
            await session.delete(c)
        for key, value in payload.params.items():
            session.add(DevDeviceConn(device_id=device_id, param_key=key, param_value=str(value)))
    session.add(device)
    await session.commit()
    await session.refresh(device)
    return device


async def delete_device(session: AsyncSession, device_id: int) -> None:
    device = await session.get(DevDevice, device_id)
    if not device:
        raise BizException("设备不存在")
    # 先删数据补录（引用历史数据）
    data_ids = list(
        (await session.execute(select(DevData.id).where(DevData.device_id == device_id))).scalars().all()
    )
    if data_ids:
        patches = list(
            (await session.execute(select(DevDataPatch).where(DevDataPatch.data_id.in_(data_ids)))).scalars().all()
        )
        for p in patches:
            await session.delete(p)
    # 再删设备关联的从表（含接入日志）
    for model in (DevDeviceConn, DevPoint, DevCollectTask, DevData, DevAccessLog):
        rows = list((await session.execute(select(model).where(model.device_id == device_id))).scalars().all())
        for r in rows:
            await session.delete(r)
    await session.delete(device)
    await session.commit()


async def set_online_status(session: AsyncSession, device_id: int, online: bool, operator_id: int | None) -> DevDevice:
    device = await session.get(DevDevice, device_id)
    if not device:
        raise BizException("设备不存在")
    device.online_status = "online" if online else "offline"
    if online:
        device.last_online_time = datetime.now().astimezone()
    device.updated_at = datetime.now().astimezone()
    session.add(device)
    session.add(
        DevAccessLog(
            device_id=device_id,
            action="上线" if online else "下线",
            result="成功",
            message="设备已上线" if online else "设备已下线",
            operator_id=operator_id,
        )
    )
    await session.commit()
    await session.refresh(device)
    return device


# ==================== 接入向导 ====================


async def wizard_types(session: AsyncSession) -> list[dict]:
    rows = (await session.execute(select(CfgDeviceType).where(CfgDeviceType.status == 1).order_by(CfgDeviceType.sort_no))).scalars().all()
    return [r.model_dump() for r in rows]


async def wizard_protocols(session: AsyncSession, device_type_id: int | None) -> list[dict]:
    stmt = select(CfgProtocol).where(CfgProtocol.status == 1)
    rows = (await session.execute(stmt.order_by(CfgProtocol.id))).scalars().all()
    default_id = None
    if device_type_id:
        dt = await session.get(CfgDeviceType, device_type_id)
        default_id = dt.default_protocol_id if dt else None
    result = []
    for r in rows:
        item = r.model_dump()
        item["is_default"] = r.id == default_id
        result.append(item)
    return result


async def wizard_params(session: AsyncSession, protocol_id: int | None) -> list[dict]:
    if not protocol_id:
        return []
    rows = (
        await session.execute(
            select(CfgProtocolParam).where(CfgProtocolParam.protocol_id == protocol_id).order_by(CfgProtocolParam.sort_no)
        )
    ).scalars().all()
    return [r.model_dump() for r in rows]


def test_connection(payload: TestConnectionRequest) -> dict:
    """V1.0 模拟测试连接：必要参数完整即返回成功。"""
    if not payload.protocol_id:
        raise BizException("请先选择通信协议")
    ip = payload.params.get("ip") or payload.params.get("host") or payload.params.get("broker")
    if "ip" in payload.params and payload.params.get("ip"):
        ip = str(ip)
        if ip.count(".") != 3:
            raise BizException("IP 地址格式不正确")
    cost = 120
    return {"success": True, "message": "连接成功", "cost_ms": cost}


# ==================== 批量导入 ====================

IMPORT_COLUMNS = [
    "设备编号",
    "设备名称",
    "设备类型编码",
    "所属区域",
    "安装位置",
    "通信协议编码",
]


def build_import_template() -> bytes:
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "设备导入模板"
    ws.append(IMPORT_COLUMNS)
    ws.append(["DT-DEMO-001", "示例设备", "DT_METER_E", "园区/办公楼", "一层配电间", "modbus_tcp"])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


async def import_devices(session: AsyncSession, filename: str, content: bytes, operator_id: int | None) -> dict:
    rows = _parse_import_file(filename, content)
    if not rows:
        raise BizException("导入文件为空或无有效数据")

    type_map = {t.type_code: t for t in (await session.execute(select(CfgDeviceType))).scalars().all()}
    proto_map = {p.protocol_code: p for p in (await session.execute(select(CfgProtocol))).scalars().all()}
    area_map = {a.area_name: a for a in (await session.execute(select(DevArea))).scalars().all()}

    success, failed = 0, 0
    messages: list[str] = []
    for idx, row in enumerate(rows, start=2):
        code = (row.get("设备编号") or "").strip()
        name = (row.get("设备名称") or "").strip()
        if not code or not name:
            failed += 1
            messages.append(f"第 {idx} 行：设备编号/名称不能为空")
            continue
        exists = (await session.execute(select(DevDevice).where(DevDevice.device_code == code))).scalars().first()
        if exists:
            failed += 1
            messages.append(f"第 {idx} 行：设备编号 {code} 已存在")
            continue
        dtype = type_map.get((row.get("设备类型编码") or "").strip())
        proto = proto_map.get((row.get("通信协议编码") or "").strip())
        area = area_map.get((row.get("所属区域") or "").strip())
        device = DevDevice(
            device_code=code,
            device_name=name,
            device_type_id=dtype.id if dtype else None,
            protocol_id=proto.id if proto else None,
            area_id=area.id if area else None,
            install_location=(row.get("安装位置") or "").strip() or None,
            status="normal",
            online_status="offline",
            access_time=datetime.now().astimezone(),
        )
        session.add(device)
        success += 1
    session.add(
        DevAccessLog(
            action="批量导入",
            result="成功" if failed == 0 else "部分成功",
            message=f"成功 {success} 条，失败 {failed} 条",
            operator_id=operator_id,
        )
    )
    await session.commit()
    return {"success": success, "failed": failed, "messages": messages}


def _parse_import_file(filename: str, content: bytes) -> list[dict]:
    lower = filename.lower()
    if lower.endswith(".csv"):
        text = content.decode("utf-8-sig")
        return list(csv.DictReader(io.StringIO(text)))
    if lower.endswith(".xlsx"):
        from openpyxl import load_workbook

        wb = load_workbook(io.BytesIO(content), read_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            return []
        header = [str(c).strip() if c is not None else "" for c in rows[0]]
        result = []
        for r in rows[1:]:
            result.append({header[i]: ("" if v is None else str(v)) for i, v in enumerate(r) if i < len(header)})
        return result
    raise BizException("仅支持 .csv 或 .xlsx 文件")


async def page_access_logs(
    session: AsyncSession,
    params: PageParams,
    keyword: str | None = None,
    action: str | None = None,
    result: str | None = None,
) -> dict:
    stmt = select(DevAccessLog)
    if keyword:
        stmt = stmt.where(DevAccessLog.message.ilike(f"%{keyword}%"))
    if action:
        stmt = stmt.where(DevAccessLog.action == action)
    if result:
        stmt = stmt.where(DevAccessLog.result == result)
    total, rows = await paginate_query(session, stmt.order_by(DevAccessLog.id.desc()), params)
    # 设备名称映射
    ids = {r.device_id for r in rows if r.device_id}
    devices = {}
    if ids:
        dev_rows = (await session.execute(select(DevDevice.id, DevDevice.device_name).where(DevDevice.id.in_(ids)))).all()
        devices = {r[0]: r[1] for r in dev_rows}
    items = []
    for r in rows:
        d = r.model_dump()
        d["device_name"] = devices.get(r.device_id, "-")
        items.append(d)
    return {"total": total, "items": items}


# ==================== 测点 ====================


async def page_points(
    session: AsyncSession,
    params: PageParams,
    keyword: str | None = None,
    device_id: int | None = None,
) -> dict:
    stmt = select(DevPoint)
    if keyword:
        stmt = stmt.where(or_(DevPoint.point_code.ilike(f"%{keyword}%"), DevPoint.point_name.ilike(f"%{keyword}%")))
    if device_id:
        stmt = stmt.where(DevPoint.device_id == device_id)
    total, rows = await paginate_query(session, stmt.order_by(DevPoint.device_id, DevPoint.sort_no), params)
    ids = {r.device_id for r in rows if r.device_id}
    devices = {}
    if ids:
        dev_rows = (await session.execute(select(DevDevice.id, DevDevice.device_name).where(DevDevice.id.in_(ids)))).all()
        devices = {r[0]: r[1] for r in dev_rows}
    items = []
    for r in rows:
        d = r.model_dump()
        d["device_name"] = devices.get(r.device_id, "-")
        items.append(d)
    return {"total": total, "items": items}


async def create_point(session: AsyncSession, data: dict) -> DevPoint:
    obj = DevPoint(**data)
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return obj


async def update_point(session: AsyncSession, point_id: int, data: dict) -> DevPoint:
    obj = await session.get(DevPoint, point_id)
    if not obj:
        raise BizException("测点不存在")
    for k, v in data.items():
        setattr(obj, k, v)
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return obj


async def delete_point(session: AsyncSession, point_id: int) -> None:
    obj = await session.get(DevPoint, point_id)
    if not obj:
        raise BizException("测点不存在")
    await session.delete(obj)
    await session.commit()


# ==================== 采集任务 ====================


async def page_collect_tasks(
    session: AsyncSession,
    params: PageParams,
    keyword: str | None = None,
    device_id: int | None = None,
) -> dict:
    stmt = select(DevCollectTask)
    if keyword:
        stmt = stmt.where(DevCollectTask.task_name.ilike(f"%{keyword}%"))
    if device_id:
        stmt = stmt.where(DevCollectTask.device_id == device_id)
    total, rows = await paginate_query(session, stmt.order_by(DevCollectTask.id.desc()), params)
    ids = {r.device_id for r in rows if r.device_id}
    devices = {}
    if ids:
        dev_rows = (await session.execute(select(DevDevice.id, DevDevice.device_name).where(DevDevice.id.in_(ids)))).all()
        devices = {r[0]: r[1] for r in dev_rows}
    items = []
    for r in rows:
        d = r.model_dump()
        d["device_name"] = devices.get(r.device_id, "-")
        items.append(d)
    return {"total": total, "items": items}


async def save_collect_task(session: AsyncSession, task_id: int | None, data: dict) -> DevCollectTask:
    if task_id:
        obj = await session.get(DevCollectTask, task_id)
        if not obj:
            raise BizException("采集任务不存在")
        for k, v in data.items():
            setattr(obj, k, v)
        obj.updated_at = datetime.now().astimezone()
    else:
        obj = DevCollectTask(**data)
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return obj


# ==================== 历史数据 ====================


async def page_data(
    session: AsyncSession,
    params: PageParams,
    device_id: int | None = None,
    point_id: int | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    data_quality: str | None = None,
) -> dict:
    stmt = select(DevData)
    if device_id:
        stmt = stmt.where(DevData.device_id == device_id)
    if point_id:
        stmt = stmt.where(DevData.point_id == point_id)
    if start_time:
        stmt = stmt.where(DevData.collect_time >= datetime.fromisoformat(start_time))
    if end_time:
        stmt = stmt.where(DevData.collect_time <= datetime.fromisoformat(end_time))
    if data_quality:
        stmt = stmt.where(DevData.data_quality == data_quality)
    total, rows = await paginate_query(session, stmt.order_by(DevData.collect_time.desc(), DevData.id.desc()), params)
    return {"total": total, "items": [r.model_dump() for r in rows]}


async def patch_data(session: AsyncSession, payload: DataPatchRequest, operator_id: int | None) -> dict:
    data = await session.get(DevData, payload.data_id)
    if not data:
        raise BizException("原始数据不存在")
    session.add(
        DevDataPatch(
            data_id=payload.data_id,
            patch_value=payload.patch_value,
            reason=payload.reason,
            operator_id=operator_id,
        )
    )
    data.collect_value = payload.patch_value
    data.data_quality = "patched"
    session.add(data)
    await session.commit()
    return {"data_id": payload.data_id, "collect_value": payload.patch_value, "data_quality": "patched"}


async def set_data_quality(session: AsyncSession, data_id: int, quality: str) -> DevData:
    data = await session.get(DevData, data_id)
    if not data:
        raise BizException("数据不存在")
    data.data_quality = quality
    session.add(data)
    await session.commit()
    await session.refresh(data)
    return data


async def count_data(session: AsyncSession, device_id: int | None = None) -> int:
    stmt = select(func.count()).select_from(DevData)
    if device_id:
        stmt = stmt.where(DevData.device_id == device_id)
    return (await session.execute(stmt)).scalar_one()
