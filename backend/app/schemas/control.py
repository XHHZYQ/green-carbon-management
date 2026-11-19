"""控制域请求模型（B4-1 设备控制）。"""

from datetime import datetime

from pydantic import BaseModel, Field


class CommandCreate(BaseModel):
    """单设备控制下发。"""

    device_id: int
    point_key: str
    target_value: str
    priority: str = "normal"
    exec_mode: str = "immediate"
    schedule_time: datetime | None = None
    timeout_sec: int = 10
    need_confirm: bool = False
    source: str = "manual"


class BatchCommandItem(BaseModel):
    device_id: int
    point_key: str
    target_value: str


class BatchCommandCreate(BaseModel):
    """批量控制下发。"""

    items: list[BatchCommandItem] = Field(default_factory=list)
    priority: str = "normal"
    need_confirm: bool = True


class TimedTaskCreate(BaseModel):
    task_name: str
    device_id: int
    point_key: str
    target_value: str
    cron_expr: str
    repeat_desc: str | None = None
    enable_status: int = 1


class TimedTaskUpdate(BaseModel):
    task_name: str | None = None
    device_id: int | None = None
    point_key: str | None = None
    target_value: str | None = None
    cron_expr: str | None = None
    repeat_desc: str | None = None
    enable_status: int | None = None
