"""报表域示例数据（B7）。

覆盖：报表模板（report_template）、报表记录（report_record）、报表订阅（report_subscribe）。

用法：
    uv run python -m app.seed.run_seed
"""

from datetime import date, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notify import NotifyChannel
from app.models.report import ReportRecord, ReportSubscribe, ReportTemplate
from app.models.sys import SysUser
from app.schemas.report import ReportGenerateRequest
from app.services import report_service as report_svc

# 模板：(编码, 名称, 类型, 数据源, 维度, 列)
TEMPLATES = [
    ("TPL_ENERGY_DAILY", "能耗日报", "daily", "energy", ["area"], ["区域", "用电量", "费用"]),
    ("TPL_ENERGY_MONTHLY", "能耗月报", "monthly", "energy", ["area", "item"], ["区域", "分项", "用电量", "同比"]),
    ("TPL_CARBON_MONTHLY", "碳排月报", "monthly", "carbon", ["area"], ["范围", "碳排量", "环比"]),
    ("TPL_FEE_MONTHLY", "费用月报", "monthly", "fee", ["area"], ["时段", "用电量", "费用"]),
    ("TPL_COMPREHENSIVE_YEARLY", "综合年报", "yearly", "comprehensive", ["area"], ["指标", "数值", "同比"]),
]


def _add_months(d: date, n: int) -> date:
    y, m = d.year, d.month + n
    y += (m - 1) // 12
    m = (m - 1) % 12 + 1
    return date(y, m, 1)


async def seed_report_domain(session: AsyncSession) -> dict[str, int]:
    # 清空历史
    for model in (ReportRecord, ReportSubscribe, ReportTemplate):
        await session.execute(delete(model))
    await session.commit()

    # 模板
    templates: list[ReportTemplate] = []
    for code, name, rtype, source, dim, cols in TEMPLATES:
        obj = ReportTemplate(
            template_code=code,
            template_name=name,
            report_type=rtype,
            data_source=source,
            dimension_json=dim,
            columns_json=cols,
            status=1,
        )
        session.add(obj)
        templates.append(obj)
    await session.commit()
    for t in templates:
        await session.refresh(t)

    by_type = {t.report_type: t for t in templates}
    today = date.today()
    operator_id = 1

    # 报表记录：近 6 个月月报 + 近 5 天日报 + 1 份年报
    record_count = 0
    for i in range(5, -1, -1):
        m_start = _add_months(today.replace(day=1), -i)
        m_end = _add_months(m_start, 1) - timedelta(days=1)
        for tpl in templates:
            if tpl.report_type != "monthly":
                continue
            file_type = "pdf" if tpl.template_code == "TPL_CARBON_MONTHLY" else "excel"
            await report_svc.generate(
                session,
                ReportGenerateRequest(
                    template_id=tpl.id,
                    report_type="monthly",
                    period_start=m_start,
                    period_end=m_end,
                    file_type=file_type,
                ),
                operator_id,
            )
            record_count += 1

    for i in range(4, -1, -1):
        d = today - timedelta(days=i)
        await report_svc.generate(
            session,
            ReportGenerateRequest(
                template_id=by_type["daily"].id,
                report_type="daily",
                period_start=d,
                period_end=d,
                file_type="excel",
            ),
            operator_id,
        )
        record_count += 1

    await report_svc.generate(
        session,
        ReportGenerateRequest(
            template_id=by_type["yearly"].id,
            report_type="yearly",
            period_start=date(today.year, 1, 1),
            period_end=date(today.year, 12, 31),
            file_type="excel",
        ),
        operator_id,
    )
    record_count += 1

    # 订阅（接收人/渠道使用库中真实存在的 ID，避免外键约束失败）
    user_ids = list((await session.execute(select(SysUser.id).order_by(SysUser.id).limit(2))).scalars().all())
    channel_ids = list(
        (await session.execute(select(NotifyChannel.id).order_by(NotifyChannel.id).limit(2))).scalars().all()
    )
    receivers = ",".join(str(x) for x in user_ids)
    channels_a = ",".join(str(x) for x in channel_ids)
    channels_b = str(channel_ids[0]) if channel_ids else ""

    subs = [
        ReportSubscribe(
            template_id=by_type["monthly"].id,
            subscribe_name="能耗月报订阅",
            cron_expr="0 8 1 * *",
            receivers=receivers,
            channel_ids=channels_a,
            enable_status=1,
        ),
        ReportSubscribe(
            template_id=by_type["monthly"].id if by_type.get("monthly") else None,
            subscribe_name="碳排月报订阅",
            cron_expr="0 9 1 * *",
            receivers=receivers,
            channel_ids=channels_b,
            enable_status=1,
        ),
    ]
    # 碳排月报订阅指向碳排模板
    carbon_tpl = next((t for t in templates if t.template_code == "TPL_CARBON_MONTHLY"), None)
    if carbon_tpl:
        subs[1].template_id = carbon_tpl.id
    for s in subs:
        session.add(s)
    await session.commit()

    record_total = (await session.execute(select(func.count(ReportRecord.id)))).scalar_one()
    return {
        "report_template": len(templates),
        "report_record": int(record_total),
        "report_subscribe": len(subs),
    }
