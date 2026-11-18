"""工单域模型（wo，1 张表）。"""

from datetime import datetime

from sqlmodel import Field

from app.models.base import IdModel


class WoWorkOrder(IdModel, table=True):
    __tablename__ = "wo_work_order"

    order_no: str = Field(max_length=64)
    title: str = Field(max_length=128)
    type: str | None = Field(default=None, max_length=32)
    source: str | None = Field(default=None, max_length=32)  # alarm / manual
    alarm_id: int | None = Field(default=None, foreign_key="alarm_info.id")
    device_id: int | None = Field(default=None, foreign_key="dev_device.id")
    level: str | None = Field(default=None, max_length=32)
    status: str = Field(default="pending", max_length=32)
    assignee_id: int | None = Field(default=None, foreign_key="sys_user.id")
    creator_id: int | None = Field(default=None, foreign_key="sys_user.id")
    content: str | None = None
    handle_result: str | None = None
    create_time: datetime | None = Field(default_factory=lambda: datetime.now().astimezone())
    finish_time: datetime | None = None
    created_at: datetime | None = Field(default_factory=lambda: datetime.now().astimezone())
