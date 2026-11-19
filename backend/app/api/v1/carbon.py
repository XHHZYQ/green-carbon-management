"""碳排放域接口（B5-3 碳排总览/核算/明细/报告/减排对比）。"""

from fastapi import APIRouter, Depends, Query, Response

from app.core.deps import CurrentUser, SessionDep, require_perm
from app.core.pagination import PageDep
from app.core.response import paginate, success
from app.schemas.carbon import CarbonCalcRequest, CarbonReportCreate
from app.services import carbon_service as svc

router = APIRouter(prefix="/carbon", tags=["碳排放管理"])


@router.get("/overview", summary="碳排放总览", dependencies=[Depends(require_perm("carbon:overview:view"))])
async def carbon_overview(session: SessionDep, year: int | None = Query(None)):
    return success(await svc.overview(session, year))


@router.post("/calc", summary="执行碳排放核算", dependencies=[Depends(require_perm("carbon:accounting:view"))])
async def carbon_calc(session: SessionDep, payload: CarbonCalcRequest):
    return success(await svc.calc(session, payload.period_type, payload.period_value), message="核算完成")


@router.get("/emissions", summary="碳排放明细", dependencies=[Depends(require_perm("carbon:accounting:view"))])
async def carbon_emissions(
    session: SessionDep,
    params: PageDep,
    period_type: str | None = Query(None),
    area_id: int | None = Query(None),
):
    total, items = await svc.page_emissions(session, params.page, params.page_size, period_type, area_id)
    return success(paginate(total, items))


@router.get("/reports", summary="碳报告列表", dependencies=[Depends(require_perm("carbon:report:view"))])
async def carbon_reports(session: SessionDep, params: PageDep):
    total, items = await svc.page_reports(session, params.page, params.page_size)
    return success(paginate(total, items))


@router.post("/reports", summary="生成碳报告", dependencies=[Depends(require_perm("carbon:report:generate"))])
async def create_carbon_report(session: SessionDep, payload: CarbonReportCreate):
    return success(await svc.create_report(session, payload.model_dump()), message="报告生成成功")


@router.get("/reports/{report_id}/export", summary="碳报告导出", dependencies=[Depends(require_perm("carbon:report:view"))])
async def export_carbon_report(report_id: int, session: SessionDep):
    content, name = await svc.export_report(session, report_id)
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=carbon_report_{report_id}.xlsx"},
    )


@router.get("/reduction-compare", summary="减排对比", dependencies=[Depends(require_perm("carbon:report:view"))])
async def carbon_reduction_compare(session: SessionDep):
    return success(await svc.reduction_compare(session))
