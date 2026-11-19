"""报表域请求模型（B7 报表中心）。"""

from datetime import date
from typing import Any

from pydantic import BaseModel, Field


class ReportTemplateUpsert(BaseModel):
    """报表模板新增/修改。"""

    template_code: str = Field(max_length=64)
    template_name: str = Field(max_length=128)
    report_type: str = Field(default="monthly", max_length=32)  # daily/monthly/yearly
    data_source: str = Field(default="energy", max_length=64)  # energy/carbon/fee/comprehensive
    dimension_json: Any | None = None
    columns_json: Any | None = None
    status: int = 1


class ReportGenerateRequest(BaseModel):
    """按模板生成报表。"""

    template_id: int | None = None
    report_name: str | None = None
    report_type: str = Field(default="monthly", max_length=32)
    period_start: date | None = None
    period_end: date | None = None
    file_type: str = Field(default="excel", max_length=16)  # excel/pdf


class ReportCustomRequest(BaseModel):
    """自定义报表：自选数据源、维度与时间范围。"""

    report_name: str = Field(max_length=128)
    data_source: str = Field(default="energy", max_length=64)  # energy/carbon/fee
    dimension: str = Field(default="area", max_length=32)  # area/item/device
    period_start: date | None = None
    period_end: date | None = None


class ReportSubscribeUpsert(BaseModel):
    """报表订阅新增/修改。"""

    template_id: int | None = None
    subscribe_name: str = Field(max_length=128)
    cron_expr: str | None = Field(default=None, max_length=64)
    receivers: str | None = None
    channel_ids: str | None = None
    enable_status: int = 1
