"""碳排放域模型（carbon，2 张表）。"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlmodel import Field

from app.models.base import IdModel, jsonb_field


class CarbonEmission(IdModel, table=True):
    __tablename__ = "carbon_emission"

    period_type: str | None = Field(default=None, max_length=32)
    period_value: str | None = Field(default=None, max_length=32)
    energy_type_id: int | None = Field(default=None, foreign_key="cfg_energy_type.id")
    area_id: int | None = Field(default=None, foreign_key="dev_area.id")
    scope: str | None = Field(default=None, max_length=32)
    energy_value: Decimal | None = Field(default=None, max_digits=18, decimal_places=4)
    factor_id: int | None = Field(default=None, foreign_key="cfg_carbon_factor.id")
    factor_value: Decimal | None = Field(default=None, max_digits=18, decimal_places=6)
    emission_value: Decimal | None = Field(default=None, max_digits=18, decimal_places=4)
    unit: str | None = Field(default=None, max_length=32)
    created_at: datetime | None = Field(default_factory=lambda: datetime.now().astimezone())


class CarbonReport(IdModel, table=True):
    __tablename__ = "carbon_report"

    report_no: str = Field(max_length=64)
    report_name: str = Field(max_length=128)
    report_type: str | None = Field(default=None, max_length=32)
    period_start: date | None = None
    period_end: date | None = None
    total_emission: Decimal | None = Field(default=None, max_digits=18, decimal_places=4)
    reduction_value: Decimal | None = Field(default=None, max_digits=18, decimal_places=4)
    reduction_rate: Decimal | None = Field(default=None, max_digits=10, decimal_places=4)
    content_json: Any | None = Field(default=None, sa_column=jsonb_field())
    file_path: str | None = Field(default=None, max_length=255)
    operator_id: int | None = Field(default=None, foreign_key="sys_user.id")
    created_at: datetime | None = Field(default_factory=lambda: datetime.now().astimezone())
