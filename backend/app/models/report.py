"""报表域模型（report，3 张表）。"""

from datetime import date, datetime
from typing import Any

from sqlmodel import Field

from app.models.base import IdModel, jsonb_field


class ReportTemplate(IdModel, table=True):
    __tablename__ = "report_template"

    template_code: str = Field(max_length=64)
    template_name: str = Field(max_length=64)
    report_type: str | None = Field(default=None, max_length=32)
    data_source: str | None = Field(default=None, max_length=64)
    dimension_json: Any | None = Field(default=None, sa_column=jsonb_field())
    columns_json: Any | None = Field(default=None, sa_column=jsonb_field())
    status: int = Field(default=1)
    created_at: datetime | None = Field(default_factory=lambda: datetime.now().astimezone())


class ReportRecord(IdModel, table=True):
    __tablename__ = "report_record"

    template_id: int | None = Field(default=None, foreign_key="report_template.id")
    report_name: str = Field(max_length=128)
    period_start: date | None = None
    period_end: date | None = None
    file_type: str | None = Field(default=None, max_length=32)
    file_path: str | None = Field(default=None, max_length=255)
    gen_status: str | None = Field(default=None, max_length=32)
    gen_time: datetime | None = Field(default_factory=lambda: datetime.now().astimezone())
    operator_id: int | None = Field(default=None, foreign_key="sys_user.id")
    created_at: datetime | None = Field(default_factory=lambda: datetime.now().astimezone())


class ReportSubscribe(IdModel, table=True):
    __tablename__ = "report_subscribe"

    template_id: int | None = Field(default=None, foreign_key="report_template.id")
    subscribe_name: str = Field(max_length=64)
    cron_expr: str | None = Field(default=None, max_length=64)
    receivers: str | None = Field(default=None, max_length=255)
    channel_ids: str | None = Field(default=None, max_length=255)
    enable_status: int = Field(default=1)
    last_send_time: datetime | None = None
    created_at: datetime | None = Field(default_factory=lambda: datetime.now().astimezone())
