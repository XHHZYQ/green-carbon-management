"""控制域模型（ctrl，2 张表）。"""

from datetime import datetime

from sqlmodel import Field

from app.models.base import IdModel


class CtrlCommand(IdModel, table=True):
    __tablename__ = "ctrl_command"

    command_no: str = Field(max_length=64)
    device_id: int | None = Field(default=None, foreign_key="dev_device.id")
    point_key: str | None = Field(default=None, max_length=64)
    target_value: str | None = Field(default=None, max_length=64)
    priority: str = Field(default="normal", max_length=32)
    exec_mode: str = Field(default="immediate", max_length=32)
    schedule_time: datetime | None = None
    timeout_sec: int = Field(default=10)
    need_confirm: bool = Field(default=False)
    source: str | None = Field(default=None, max_length=32)
    status: str = Field(default="pending", max_length=32)
    fail_reason: str | None = Field(default=None, max_length=255)
    operator_id: int | None = Field(default=None, foreign_key="sys_user.id")
    send_time: datetime | None = None
    finish_time: datetime | None = None
    created_at: datetime | None = Field(default_factory=lambda: datetime.now().astimezone())


class CtrlTimedTask(IdModel, table=True):
    __tablename__ = "ctrl_timed_task"

    task_name: str = Field(max_length=64)
    device_id: int | None = Field(default=None, foreign_key="dev_device.id")
    point_key: str | None = Field(default=None, max_length=64)
    target_value: str | None = Field(default=None, max_length=64)
    cron_expr: str | None = Field(default=None, max_length=64)
    repeat_desc: str | None = Field(default=None, max_length=128)
    enable_status: int = Field(default=1)
    last_run_time: datetime | None = None
    next_run_time: datetime | None = None
    operator_id: int | None = Field(default=None, foreign_key="sys_user.id")
    created_at: datetime | None = Field(default_factory=lambda: datetime.now().astimezone())
