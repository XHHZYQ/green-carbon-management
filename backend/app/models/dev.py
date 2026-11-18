"""设备域模型（dev，11 张表）。"""

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlmodel import Field

from app.models.base import IdModel, TimeModel, jsonb_field


class DevArea(IdModel, table=True):
    __tablename__ = "dev_area"

    parent_id: int | None = Field(default=None, foreign_key="dev_area.id")
    area_code: str = Field(max_length=64)
    area_name: str = Field(max_length=64)
    area_type: str | None = Field(default=None, max_length=32)
    sort_no: int = Field(default=0)
    status: int = Field(default=1)
    created_at: datetime | None = Field(default_factory=lambda: datetime.now().astimezone())


class DevDevice(TimeModel, table=True):
    __tablename__ = "dev_device"

    device_code: str = Field(max_length=64, index=True)
    device_name: str = Field(max_length=128)
    device_type_id: int | None = Field(default=None, foreign_key="cfg_device_type.id")
    area_id: int | None = Field(default=None, foreign_key="dev_area.id")
    protocol_id: int | None = Field(default=None, foreign_key="cfg_protocol.id")
    install_location: str | None = Field(default=None, max_length=128)
    status: str = Field(default="normal", max_length=32)
    online_status: str = Field(default="offline", max_length=32)
    access_time: datetime | None = None
    last_online_time: datetime | None = None
    remark: str | None = Field(default=None, max_length=255)


class DevDeviceConn(IdModel, table=True):
    __tablename__ = "dev_device_conn"

    device_id: int | None = Field(default=None, foreign_key="dev_device.id")
    param_key: str = Field(max_length=64)
    param_value: str | None = Field(default=None, max_length=255)
    updated_at: datetime | None = Field(default_factory=lambda: datetime.now().astimezone())


class DevPoint(IdModel, table=True):
    __tablename__ = "dev_point"

    device_id: int | None = Field(default=None, foreign_key="dev_device.id")
    point_code: str = Field(max_length=64)
    point_name: str = Field(max_length=64)
    data_type: str | None = Field(default=None, max_length=32)
    unit: str | None = Field(default=None, max_length=32)
    range_min: Decimal | None = Field(default=None, max_digits=18, decimal_places=4)
    range_max: Decimal | None = Field(default=None, max_digits=18, decimal_places=4)
    point_type: str | None = Field(default=None, max_length=32)
    sort_no: int = Field(default=0)
    status: int = Field(default=1)
    created_at: datetime | None = Field(default_factory=lambda: datetime.now().astimezone())


class DevPointTemplate(IdModel, table=True):
    __tablename__ = "dev_point_template"

    template_code: str = Field(max_length=64)
    template_name: str = Field(max_length=64)
    device_type_id: int | None = Field(default=None, foreign_key="cfg_device_type.id")
    description: str | None = Field(default=None, max_length=255)
    status: int = Field(default=1)
    created_at: datetime | None = Field(default_factory=lambda: datetime.now().astimezone())


class DevPointTemplateItem(IdModel, table=True):
    __tablename__ = "dev_point_template_item"

    template_id: int | None = Field(default=None, foreign_key="dev_point_template.id")
    point_code: str = Field(max_length=64)
    point_name: str = Field(max_length=64)
    data_type: str | None = Field(default=None, max_length=32)
    unit: str | None = Field(default=None, max_length=32)
    range_min: Decimal | None = Field(default=None, max_digits=18, decimal_places=4)
    range_max: Decimal | None = Field(default=None, max_digits=18, decimal_places=4)
    sort_no: int = Field(default=0)


class DevControlPoint(IdModel, table=True):
    __tablename__ = "dev_control_point"

    device_id: int | None = Field(default=None, foreign_key="dev_device.id")
    point_key: str = Field(max_length=64)
    point_name: str = Field(max_length=64)
    point_type: str | None = Field(default=None, max_length=32)  # enum / number
    value_min: Decimal | None = Field(default=None, max_digits=18, decimal_places=4)
    value_max: Decimal | None = Field(default=None, max_digits=18, decimal_places=4)
    enum_options: Any | None = Field(default=None, sa_column=jsonb_field())
    dangerous: bool = Field(default=False)
    sort_no: int = Field(default=0)
    status: int = Field(default=1)


class DevCollectTask(TimeModel, table=True):
    __tablename__ = "dev_collect_task"

    device_id: int | None = Field(default=None, foreign_key="dev_device.id")
    task_name: str = Field(max_length=64)
    collect_mode: str | None = Field(default=None, max_length=32)
    period_sec: int = Field(default=60)
    range_desc: str | None = Field(default=None, max_length=128)
    enable_status: int = Field(default=1)
    last_run_time: datetime | None = None


class DevData(IdModel, table=True):
    __tablename__ = "dev_data"

    device_id: int | None = Field(default=None, foreign_key="dev_device.id")
    point_id: int | None = Field(default=None, foreign_key="dev_point.id")
    collect_value: Decimal | None = Field(default=None, max_digits=18, decimal_places=4)
    unit: str | None = Field(default=None, max_length=32)
    data_quality: str = Field(default="normal", max_length=32)
    collect_time: datetime | None = Field(default_factory=lambda: datetime.now().astimezone())


class DevDataPatch(IdModel, table=True):
    __tablename__ = "dev_data_patch"

    data_id: int | None = Field(default=None, foreign_key="dev_data.id")
    patch_value: Decimal | None = Field(default=None, max_digits=18, decimal_places=4)
    reason: str | None = Field(default=None, max_length=255)
    operator_id: int | None = Field(default=None, foreign_key="sys_user.id")
    patched_at: datetime | None = Field(default_factory=lambda: datetime.now().astimezone())


class DevAccessLog(IdModel, table=True):
    __tablename__ = "dev_access_log"

    device_id: int | None = Field(default=None, foreign_key="dev_device.id")
    action: str | None = Field(default=None, max_length=64)
    result: str | None = Field(default=None, max_length=32)
    message: str | None = Field(default=None, max_length=255)
    operator_id: int | None = Field(default=None, foreign_key="sys_user.id")
    cost_ms: int = Field(default=0)
    access_time: datetime | None = Field(default_factory=lambda: datetime.now().astimezone())
