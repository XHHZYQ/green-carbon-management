"""节能定额域接口（B6 定额/监控/考核）。"""

from fastapi import APIRouter, Depends, Query

from app.api.v1._crud import crud_router
from app.core.deps import CurrentUser, SessionDep, require_perm
from app.core.pagination import PageDep
from app.core.response import paginate, success
from app.models.quota import EnergyQuota
from app.schemas.quota import QuotaAssessGenerateRequest, QuotaMonitorRefreshRequest
from app.services import quota_service as svc

router = APIRouter(prefix="/quota", tags=["节能与定额"])

# 定额 CRUD（/quota/quotas）
router.include_router(
    crud_router(
        model=EnergyQuota,
        prefix="/quotas",
        tag="能耗定额",
        read_perm="quota:list:view",
        write_perm="quota:list:edit",
        search_fields=("quota_name",),
    )
)


@router.get("/tree", summary="定额树", dependencies=[Depends(require_perm("quota:list:view"))])
async def quota_tree(session: SessionDep):
    return success(await svc.quota_tree(session))


@router.get("/monitors", summary="定额监控列表", dependencies=[Depends(require_perm("quota:monitor:view"))])
async def quota_monitors(
    session: SessionDep,
    params: PageDep,
    warn_status: str | None = Query(None),
    period_value: str | None = Query(None),
):
    total, items = await svc.page_monitors(session, params.page, params.page_size, warn_status, period_value)
    return success(paginate(total, items))


@router.post("/monitors/refresh", summary="刷新定额监控", dependencies=[Depends(require_perm("quota:monitor:view"))])
async def quota_monitor_refresh(
    session: SessionDep, user: CurrentUser, payload: QuotaMonitorRefreshRequest
):
    result = await svc.refresh_monitor(session, payload.period_value, user.id)
    return success(result, message="监控刷新完成")


@router.get("/assess", summary="考核列表", dependencies=[Depends(require_perm("quota:assess:view"))])
async def quota_assess_list(
    session: SessionDep,
    params: PageDep,
    period_value: str | None = Query(None),
):
    total, items = await svc.page_assess(session, params.page, params.page_size, period_value)
    return success(paginate(total, items))


@router.post("/assess/generate", summary="生成定额考核", dependencies=[Depends(require_perm("quota:assess:view"))])
async def quota_assess_generate(
    session: SessionDep, user: CurrentUser, payload: QuotaAssessGenerateRequest
):
    return success(await svc.generate_assess(session, payload.period_value, user.id), message="考核生成完成")


@router.get("/report", summary="考核报表", dependencies=[Depends(require_perm("quota:assess:view"))])
async def quota_report(session: SessionDep, year: int | None = Query(None)):
    return success(await svc.assess_report(session, year))
