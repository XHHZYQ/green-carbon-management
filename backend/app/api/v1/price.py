"""电价域接口（B5-2 电价方案/时段/调整历史）。"""

from fastapi import APIRouter, Depends, Query

from app.core.deps import CurrentUser, SessionDep, require_perm
from app.core.response import success
from app.schemas.price import PricePeriodCreate, PricePeriodUpdate, PricePlanCreate, PricePlanUpdate
from app.services import price_service as svc

router = APIRouter(prefix="/price", tags=["电价管理"])


@router.get("/plans", summary="电价方案列表", dependencies=[Depends(require_perm("price:plan:view"))])
async def list_plans(
    session: SessionDep,
    keyword: str | None = Query(None),
    status: int | None = Query(None),
):
    return success(await svc.page_plans(session, keyword, status))


@router.post("/plans", summary="新增电价方案", dependencies=[Depends(require_perm("price:plan:edit"))])
async def create_plan(session: SessionDep, user: CurrentUser, payload: PricePlanCreate):
    return success(await svc.save_plan(session, None, payload.model_dump(), user.id), message="新增成功")


@router.put("/plans/{plan_id}", summary="编辑电价方案", dependencies=[Depends(require_perm("price:plan:edit"))])
async def update_plan(session: SessionDep, user: CurrentUser, plan_id: int, payload: PricePlanUpdate):
    return success(await svc.save_plan(session, plan_id, payload.model_dump(exclude_unset=True), user.id), message="修改成功")


@router.delete("/plans/{plan_id}", summary="删除电价方案", dependencies=[Depends(require_perm("price:plan:edit"))])
async def delete_plan(plan_id: int, session: SessionDep):
    await svc.delete_plan(session, plan_id)
    return success(None, message="删除成功")


@router.get("/plans/{plan_id}/periods", summary="时段划分列表", dependencies=[Depends(require_perm("price:plan:view"))])
async def list_periods(plan_id: int, session: SessionDep):
    return success(await svc.list_periods(session, plan_id))


@router.post("/plans/{plan_id}/periods", summary="新增时段划分", dependencies=[Depends(require_perm("price:plan:edit"))])
async def create_period(plan_id: int, session: SessionDep, user: CurrentUser, payload: PricePeriodCreate):
    return success(await svc.save_period(session, plan_id, None, payload.model_dump(), user.id), message="新增成功")


@router.put("/periods/{period_id}", summary="编辑时段划分", dependencies=[Depends(require_perm("price:plan:edit"))])
async def update_period(period_id: int, session: SessionDep, user: CurrentUser, payload: PricePeriodUpdate):
    period = await svc.get_period(session, period_id)
    data = payload.model_dump(exclude_unset=True)
    return success(await svc.save_period(session, period.plan_id, period_id, data, user.id), message="修改成功")


@router.delete("/periods/{period_id}", summary="删除时段划分", dependencies=[Depends(require_perm("price:plan:edit"))])
async def delete_period(period_id: int, session: SessionDep):
    await svc.delete_period(session, period_id)
    return success(None, message="删除成功")


@router.get("/plans/{plan_id}/history", summary="电价调整历史", dependencies=[Depends(require_perm("price:plan:view"))])
async def plan_history(plan_id: int, session: SessionDep):
    return success(await svc.list_history(session, plan_id))
