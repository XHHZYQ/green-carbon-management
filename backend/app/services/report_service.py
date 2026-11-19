"""报表中心服务（B7）：模板 / 生成 / 自定义 / 记录 / 导出 / 订阅。"""

import io
from datetime import date, datetime, time, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BizException
from app.models.carbon import CarbonEmission
from app.models.cfg import CfgEnergyItem, CfgEnergyType
from app.models.dev import DevArea, DevDevice
from app.models.energy import EnergyFeeStat, EnergyStat
from app.models.notify import NotifyChannel, NotifyMessage, NotifySendLog
from app.models.report import ReportRecord, ReportSubscribe, ReportTemplate
from app.models.sys import SysUser
from app.schemas.report import (
    ReportCustomRequest,
    ReportGenerateRequest,
    ReportSubscribeUpsert,
    ReportTemplateUpsert,
)

REPORT_TYPE_NAMES = {"daily": "日报", "weekly": "周报", "monthly": "月报", "yearly": "年报"}
PERIOD_NAMES = {"sharp": "尖峰", "peak": "高峰", "flat": "平段", "valley": "低谷"}


def _dt(d: date) -> datetime:
    return datetime.combine(d, time.min).astimezone()


def _month_start(d: date) -> date:
    return d.replace(day=1)


def _add_months(d: date, n: int) -> date:
    y, m = d.year, d.month + n
    y += (m - 1) // 12
    m = (m - 1) % 12 + 1
    return date(y, m, 1)


def _derive_period(report_type: str, start: date | None, end: date | None) -> tuple[date, date]:
    """未显式指定时间范围时，按报表周期推导默认区间（含首尾）。"""
    today = date.today()
    if start and end:
        return start, end
    if report_type == "daily":
        return start or today, end or today
    if report_type == "weekly":
        s = today - timedelta(days=today.weekday())
        return start or s, end or s + timedelta(days=6)
    if report_type == "yearly":
        return start or date(today.year, 1, 1), end or date(today.year, 12, 31)
    return start or _month_start(today), end or (_add_months(_month_start(today), 1) - timedelta(days=1))


def _bounds(start: date, end: date) -> tuple[datetime, datetime]:
    """[start_dt, end_dt) 左闭右开。"""
    return _dt(start), _dt(end + timedelta(days=1))


# ==================== 模板 ====================


async def list_templates(session: AsyncSession, keyword: str | None = None) -> list[dict]:
    stmt = select(ReportTemplate).order_by(ReportTemplate.id)
    if keyword:
        stmt = stmt.where(ReportTemplate.template_name.like(f"%{keyword}%"))
    rows = (await session.execute(stmt)).scalars().all()
    return [r.model_dump() for r in rows]


async def create_template(session: AsyncSession, data: ReportTemplateUpsert) -> dict:
    exists = (
        await session.execute(
            select(ReportTemplate).where(ReportTemplate.template_code == data.template_code)
        )
    ).scalars().first()
    if exists:
        raise BizException("模板编码已存在")
    obj = ReportTemplate(**data.model_dump())
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return obj.model_dump()


async def update_template(session: AsyncSession, template_id: int, data: ReportTemplateUpsert) -> dict:
    obj = await session.get(ReportTemplate, template_id)
    if not obj:
        raise BizException("模板不存在")
    for k, v in data.model_dump().items():
        setattr(obj, k, v)
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return obj.model_dump()


async def delete_template(session: AsyncSession, template_id: int) -> None:
    obj = await session.get(ReportTemplate, template_id)
    if not obj:
        raise BizException("模板不存在")
    used = (
        await session.execute(
            select(func.count(ReportRecord.id)).where(ReportRecord.template_id == template_id)
        )
    ).scalar_one()
    if used:
        raise BizException("该模板已生成报表记录，无法删除")
    await session.delete(obj)
    await session.commit()


# ==================== 报表内容聚合 ====================


async def _energy_by_type(session: AsyncSession, start: date, end: date) -> list[dict]:
    s, e = _bounds(start, end)
    rows = (
        await session.execute(
            select(
                CfgEnergyType.type_name,
                func.coalesce(func.sum(EnergyStat.stat_value), 0),
                func.max(EnergyStat.unit),
            )
            .join(CfgEnergyType, CfgEnergyType.id == EnergyStat.energy_type_id)
            .where(
                EnergyStat.stat_type == "day",
                EnergyStat.device_id.is_(None),
                EnergyStat.stat_time >= s,
                EnergyStat.stat_time < e,
            )
            .group_by(CfgEnergyType.type_name)
        )
    ).all()
    return [
        {"name": r[0], "value": round(float(r[1] or 0), 2), "unit": r[2] or ""} for r in rows
    ]


async def _dimension_rows(session: AsyncSession, start: date, end: date, dimension: str) -> list[dict]:
    """按区域/分项/设备汇总电力用量。"""
    s, e = _bounds(start, end)
    ele = (
        await session.execute(select(CfgEnergyType).where(CfgEnergyType.type_code == "electricity"))
    ).scalars().first()
    ele_id = ele.id if ele else None

    if dimension == "item":
        stmt = (
            select(CfgEnergyItem.item_name, func.coalesce(func.sum(EnergyStat.stat_value), 0))
            .join(CfgEnergyItem, CfgEnergyItem.id == EnergyStat.energy_item_id)
            .where(
                EnergyStat.stat_type == "day",
                EnergyStat.device_id.is_(None),
                EnergyStat.energy_item_id.is_not(None),
                EnergyStat.stat_time >= s,
                EnergyStat.stat_time < e,
            )
            .group_by(CfgEnergyItem.item_name)
        )
    else:  # area / device 均以区域聚合为主，device 走设备级统计
        if dimension == "device":
            stmt = (
                select(DevDevice.device_name, func.coalesce(func.sum(EnergyStat.stat_value), 0))
                .join(DevDevice, DevDevice.id == EnergyStat.device_id)
                .where(
                    EnergyStat.stat_type == "day",
                    EnergyStat.device_id.is_not(None),
                    EnergyStat.stat_time >= s,
                    EnergyStat.stat_time < e,
                )
                .group_by(DevDevice.device_name)
            )
        else:
            stmt = (
                select(DevArea.area_name, func.coalesce(func.sum(EnergyStat.stat_value), 0))
                .join(DevArea, DevArea.id == EnergyStat.area_id)
                .where(
                    EnergyStat.stat_type == "day",
                    EnergyStat.device_id.is_(None),
                    EnergyStat.area_id.is_not(None),
                    EnergyStat.stat_time >= s,
                    EnergyStat.stat_time < e,
                )
                .group_by(DevArea.area_name)
            )
    if dimension != "device" and ele_id is not None:
        stmt = stmt.where(EnergyStat.energy_type_id == ele_id)

    stmt = stmt.order_by(func.sum(EnergyStat.stat_value).desc())
    rows = (await session.execute(stmt)).all()
    total = sum(float(r[1] or 0) for r in rows) or 1.0
    return [
        {"name": r[0], "value": round(float(r[1] or 0), 2), "ratio": round(float(r[1] or 0) / total * 100, 1)}
        for r in rows
    ]


async def _carbon_by_scope(session: AsyncSession, start: date, end: date) -> list[dict]:
    rows = (
        await session.execute(
            select(CarbonEmission.scope, func.coalesce(func.sum(CarbonEmission.emission_value), 0))
            .where(
                CarbonEmission.period_type == "month",
                CarbonEmission.area_id.is_(None),
                CarbonEmission.period_value >= f"{start:%Y-%m}",
                CarbonEmission.period_value <= f"{end:%Y-%m}",
            )
            .group_by(CarbonEmission.scope)
        )
    ).all()
    return [{"name": r[0] or "未分类", "value": round(float(r[1] or 0), 2)} for r in rows]


async def _fee_by_period(session: AsyncSession, start: date, end: date) -> list[dict]:
    s, e = _bounds(start, end)
    rows = (
        await session.execute(
            select(
                EnergyFeeStat.period_type,
                func.coalesce(func.sum(EnergyFeeStat.usage_value), 0),
                func.coalesce(func.sum(EnergyFeeStat.fee_value), 0),
            )
            .where(
                EnergyFeeStat.stat_type == "day",
                EnergyFeeStat.area_id.is_(None),
                EnergyFeeStat.energy_item_id.is_(None),
                EnergyFeeStat.stat_time >= s,
                EnergyFeeStat.stat_time < e,
            )
            .group_by(EnergyFeeStat.period_type)
        )
    ).all()
    order = {"sharp": 0, "peak": 1, "flat": 2, "valley": 3}
    data = [
        {
            "name": PERIOD_NAMES.get(r[0], r[0]),
            "usage": round(float(r[1] or 0), 2),
            "fee": round(float(r[2] or 0), 2),
        }
        for r in rows
    ]
    data.sort(key=lambda x: order.get(x["name"], 9))
    return data


async def build_content(
    session: AsyncSession, data_source: str, start: date, end: date, dimension: str = "area"
) -> dict:
    """聚合报表数据（能耗 / 碳排 / 费用）。"""
    energy = await _energy_by_type(session, start, end)
    carbon_rows = await _carbon_by_scope(session, start, end)
    total_energy = round(sum(x["value"] for x in energy), 2)
    total_carbon = round(sum(x["value"] for x in carbon_rows), 2)
    fee_rows = await _fee_by_period(session, start, end)
    total_fee = round(sum(x["fee"] for x in fee_rows), 2)
    detail = await _dimension_rows(session, start, end, dimension)

    return {
        "period": {"start": start.strftime("%Y-%m-%d"), "end": end.strftime("%Y-%m-%d")},
        "data_source": data_source,
        "dimension": dimension,
        "summary": {
            "total_energy": total_energy,
            "total_carbon": total_carbon,
            "total_fee": total_fee,
        },
        "energy": energy,
        "carbon": carbon_rows,
        "fee": fee_rows,
        "detail": detail,
    }


# ==================== 生成 ====================


async def generate(session: AsyncSession, payload: ReportGenerateRequest, operator_id: int) -> dict:
    template = None
    if payload.template_id:
        template = await session.get(ReportTemplate, payload.template_id)
        if not template:
            raise BizException("报表模板不存在")

    report_type = payload.report_type or (template.report_type if template else "monthly")
    data_source = (template.data_source if template else None) or "energy"
    start, end = _derive_period(report_type, payload.period_start, payload.period_end)
    if start > end:
        raise BizException("开始日期不能晚于结束日期")

    dimension = "area"
    content = await build_content(session, data_source, start, end, dimension)

    name = payload.report_name or (
        f"{template.template_name if template else REPORT_TYPE_NAMES.get(report_type, '报表')}"
        f"（{start:%Y-%m-%d}~{end:%Y-%m-%d}）"
    )
    ext = "pdf" if payload.file_type == "pdf" else "xlsx"
    record = ReportRecord(
        template_id=payload.template_id,
        report_name=name,
        period_start=start,
        period_end=end,
        file_type=payload.file_type or "excel",
        file_path=f"reports/{name}.{ext}",
        gen_status="success",
        operator_id=operator_id,
    )
    session.add(record)
    await session.commit()
    await session.refresh(record)
    result = record.model_dump()
    result["content"] = content
    return result


async def custom(session: AsyncSession, payload: ReportCustomRequest, operator_id: int) -> dict:
    start, end = _derive_period("monthly", payload.period_start, payload.period_end)
    if start > end:
        raise BizException("开始日期不能晚于结束日期")
    content = await build_content(session, payload.data_source, start, end, payload.dimension)
    record = ReportRecord(
        template_id=None,
        report_name=payload.report_name,
        period_start=start,
        period_end=end,
        file_type="excel",
        file_path=f"reports/{payload.report_name}.xlsx",
        gen_status="success",
        operator_id=operator_id,
    )
    session.add(record)
    await session.commit()
    await session.refresh(record)
    result = record.model_dump()
    result["content"] = content
    return result


# ==================== 记录 ====================


async def page_records(
    session: AsyncSession,
    page: int,
    page_size: int,
    report_name: str | None = None,
    report_type: str | None = None,
) -> tuple[int, list[dict]]:
    conds = []
    if report_name:
        conds.append(ReportRecord.report_name.like(f"%{report_name}%"))
    if report_type:
        # 报表类型来自模板；自定义报表（无模板）归为 custom
        if report_type == "custom":
            conds.append(ReportRecord.template_id.is_(None))
        else:
            conds.append(
                ReportRecord.template_id.in_(
                    select(ReportTemplate.id).where(ReportTemplate.report_type == report_type)
                )
            )
    stmt = (
        select(ReportRecord, ReportTemplate.template_name)
        .join(ReportTemplate, ReportTemplate.id == ReportRecord.template_id, isouter=True)
        .where(*conds)
        .order_by(ReportRecord.gen_time.desc(), ReportRecord.id.desc())
    )
    total = (
        await session.execute(select(func.count()).select_from(stmt.order_by(None).subquery()))
    ).scalar_one()
    rows = (
        await session.execute(stmt.offset((page - 1) * page_size).limit(page_size))
    ).all()

    type_map = {t.id: t.report_type for t in (await session.execute(select(ReportTemplate))).scalars().all()}
    items = []
    for record, template_name in rows:
        item = record.model_dump()
        item["template_name"] = template_name or "自定义报表"
        item["report_type"] = type_map.get(record.template_id) or "custom"
        items.append(item)
    return total, items


async def export_record(session: AsyncSession, record_id: int, file_type: str) -> tuple[bytes, str]:
    record = await session.get(ReportRecord, record_id)
    if not record:
        raise BizException("报表记录不存在")
    start = record.period_start or _month_start(date.today())
    end = record.period_end or date.today()
    content = await build_content(session, "energy", start, end, "area")
    if file_type == "pdf":
        return _to_pdf(record.report_name, content), f"{record.report_name}.pdf"
    return _to_excel(record.report_name, content), f"{record.report_name}.xlsx"


def _to_excel(name: str, content: dict) -> bytes:
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "汇总"
    period = content["period"]
    ws.append([f"{name}"])
    ws.append(["统计区间", f"{period['start']} ~ {period['end']}"])
    ws.append([])
    summary = content["summary"]
    ws.append(["指标", "数值"])
    ws.append(["总能耗", summary["total_energy"]])
    ws.append(["总碳排(tCO2e)", summary["total_carbon"]])
    ws.append(["总费用(元)", summary["total_fee"]])

    ws2 = wb.create_sheet("能耗构成")
    ws2.append(["能源类型", "用量", "单位"])
    for r in content["energy"]:
        ws2.append([r["name"], r["value"], r["unit"]])

    ws3 = wb.create_sheet("维度明细")
    ws3.append(["名称", "用电量(kWh)", "占比(%)"])
    for r in content["detail"]:
        ws3.append([r["name"], r["value"], r["ratio"]])

    ws4 = wb.create_sheet("碳排构成")
    ws4.append(["排放范围", "碳排量(tCO2e)"])
    for r in content["carbon"]:
        ws4.append([r["name"], r["value"]])

    ws5 = wb.create_sheet("分时费用")
    ws5.append(["时段", "用电量(kWh)", "费用(元)"])
    for r in content["fee"]:
        ws5.append([r["name"], r["usage"], r["fee"]])

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _to_pdf(name: str, content: dict) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
    title_style = ParagraphStyle("title", fontName="STSong-Light", fontSize=16, leading=22, alignment=1)
    sub_style = ParagraphStyle("sub", fontName="STSong-Light", fontSize=10, leading=14)

    period = content["period"]
    summary = content["summary"]

    def _table(header: list[str], rows: list[list]) -> Table:
        data = [header] + rows
        t = Table(data, colWidths=[70 * mm, 45 * mm, 45 * mm])
        t.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, -1), "STSong-Light"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E6FFF")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                ]
            )
        )
        return t

    story = [
        Paragraph(name, title_style),
        Paragraph(f"统计区间：{period['start']} ~ {period['end']}", sub_style),
        Spacer(1, 6 * mm),
        Paragraph(
            f"总能耗：{summary['total_energy']}　总碳排：{summary['total_carbon']} tCO2e　总费用：{summary['total_fee']} 元",
            sub_style,
        ),
        Spacer(1, 4 * mm),
        Paragraph("一、能耗构成", sub_style),
        _table(["能源类型", "用量", "单位"], [[r["name"], r["value"], r["unit"]] for r in content["energy"]]),
        Spacer(1, 4 * mm),
        Paragraph("二、区域/维度明细", sub_style),
        _table(["名称", "用电量(kWh)", "占比(%)"], [[r["name"], r["value"], r["ratio"]] for r in content["detail"]]),
        Spacer(1, 4 * mm),
        Paragraph("三、碳排构成", sub_style),
        _table(["排放范围", "碳排量(tCO2e)", ""], [[r["name"], r["value"], ""] for r in content["carbon"]]),
        Spacer(1, 4 * mm),
        Paragraph("四、分时费用", sub_style),
        _table(["时段", "用电量(kWh)", "费用(元)"], [[r["name"], r["usage"], r["fee"]] for r in content["fee"]]),
    ]
    buf = io.BytesIO()
    SimpleDocTemplate(buf, pagesize=A4).build(story)
    return buf.getvalue()


# ==================== 订阅 ====================


async def page_subscriptions(session: AsyncSession, page: int, page_size: int) -> tuple[int, list[dict]]:
    stmt = select(ReportSubscribe, ReportTemplate.template_name).join(
        ReportTemplate, ReportTemplate.id == ReportSubscribe.template_id, isouter=True
    ).order_by(ReportSubscribe.id.desc())
    total = (
        await session.execute(select(func.count()).select_from(stmt.order_by(None).subquery()))
    ).scalar_one()
    rows = (await session.execute(stmt.offset((page - 1) * page_size).limit(page_size))).all()
    items = []
    for sub, template_name in rows:
        item = sub.model_dump()
        item["template_name"] = template_name or "-"
        items.append(item)
    return total, items


async def create_subscription(session: AsyncSession, data: ReportSubscribeUpsert) -> dict:
    obj = ReportSubscribe(**data.model_dump())
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return obj.model_dump()


async def update_subscription(session: AsyncSession, sub_id: int, data: ReportSubscribeUpsert) -> dict:
    obj = await session.get(ReportSubscribe, sub_id)
    if not obj:
        raise BizException("订阅不存在")
    for k, v in data.model_dump().items():
        setattr(obj, k, v)
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return obj.model_dump()


async def delete_subscription(session: AsyncSession, sub_id: int) -> None:
    obj = await session.get(ReportSubscribe, sub_id)
    if not obj:
        raise BizException("订阅不存在")
    await session.delete(obj)
    await session.commit()


async def run_subscription(session: AsyncSession, sub_id: int, operator_id: int) -> dict:
    """立即执行订阅：生成报表记录并推送站内消息（模拟）。"""
    obj = await session.get(ReportSubscribe, sub_id)
    if not obj:
        raise BizException("订阅不存在")
    template = await session.get(ReportTemplate, obj.template_id) if obj.template_id else None
    report_type = (template.report_type if template else None) or "monthly"
    start, end = _derive_period(report_type, None, None)
    name = f"{obj.subscribe_name}（{start:%Y-%m-%d}~{end:%Y-%m-%d}）"
    content = await build_content(session, (template.data_source if template else None) or "energy", start, end)

    record = ReportRecord(
        template_id=obj.template_id,
        report_name=name,
        period_start=start,
        period_end=end,
        file_type="excel",
        file_path=f"reports/{name}.xlsx",
        gen_status="success",
        operator_id=operator_id,
    )
    session.add(record)

    # 推送：按接收人写站内消息，按渠道写发送记录
    now = datetime.now().astimezone()
    receiver_ids = [int(x) for x in (obj.receivers or "").replace("，", ",").split(",") if x.strip().isdigit()]
    channel_ids = [int(x) for x in (obj.channel_ids or "").replace("，", ",").split(",") if x.strip().isdigit()]
    # 过滤掉数据库中已不存在的用户/渠道，避免外键约束报错
    if receiver_ids:
        valid_users = set(
            (await session.execute(select(SysUser.id).where(SysUser.id.in_(receiver_ids)))).scalars().all()
        )
        receiver_ids = [r for r in receiver_ids if r in valid_users]
    if channel_ids:
        valid_channels = set(
            (await session.execute(select(NotifyChannel.id).where(NotifyChannel.id.in_(channel_ids)))).scalars().all()
        )
        channel_ids = [c for c in channel_ids if c in valid_channels]
    title = f"【报表订阅】{obj.subscribe_name}"
    text = f"{name} 已生成：总能耗 {content['summary']['total_energy']}，总费用 {content['summary']['total_fee']} 元。"
    for rid in receiver_ids:
        session.add(
            NotifyMessage(
                title=title, content=text, msg_type="internal", level="info", receiver_id=rid, send_time=now
            )
        )
    for cid in channel_ids:
        session.add(
            NotifySendLog(
                channel_id=cid,
                receiver=",".join(str(r) for r in receiver_ids),
                title=title,
                content=text,
                send_status="success",
                send_time=now,
            )
        )
    obj.last_send_time = now
    session.add(obj)
    await session.commit()

    return {
        "record_id": record.id,
        "report_name": name,
        "receiver_count": len(receiver_ids),
        "channel_count": len(channel_ids),
    }
