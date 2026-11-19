"""数据驾驶舱接口（B7）。"""

from fastapi import APIRouter, Depends, Query

from app.core.deps import SessionDep, require_perm
from app.core.response import success
from app.services import dashboard_service as svc

router = APIRouter(prefix="/dashboard", tags=["数据驾驶舱"])


@router.get("/overview", summary="关键指标卡", dependencies=[Depends(require_perm("dashboard:view"))])
async def overview(session: SessionDep):
    return success(await svc.overview(session))


@router.get("/energy-trend", summary="能耗趋势", dependencies=[Depends(require_perm("dashboard:view"))])
async def energy_trend(session: SessionDep, days: int = Query(7, ge=3, le=90)):
    return success(await svc.energy_trend(session, days))


@router.get("/energy-item-ratio", summary="分项用电占比", dependencies=[Depends(require_perm("dashboard:view"))])
async def energy_item_ratio(session: SessionDep):
    return success(await svc.energy_item_ratio(session))


@router.get("/area-rank", summary="区域用电排名", dependencies=[Depends(require_perm("dashboard:view"))])
async def area_rank(session: SessionDep, limit: int = Query(8, ge=3, le=20)):
    return success(await svc.area_rank(session, limit=limit))


@router.get("/carbon-overview", summary="碳排总览", dependencies=[Depends(require_perm("dashboard:view"))])
async def carbon_overview(session: SessionDep, year: int | None = Query(None)):
    return success(await svc.carbon_overview(session, year))


@router.get("/device-status", summary="设备状态分布", dependencies=[Depends(require_perm("dashboard:view"))])
async def device_status(session: SessionDep):
    return success(await svc.device_status(session))


@router.get("/latest-alarms", summary="最新告警", dependencies=[Depends(require_perm("dashboard:view"))])
async def latest_alarms(session: SessionDep, limit: int = Query(10, ge=1, le=50)):
    return success(await svc.latest_alarms(session, limit))


@router.get("/fee-quota", summary="费用与定额概览", dependencies=[Depends(require_perm("dashboard:view"))])
async def fee_quota(session: SessionDep):
    return success(await svc.fee_quota(session))
