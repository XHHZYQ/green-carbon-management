"""控制域接口（B4-1 设备控制）。"""

from fastapi import APIRouter, Depends, Query

from app.core.deps import CurrentUser, SessionDep, require_perm
from app.core.pagination import PageDep
from app.core.response import paginate, success
from app.schemas.control import BatchCommandCreate, CommandCreate, TimedTaskCreate, TimedTaskUpdate
from app.services import control_service as svc

router = APIRouter(prefix="/control", tags=["设备控制"])


@router.get("/points", summary="设备可控点（控制面板）", dependencies=[Depends(require_perm("control:panel:view"))])
async def control_points(
    session: SessionDep,
    device_id: int | None = Query(None),
    area_id: int | None = Query(None),
    keyword: str | None = Query(None),
):
    return success(await svc.control_points(session, device_id, area_id, keyword))


@router.post("/command", summary="单设备控制下发", dependencies=[Depends(require_perm("control:command:send"))])
async def send_command(session: SessionDep, user: CurrentUser, payload: CommandCreate):
    return success(await svc.send_command(session, payload, user.id), message="指令已下发")


@router.post("/batch", summary="批量控制下发", dependencies=[Depends(require_perm("control:command:send"))])
async def send_batch(session: SessionDep, user: CurrentUser, payload: BatchCommandCreate):
    return success(await svc.send_batch(session, payload, user.id), message="批量指令已下发")


@router.get("/commands", summary="控制记录", dependencies=[Depends(require_perm("control:record:view"))])
async def list_commands(
    session: SessionDep,
    params: PageDep,
    keyword: str | None = Query(None),
    device_id: int | None = Query(None),
    status: str | None = Query(None),
    source: str | None = Query(None),
):
    return success(paginate(**await svc.page_commands(session, params, keyword, device_id, status, source)))


@router.get("/commands/{command_id}", summary="控制记录详情", dependencies=[Depends(require_perm("control:record:view"))])
async def command_detail(command_id: int, session: SessionDep):
    return success(await svc.get_command(session, command_id))


@router.get("/timed-tasks", summary="定时任务列表", dependencies=[Depends(require_perm("control:timed:view"))])
async def list_timed_tasks(
    session: SessionDep,
    params: PageDep,
    keyword: str | None = Query(None),
    device_id: int | None = Query(None),
):
    return success(paginate(**await svc.page_timed_tasks(session, params, keyword, device_id)))


@router.post("/timed-tasks", summary="新增定时任务", dependencies=[Depends(require_perm("control:timed:add"))])
async def create_timed_task(session: SessionDep, user: CurrentUser, payload: TimedTaskCreate):
    return success(await svc.save_timed_task(session, None, payload.model_dump(), user.id), message="新增成功")


@router.put("/timed-tasks/{task_id}", summary="编辑定时任务", dependencies=[Depends(require_perm("control:timed:add"))])
async def update_timed_task(session: SessionDep, user: CurrentUser, task_id: int, payload: TimedTaskUpdate):
    return success(await svc.save_timed_task(session, task_id, payload.model_dump(exclude_unset=True), user.id), message="修改成功")


@router.delete("/timed-tasks/{task_id}", summary="删除定时任务", dependencies=[Depends(require_perm("control:timed:add"))])
async def delete_timed_task(session: SessionDep, task_id: int):
    await svc.delete_timed_task(session, task_id)
    return success(None, message="删除成功")
