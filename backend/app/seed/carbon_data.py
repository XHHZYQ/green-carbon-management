"""碳排放域示例数据（B5-3）：执行碳核算 + 生成若干碳报告。"""

from datetime import date

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.carbon import CarbonEmission, CarbonReport
from app.models.sys import SysUser
from app.services import carbon_service as svc


async def seed_carbon_domain(session: AsyncSession) -> dict[str, int]:
    await session.execute(delete(CarbonReport))
    await session.execute(delete(CarbonEmission))
    await session.commit()

    # 依据能耗统计 × 碳因子核算近 12 个月碳排放（先清后建）
    calc_result = await svc.calc(session, "month")

    admin = (await session.execute(select(SysUser).where(SysUser.username == "admin"))).scalars().first()
    operator_id = admin.id if admin else None

    today = date.today()
    year = today.year
    last_month_start = date(year if today.month > 1 else year - 1, today.month - 1 if today.month > 1 else 12, 1)
    q = (today.month - 1) // 3  # 已完成的上一个季度序号
    q_end_month = q * 3
    q_start_month = q_end_month - 2
    q_year = year if q_end_month >= 1 else year - 1

    report_defs = [
        (f"{year}年度园区碳排放核算报告", "yearly", date(year, 1, 1), date(year, 12, 31)),
        (f"{q_year}年第{(q_start_month + 2) // 3}季度碳排放报告", "monthly", date(q_year, q_start_month, 1),
         date(q_year, q_end_month, 28)),
        (f"{last_month_start.year}年{last_month_start.month}月碳排放报告", "monthly",
         last_month_start, last_month_start.replace(day=28)),
    ]

    report_count = 0
    for name, rtype, start, end in report_defs:
        try:
            result = await svc.create_report(session, {
                "report_name": name, "report_type": rtype,
                "period_start": start, "period_end": end,
            })
            if not result.get("operator_id"):
                report = await session.get(CarbonReport, result["id"])
                if report:
                    report.operator_id = operator_id
            report_count += 1
        except Exception:  # noqa: BLE001 该周期无数据时跳过
            continue
    await session.commit()

    return {
        "碳排核算": calc_result["inserted"],
        "碳报告": report_count,
    }
