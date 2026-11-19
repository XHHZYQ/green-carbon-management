"""告警中心接口（B6：告警规则 CRUD + 告警列表/详情/确认/处理/转工单/统计）。"""

from typing import Annotated

from fastapi import APIRouter, Body, Depends, Query

from app.api.v1._crud import crud_router
from app.core.deps import SessionDep, require_perm
from app.core.pagination import PageDep
from app.core.response import paginate, success
from app.models.alarm import AlarmRule
from app.models.sys import SysUser
from app.schemas.alarm import AlarmConfirmRequest, AlarmHandleRequest
from app.services import alarm_service as svc

router = APIRouter(prefix="/alarm", tags=["告警与工单"])

# 告警规则：通用 CRUD
router.include_router(
    crud_router(
        model=AlarmRule,
        prefix="/rules",
        tag="告警规则",
        read_perm="alarm:view",
        write_perm="alarm:center:confirm",
        search_fields=("rule_name",),
    )
)


@router.get("/infos", summary="告警列表", dependencies=[Depends(require_perm("alarm:center:view"))])
async def list_alarms(
    session: SessionDep,
    params: PageDep,
    level: str | None = Query(None),
    status: str | None = Query(None),
    alarm_type: str | None = Query(None),
    device_id: int | None = Query(None),
    keyword: str | None = Query(None),
):
    total, items = await svc.page_alarms(
        session, params.page, params.page_size, level, status, alarm_type, device_id, keyword
    )
    return success(paginate(total, items))


@router.get("/statistics", summary="告警统计", dependencies=[Depends(require_perm("alarm:center:view"))])
async def get_statistics(session: SessionDep):
    return success(await svc.alarm_statistics(session))


@router.get("/infos/{alarm_id}", summary="告警详情", dependencies=[Depends(require_perm("alarm:center:view"))])
async def get_alarm(alarm_id: int, session: SessionDep):
    return success(await svc.get_alarm(session, alarm_id))


@router.put("/infos/{alarm_id}/confirm", summary="确认告警")
async def confirm_alarm(
    alarm_id: int,
    session: SessionDep,
    user: Annotated[SysUser, Depends(require_perm("alarm:center:confirm"))],
    payload: AlarmConfirmRequest | None = Body(None),
):
    return success(await svc.confirm_alarm(session, alarm_id, user.id), message="确认成功")


@router.put("/infos/{alarm_id}/handle", summary="处理告警")
async def handle_alarm(
    alarm_id: int,
    session: SessionDep,
    user: Annotated[SysUser, Depends(require_perm("alarm:center:confirm"))],
    payload: AlarmHandleRequest | None = Body(None),
):
    return success(await svc.handle_alarm(session, alarm_id, user.id), message="处理成功")


@router.post("/infos/{alarm_id}/work-order", summary="告警转工单")
async def alarm_to_work_order(
    alarm_id: int,
    session: SessionDep,
    user: Annotated[SysUser, Depends(require_perm("alarm:center:confirm"))],
):
    return success(await svc.create_work_order_from_alarm(session, alarm_id, user.id), message="工单已生成")
