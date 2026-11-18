"""节能定额域模型（quota，3 张表）。"""

from datetime import datetime
from decimal import Decimal

from sqlmodel import Field

from app.models.base import IdModel


class EnergyQuota(IdModel, table=True):
    __tablename__ = "energy_quota"

    quota_name: str = Field(max_length=64)
    quota_type: str | None = Field(default=None, max_length=32)  # area / device / item
    target_id: int | None = None
    energy_type_id: int | None = Field(default=None, foreign_key="cfg_energy_type.id")
    period_type: str | None = Field(default=None, max_length=32)
    period_value: str | None = Field(default=None, max_length=32)
    quota_value: Decimal | None = Field(default=None, max_digits=18, decimal_places=4)
    unit: str | None = Field(default=None, max_length=32)
    parent_id: int | None = Field(default=None, foreign_key="energy_quota.id")
    operator_id: int | None = Field(default=None, foreign_key="sys_user.id")
    created_at: datetime | None = Field(default_factory=lambda: datetime.now().astimezone())


class QuotaMonitor(IdModel, table=True):
    __tablename__ = "quota_monitor"

    quota_id: int | None = Field(default=None, foreign_key="energy_quota.id")
    period_value: str | None = Field(default=None, max_length=32)
    actual_value: Decimal | None = Field(default=None, max_digits=18, decimal_places=4)
    complete_rate: Decimal | None = Field(default=None, max_digits=10, decimal_places=4)
    deviation: Decimal | None = Field(default=None, max_digits=10, decimal_places=4)
    warn_status: str | None = Field(default=None, max_length=32)
    stat_time: datetime | None = Field(default_factory=lambda: datetime.now().astimezone())


class QuotaAssess(IdModel, table=True):
    __tablename__ = "quota_assess"

    assess_name: str = Field(max_length=64)
    target_id: int | None = None
    target_name: str | None = Field(default=None, max_length=64)
    period_value: str | None = Field(default=None, max_length=32)
    quota_value: Decimal | None = Field(default=None, max_digits=18, decimal_places=4)
    actual_value: Decimal | None = Field(default=None, max_digits=18, decimal_places=4)
    score: Decimal | None = Field(default=None, max_digits=10, decimal_places=2)
    grade: str | None = Field(default=None, max_length=32)
    assess_result: str | None = Field(default=None, max_length=64)
    assess_time: datetime | None = Field(default_factory=lambda: datetime.now().astimezone())
    operator_id: int | None = Field(default=None, foreign_key="sys_user.id")
    created_at: datetime | None = Field(default_factory=lambda: datetime.now().astimezone())
