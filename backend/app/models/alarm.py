"""告警域模型（alarm，1 张表）+ 告警规则。"""

from datetime import datetime
from decimal import Decimal

from sqlmodel import Field

from app.models.base import IdModel


class AlarmRule(IdModel, table=True):
    __tablename__ = "alarm_rule"

    rule_name: str = Field(max_length=64)
    rule_type: str | None = Field(default=None, max_length=32)
    device_id: int | None = Field(default=None, foreign_key="dev_device.id")
    device_type_id: int | None = Field(default=None, foreign_key="cfg_device_type.id")
    point_id: int | None = Field(default=None, foreign_key="dev_point.id")
    operator: str | None = Field(default=None, max_length=16)  # gt / lt / eq / range
    threshold: Decimal | None = Field(default=None, max_digits=18, decimal_places=4)
    duration_sec: int = Field(default=0)
    alarm_level: str | None = Field(default=None, max_length=32)
    notify_rule_id: int | None = Field(default=None, foreign_key="notify_rule.id")
    enable_status: int = Field(default=1)
    created_at: datetime | None = Field(default_factory=lambda: datetime.now().astimezone())


class AlarmInfo(IdModel, table=True):
    __tablename__ = "alarm_info"

    alarm_no: str = Field(max_length=64)
    rule_id: int | None = Field(default=None, foreign_key="alarm_rule.id")
    device_id: int | None = Field(default=None, foreign_key="dev_device.id")
    point_id: int | None = Field(default=None, foreign_key="dev_point.id")
    alarm_type: str | None = Field(default=None, max_length=32)
    alarm_level: str | None = Field(default=None, max_length=32)
    alarm_value: Decimal | None = Field(default=None, max_digits=18, decimal_places=4)
    threshold: Decimal | None = Field(default=None, max_digits=18, decimal_places=4)
    content: str | None = Field(default=None, max_length=255)
    status: str = Field(default="pending", max_length=32)
    confirm_by: int | None = Field(default=None, foreign_key="sys_user.id")
    confirm_time: datetime | None = None
    alarm_time: datetime | None = Field(default_factory=lambda: datetime.now().astimezone())
    created_at: datetime | None = Field(default_factory=lambda: datetime.now().astimezone())
