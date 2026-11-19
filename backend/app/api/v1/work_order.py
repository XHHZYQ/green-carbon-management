"""工单管理接口（B6：工单列表/详情/新建/编辑/指派/处理/完成/删除）。"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.deps import SessionDep, require_perm
from app.core.pagination import PageDep
from app.core.response import paginate, success
from app.models.sys import SysUser
from app.schemas.alarm import (
    WorkOrderAssignRequest,
    WorkOrderCreate,
    WorkOrderHandleRequest,
    WorkOrderUpdate,
)
from app.services import wo_service as svc

router = APIRouter(prefix="/wo", tags=["工单管理"])

VIEW = "alarm:work-order:view"
HANDLE = "alarm:work-order:handle"


@router.get("/work-orders", summary="工单列表", dependencies=[Depends(require_perm(VIEW))])
async def list_work_orders(
    session: SessionDep,
    params: PageDep,
    status: str | None = Query(None),
    source: str | None = Query(None),
    level: str | None = Query(None),
    type: str | None = Query(None),
    assignee_id: int | None = Query(None),
    keyword: str | None = Query(None),
):
    total, items = await svc.page_work_orders(
        session, params.page, params.page_size, status, source, level, type, assignee_id, keyword
    )
    return success(paginate(total, items))


@router.post("/work-orders", summary="新建工单")
async def create_work_order(
    session: SessionDep,
    payload: WorkOrderCreate,
    user: Annotated[SysUser, Depends(require_perm(HANDLE))],
):
    return success(await svc.create_work_order(session, payload.model_dump(), user.id), message="新建成功")


@router.get("/work-orders/{work_order_id}", summary="工单详情", dependencies=[Depends(require_perm(VIEW))])
async def get_work_order(work_order_id: int, session: SessionDep):
    return success(await svc.get_work_order(session, work_order_id))


@router.put("/work-orders/{work_order_id}", summary="编辑工单")
async def update_work_order(
    work_order_id: int,
    session: SessionDep,
    payload: WorkOrderUpdate,
    _: Annotated[SysUser, Depends(require_perm(HANDLE))],
):
    return success(await svc.update_work_order(session, work_order_id, payload.model_dump()), message="修改成功")


@router.delete("/work-orders/{work_order_id}", summary="删除工单")
async def delete_work_order(
    work_order_id: int,
    session: SessionDep,
    _: Annotated[SysUser, Depends(require_perm(HANDLE))],
):
    await svc.delete_work_order(session, work_order_id)
    return success(message="删除成功")


@router.put("/work-orders/{work_order_id}/assign", summary="指派工单")
async def assign_work_order(
    work_order_id: int,
    session: SessionDep,
    payload: WorkOrderAssignRequest,
    _: Annotated[SysUser, Depends(require_perm(HANDLE))],
):
    return success(await svc.assign_work_order(session, work_order_id, payload.assignee_id), message="指派成功")


@router.put("/work-orders/{work_order_id}/handle", summary="处理工单")
async def handle_work_order(
    work_order_id: int,
    session: SessionDep,
    payload: WorkOrderHandleRequest,
    _: Annotated[SysUser, Depends(require_perm(HANDLE))],
):
    return success(await svc.handle_work_order(session, work_order_id, payload.handle_result), message="处理成功")


@router.put("/work-orders/{work_order_id}/finish", summary="完成工单")
async def finish_work_order(
    work_order_id: int,
    session: SessionDep,
    _: Annotated[SysUser, Depends(require_perm(HANDLE))],
    payload: WorkOrderHandleRequest | None = None,
):
    handle_result = payload.handle_result if payload else None
    return success(await svc.finish_work_order(session, work_order_id, handle_result), message="工单已完成")
