"""碳排放域请求模型（B5-3）。"""

from datetime import date

from pydantic import BaseModel


class CarbonCalcRequest(BaseModel):
    """碳排放核算请求。"""

    period_type: str = "month"
    period_value: str | None = None  # 为空则核算最近 12 个月


class CarbonReportCreate(BaseModel):
    """碳报告生成请求。"""

    report_name: str
    report_type: str = "month"
    period_start: date
    period_end: date
