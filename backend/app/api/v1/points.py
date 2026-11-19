"""测点与数据接口。"""

from fastapi import APIRouter, Depends, Query

from app.api.v1._crud import crud_router
from app.core.deps import CurrentUser, SessionDep, require_perm
from app.core.pagination import PageDep
from app.core.response import paginate, success
from app.models.dev import DevPointTemplate
from app.schemas.device import (
    CollectTaskCreate,
    CollectTaskUpdate,
    DataPatchRequest,
    DataQualityRequest,
    PointCreate,
    PointUpdate,
)
from app.services import device_service as svc

router = APIRouter(tags=["测点与数据"])

# 测点模板：标准 CRUD
router.include_router(
    crud_router(
        model=DevPointTemplate,
        prefix="/point-templates",
        tag="测点模板",
        read_perm="point:list:view",
        write_perm="point:list:edit",
        order_by="id",
        search_fields=("template_code", "template_name"),
    )
)


# ==================== 测点 ====================
@router.get("/points", summary="测点列表", dependencies=[Depends(require_perm("point:list:view"))])
async def list_points(
    session: SessionDep,
    params: PageDep,
    keyword: str | None = Query(None),
    device_id: int | None = Query(None),
):
    return success(paginate(**await svc.page_points(session, params, keyword, device_id)))


@router.post("/points", summary="新增测点", dependencies=[Depends(require_perm("point:list:edit"))])
async def create_point(session: SessionDep, payload: PointCreate):
    return success(await svc.create_point(session, payload.model_dump()), message="新增成功")


@router.put("/points/{point_id}", summary="编辑测点", dependencies=[Depends(require_perm("point:list:edit"))])
async def update_point(session: SessionDep, point_id: int, payload: PointUpdate):
    return success(await svc.update_point(session, point_id, payload.model_dump(exclude_unset=True)), message="修改成功")


@router.delete("/points/{point_id}", summary="删除测点", dependencies=[Depends(require_perm("point:list:edit"))])
async def delete_point(session: SessionDep, point_id: int):
    await svc.delete_point(session, point_id)
    return success(message="删除成功")


# ==================== 采集任务 ====================
@router.get("/collect-tasks", summary="采集任务列表", dependencies=[Depends(require_perm("point:task:view"))])
async def list_collect_tasks(
    session: SessionDep,
    params: PageDep,
    keyword: str | None = Query(None),
    device_id: int | None = Query(None),
):
    return success(paginate(**await svc.page_collect_tasks(session, params, keyword, device_id)))


@router.post("/collect-tasks", summary="新增采集任务", dependencies=[Depends(require_perm("point:task:view"))])
async def create_collect_task(session: SessionDep, payload: CollectTaskCreate):
    return success(await svc.save_collect_task(session, None, payload.model_dump()), message="新增成功")


@router.put("/collect-tasks/{task_id}", summary="编辑采集任务", dependencies=[Depends(require_perm("point:task:view"))])
async def update_collect_task(session: SessionDep, task_id: int, payload: CollectTaskUpdate):
    return success(await svc.save_collect_task(session, task_id, payload.model_dump(exclude_unset=True)), message="修改成功")


# ==================== 历史数据 ====================
@router.get("/data", summary="历史数据查询", dependencies=[Depends(require_perm("point:history:view"))])
async def list_data(
    session: SessionDep,
    params: PageDep,
    device_id: int | None = Query(None),
    point_id: int | None = Query(None),
    start_time: str | None = Query(None),
    end_time: str | None = Query(None),
    data_quality: str | None = Query(None),
):
    data = await svc.page_data(session, params, device_id, point_id, start_time, end_time, data_quality)
    return success(paginate(**data))


@router.post("/data/patch", summary="数据补录", dependencies=[Depends(require_perm("point:patch:edit"))])
async def patch_data(session: SessionDep, user: CurrentUser, payload: DataPatchRequest):
    return success(await svc.patch_data(session, payload, user.id), message="补录成功")


@router.put("/data/{data_id}/quality", summary="数据质量标记", dependencies=[Depends(require_perm("point:patch:edit"))])
async def set_quality(session: SessionDep, data_id: int, payload: DataQualityRequest):
    return success(await svc.set_data_quality(session, data_id, payload.data_quality), message="标记成功")
