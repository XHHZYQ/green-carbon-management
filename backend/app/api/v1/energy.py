"""能耗域接口（B5-1 能耗管理）。"""

from datetime import date

from fastapi import APIRouter, Depends, Query, Response

from app.core.deps import SessionDep, require_perm
from app.core.response import success
from app.services import energy_service as svc

router = APIRouter(prefix="/energy", tags=["能耗管理"])


@router.get("/overview", summary="能耗总览", dependencies=[Depends(require_perm("energy:overview:view"))])
async def energy_overview(session: SessionDep):
    return success(await svc.overview(session))


@router.get("/analysis", summary="能耗分析（区域/分项/设备）", dependencies=[Depends(require_perm("energy:analysis:view"))])
async def energy_analysis(
    session: SessionDep,
    dim: str = Query("area", description="维度：area/item/device"),
    start: date | None = Query(None),
    end: date | None = Query(None),
):
    return success(await svc.analysis(session, dim, start, end))


@router.get("/item-ratio", summary="分项计量占比", dependencies=[Depends(require_perm("energy:item:view"))])
async def energy_item_ratio(
    session: SessionDep,
    start: date | None = Query(None),
    end: date | None = Query(None),
):
    return success(await svc.item_ratio(session, start, end))


@router.get("/peak-valley", summary="峰谷用电分析", dependencies=[Depends(require_perm("energy:item:view"))])
async def energy_peak_valley(
    session: SessionDep,
    start: date | None = Query(None),
    end: date | None = Query(None),
):
    return success(await svc.peak_valley(session, start, end))


@router.get("/rank", summary="能耗排名", dependencies=[Depends(require_perm("energy:analysis:view"))])
async def energy_rank(
    session: SessionDep,
    dim: str = Query("area", description="维度：area/device"),
    start: date | None = Query(None),
    end: date | None = Query(None),
    limit: int = Query(10, ge=1, le=50),
):
    return success(await svc.rank(session, dim, start, end, limit))


@router.get("/cost", summary="能耗成本", dependencies=[Depends(require_perm("energy:analysis:view"))])
async def energy_cost(session: SessionDep, months: int = Query(6, ge=1, le=12)):
    return success(await svc.cost(session, months))


@router.get("/export", summary="能耗数据导出", dependencies=[Depends(require_perm("energy:export"))])
async def energy_export(
    session: SessionDep,
    start: date | None = Query(None),
    end: date | None = Query(None),
):
    content = await svc.export_energy(session, start, end)
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=energy_stat.xlsx"},
    )
