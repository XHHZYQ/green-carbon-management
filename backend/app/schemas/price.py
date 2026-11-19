"""电价与费用域请求模型（B5-2）。"""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class PricePlanCreate(BaseModel):
    """电价方案新增。"""

    plan_code: str
    plan_name: str
    energy_type_id: int | None = None
    effective_date: date | None = None
    expire_date: date | None = None
    status: int = 1


class PricePlanUpdate(BaseModel):
    """电价方案编辑（字段可选）。"""

    plan_code: str | None = None
    plan_name: str | None = None
    energy_type_id: int | None = None
    effective_date: date | None = None
    expire_date: date | None = None
    status: int | None = None


class PricePeriodCreate(BaseModel):
    """时段划分新增。"""

    period_type: str
    start_time: str
    end_time: str
    day_type: str = "workday"
    price: Decimal = Decimal("0")
    sort_no: int = 0


class PricePeriodUpdate(BaseModel):
    """时段划分编辑（字段可选）。"""

    period_type: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    day_type: str | None = None
    price: Decimal | None = None
    sort_no: int | None = None
