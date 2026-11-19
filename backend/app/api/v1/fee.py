"""费用域接口（B5-2 费用统计/对比/报表/导出）。"""

from fastapi import APIRouter, Depends, Query, Response

from app.core.deps import SessionDep, require_perm
from app.core.response import success
from app.services import fee_service as svc

router = APIRouter(prefix="/fee", tags=["费用管理"])


@router.get("/stat", summary="费用统计", dependencies=[Depends(require_perm("price:stat:view"))])
async def fee_stat(session: SessionDep, dim: str = Query("period", description="维度：period/month/area")):
    return success(await svc.stat(session, dim))


@router.get("/compare", summary="费用对比（环比/同比/分时）", dependencies=[Depends(require_perm("price:stat:view"))])
async def fee_compare(session: SessionDep):
    return success(await svc.compare(session))


@router.get("/report", summary="费用报表", dependencies=[Depends(require_perm("price:report:view"))])
async def fee_report(session: SessionDep, year: int | None = Query(None)):
    return success(await svc.report(session, year))


@router.get("/export", summary="费用报表导出", dependencies=[Depends(require_perm("price:report:view"))])
async def fee_export(session: SessionDep, year: int | None = Query(None)):
    content = await svc.export_report(session, year)
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=fee_report.xlsx"},
    )
