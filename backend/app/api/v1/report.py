"""报表中心接口（B7 报表模板 / 生成 / 自定义 / 记录 / 导出 / 订阅）。"""

from urllib.parse import quote

from fastapi import APIRouter, Depends, Query, Response

from app.core.deps import CurrentUser, SessionDep, require_perm
from app.core.pagination import PageDep
from app.core.response import paginate, success
from app.schemas.report import (
    ReportCustomRequest,
    ReportGenerateRequest,
    ReportSubscribeUpsert,
    ReportTemplateUpsert,
)
from app.services import report_service as svc

router = APIRouter(prefix="/reports", tags=["报表中心"])


# ------------------------- 报表模板 -------------------------


@router.get("/templates", summary="报表模板列表", dependencies=[Depends(require_perm("report:center:view"))])
async def list_templates(session: SessionDep, keyword: str | None = Query(None)):
    return success(await svc.list_templates(session, keyword))


@router.post("/templates", summary="新增报表模板", dependencies=[Depends(require_perm("report:center:generate"))])
async def create_template(session: SessionDep, payload: ReportTemplateUpsert):
    return success(await svc.create_template(session, payload), message="模板创建成功")


@router.put("/templates/{template_id}", summary="修改报表模板", dependencies=[Depends(require_perm("report:center:generate"))])
async def update_template(template_id: int, session: SessionDep, payload: ReportTemplateUpsert):
    return success(await svc.update_template(session, template_id, payload), message="模板更新成功")


@router.delete("/templates/{template_id}", summary="删除报表模板", dependencies=[Depends(require_perm("report:center:generate"))])
async def delete_template(template_id: int, session: SessionDep):
    await svc.delete_template(session, template_id)
    return success(message="模板删除成功")


# ------------------------- 生成 / 自定义 -------------------------


@router.post("/generate", summary="按模板生成报表", dependencies=[Depends(require_perm("report:center:generate"))])
async def generate(session: SessionDep, payload: ReportGenerateRequest, user: CurrentUser):
    return success(await svc.generate(session, payload, user.id), message="报表生成成功")


@router.post("/custom", summary="自定义报表", dependencies=[Depends(require_perm("report:center:generate"))])
async def custom(session: SessionDep, payload: ReportCustomRequest, user: CurrentUser):
    return success(await svc.custom(session, payload, user.id), message="自定义报表生成成功")


# ------------------------- 报表记录 -------------------------


@router.get("/records", summary="报表记录列表", dependencies=[Depends(require_perm("report:center:view"))])
async def page_records(
    session: SessionDep,
    params: PageDep,
    report_name: str | None = Query(None),
    report_type: str | None = Query(None),
):
    total, items = await svc.page_records(
        session, params.page, params.page_size, report_name, report_type
    )
    return success(paginate(total, items))


@router.get("/records/{record_id}/export", summary="报表导出（Excel/PDF）", dependencies=[Depends(require_perm("report:center:generate"))])
async def export_record(record_id: int, session: SessionDep, file_type: str = Query("excel")):
    content, filename = await svc.export_record(session, record_id, file_type)
    media = (
        "application/pdf"
        if file_type == "pdf"
        else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    return Response(
        content=content,
        media_type=media,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )


# ------------------------- 报表订阅 -------------------------


@router.get("/subscriptions", summary="订阅列表", dependencies=[Depends(require_perm("report:subscribe:view"))])
async def page_subscriptions(session: SessionDep, params: PageDep):
    total, items = await svc.page_subscriptions(session, params.page, params.page_size)
    return success(paginate(total, items))


@router.post("/subscriptions", summary="新增订阅", dependencies=[Depends(require_perm("report:subscribe:view"))])
async def create_subscription(session: SessionDep, payload: ReportSubscribeUpsert):
    return success(await svc.create_subscription(session, payload), message="订阅创建成功")


@router.put("/subscriptions/{sub_id}", summary="修改订阅", dependencies=[Depends(require_perm("report:subscribe:view"))])
async def update_subscription(sub_id: int, session: SessionDep, payload: ReportSubscribeUpsert):
    return success(await svc.update_subscription(session, sub_id, payload), message="订阅更新成功")


@router.delete("/subscriptions/{sub_id}", summary="删除订阅", dependencies=[Depends(require_perm("report:subscribe:view"))])
async def delete_subscription(sub_id: int, session: SessionDep):
    await svc.delete_subscription(session, sub_id)
    return success(message="订阅删除成功")


@router.post("/subscriptions/{sub_id}/run", summary="立即执行订阅", dependencies=[Depends(require_perm("report:subscribe:view"))])
async def run_subscription(sub_id: int, session: SessionDep, user: CurrentUser):
    return success(await svc.run_subscription(session, sub_id, user.id), message="订阅执行完成")
