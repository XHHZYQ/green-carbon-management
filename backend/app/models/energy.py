"""能耗与费用域模型（energy，5 张表）。"""

from datetime import date, datetime
from decimal import Decimal

from sqlmodel import Field

from app.models.base import IdModel


class EnergyStat(IdModel, table=True):
    __tablename__ = "energy_stat"

    stat_type: str | None = Field(default=None, max_length=32)  # hour / day / month
    stat_time: datetime | None = None
    energy_type_id: int | None = Field(default=None, foreign_key="cfg_energy_type.id")
    energy_item_id: int | None = Field(default=None, foreign_key="cfg_energy_item.id")
    area_id: int | None = Field(default=None, foreign_key="dev_area.id")
    device_id: int | None = Field(default=None, foreign_key="dev_device.id")
    stat_value: Decimal | None = Field(default=None, max_digits=18, decimal_places=4)
    unit: str | None = Field(default=None, max_length=32)
    created_at: datetime | None = Field(default_factory=lambda: datetime.now().astimezone())


class EnergyPricePlan(IdModel, table=True):
    __tablename__ = "energy_price_plan"

    plan_code: str = Field(max_length=64)
    plan_name: str = Field(max_length=64)
    energy_type_id: int | None = Field(default=None, foreign_key="cfg_energy_type.id")
    effective_date: date | None = None
    expire_date: date | None = None
    status: int = Field(default=1)
    operator_id: int | None = Field(default=None, foreign_key="sys_user.id")
    created_at: datetime | None = Field(default_factory=lambda: datetime.now().astimezone())


class EnergyPricePeriod(IdModel, table=True):
    __tablename__ = "energy_price_period"

    plan_id: int | None = Field(default=None, foreign_key="energy_price_plan.id")
    period_type: str | None = Field(default=None, max_length=32)  # peak / flat / valley / sharp
    start_time: str | None = Field(default=None, max_length=16)
    end_time: str | None = Field(default=None, max_length=16)
    day_type: str | None = Field(default=None, max_length=32)  # workday / weekend / holiday
    price: Decimal | None = Field(default=None, max_digits=18, decimal_places=4)
    sort_no: int = Field(default=0)


class EnergyFeeStat(IdModel, table=True):
    __tablename__ = "energy_fee_stat"

    stat_type: str | None = Field(default=None, max_length=32)
    stat_time: datetime | None = None
    plan_id: int | None = Field(default=None, foreign_key="energy_price_plan.id")
    period_type: str | None = Field(default=None, max_length=32)
    area_id: int | None = Field(default=None, foreign_key="dev_area.id")
    energy_item_id: int | None = Field(default=None, foreign_key="cfg_energy_item.id")
    usage_value: Decimal | None = Field(default=None, max_digits=18, decimal_places=4)
    fee_value: Decimal | None = Field(default=None, max_digits=18, decimal_places=4)
    created_at: datetime | None = Field(default_factory=lambda: datetime.now().astimezone())


class EnergyPriceHistory(IdModel, table=True):
    __tablename__ = "energy_price_history"

    plan_id: int | None = Field(default=None, foreign_key="energy_price_plan.id")
    change_desc: str | None = Field(default=None, max_length=255)
    old_value: str | None = Field(default=None, max_length=64)
    new_value: str | None = Field(default=None, max_length=64)
    effective_date: date | None = None
    operator_id: int | None = Field(default=None, foreign_key="sys_user.id")
    changed_at: datetime | None = Field(default_factory=lambda: datetime.now().astimezone())
