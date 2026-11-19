"""设备管理 + 设备接入接口。"""

from fastapi import APIRouter, Body, Depends, File, Query, UploadFile
from fastapi.responses import Response

from app.core.deps import CurrentUser, SessionDep, require_perm
from app.core.exceptions import BizException
from app.core.pagination import PageDep
from app.core.response import paginate, success
from app.models.dev import DevArea
from app.schemas.device import AreaCreate, AreaUpdate, DeviceCreate, DeviceUpdate, TestConnectionRequest
from app.services import device_service as svc

router = APIRouter(tags=["设备域"])


# ==================== 区域分组 ====================

area_router = APIRouter(prefix="/areas", tags=["区域分组"])


@area_router.get("/tree", summary="区域树", dependencies=[Depends(require_perm("device:area:view"))])
async def area_tree(session: SessionDep):
    return success(await svc.build_area_tree(session))


@area_router.post("", summary="新增区域", dependencies=[Depends(require_perm("device:list:edit"))])
async def create_area(session: SessionDep, payload: AreaCreate):
    obj = DevArea(**payload.model_dump())
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return success(obj, message="新增成功")


@area_router.put("/{area_id}", summary="编辑区域", dependencies=[Depends(require_perm("device:list:edit"))])
async def update_area(area_id: int, session: SessionDep, payload: AreaUpdate):
    obj = await session.get(DevArea, area_id)
    if not obj:
        raise BizException("区域不存在")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return success(obj, message="修改成功")


@area_router.delete("/{area_id}", summary="删除区域", dependencies=[Depends(require_perm("device:list:edit"))])
async def delete_area(area_id: int, session: SessionDep):
    obj = await session.get(DevArea, area_id)
    if not obj:
        raise BizException("区域不存在")
    await session.delete(obj)
    await session.commit()
    return success(message="删除成功")


# ==================== 接入向导（静态路由需在 /{id} 之前）====================

wizard_router = APIRouter(prefix="/devices", tags=["设备接入"])


@wizard_router.get("/wizard/types", summary="可选设备类型", dependencies=[Depends(require_perm("access:wizard:view"))])
async def wizard_types(session: SessionDep):
    return success(await svc.wizard_types(session))


@wizard_router.get("/wizard/protocols", summary="可选协议", dependencies=[Depends(require_perm("access:wizard:view"))])
async def wizard_protocols(session: SessionDep, device_type_id: int | None = Query(None)):
    return success(await svc.wizard_protocols(session, device_type_id))


@wizard_router.get("/wizard/params", summary="协议参数模板", dependencies=[Depends(require_perm("access:wizard:view"))])
async def wizard_params(session: SessionDep, protocol_id: int | None = Query(None)):
    return success(await svc.wizard_params(session, protocol_id))


@wizard_router.post("/test-connection", summary="测试连接", dependencies=[Depends(require_perm("access:wizard:view"))])
async def test_connection(payload: TestConnectionRequest):
    return success(svc.test_connection(payload))


@wizard_router.get("/import/template", summary="下载导入模板", dependencies=[Depends(require_perm("access:import:view"))])
async def import_template():
    content = svc.build_import_template()
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=device_import_template.xlsx"},
    )


@wizard_router.post("/import", summary="批量导入设备", dependencies=[Depends(require_perm("access:import:view"))])
async def import_devices(
    session: SessionDep,
    user: CurrentUser,
    file: UploadFile = File(...),
):
    result = await svc.import_devices(session, file.filename or "", await file.read(), user.id)
    return success(result, message=f"导入完成：成功 {result['success']} 条，失败 {result['failed']} 条")


@wizard_router.get("/access-logs", summary="接入记录", dependencies=[Depends(require_perm("access:log:view"))])
async def access_logs(
    session: SessionDep,
    params: PageDep,
    keyword: str | None = Query(None),
    action: str | None = Query(None),
    result: str | None = Query(None),
):
    return success(paginate(**await svc.page_access_logs(session, params, keyword, action, result)))


# ==================== 设备台账 ====================

device_router = APIRouter(prefix="/devices", tags=["设备台账"])


@device_router.get("", summary="设备台账", dependencies=[Depends(require_perm("device:list:view"))])
async def list_devices(
    session: SessionDep,
    params: PageDep,
    keyword: str | None = Query(None),
    area_id: int | None = Query(None),
    device_type_id: int | None = Query(None),
    online_status: str | None = Query(None),
    status: str | None = Query(None),
):
    data = await svc.page_devices(session, params, keyword, area_id, device_type_id, online_status, status)
    return success(paginate(**data))


@device_router.post("", summary="新增设备并上线", dependencies=[Depends(require_perm("access:device:add"))])
async def create_device(session: SessionDep, user: CurrentUser, payload: DeviceCreate):
    device = await svc.create_device(session, payload, user.id)
    return success({"id": device.id, "device_code": device.device_code}, message="设备接入成功")


@device_router.get("/{device_id}", summary="设备详情", dependencies=[Depends(require_perm("device:detail:view"))])
async def device_detail(session: SessionDep, device_id: int):
    return success(await svc.get_device_detail(session, device_id))


@device_router.put("/{device_id}", summary="编辑设备", dependencies=[Depends(require_perm("device:list:edit"))])
async def update_device(session: SessionDep, user: CurrentUser, device_id: int, payload: DeviceUpdate):
    return success(await svc.update_device(session, device_id, payload, user.id), message="修改成功")


@device_router.put(
    "/{device_id}/online-status", summary="上线/下线", dependencies=[Depends(require_perm("access:device:edit"))]
)
async def online_status(session: SessionDep, user: CurrentUser, device_id: int, online: bool = Body(..., embed=True)):
    device = await svc.set_online_status(session, device_id, online, user.id)
    return success({"online_status": device.online_status}, message="操作成功")


@device_router.delete("/{device_id}", summary="删除设备", dependencies=[Depends(require_perm("device:list:delete"))])
async def delete_device(session: SessionDep, device_id: int):
    await svc.delete_device(session, device_id)
    return success(message="删除成功")


router.include_router(area_router)
router.include_router(wizard_router)
router.include_router(device_router)
