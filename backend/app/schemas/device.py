"""设备域请求模型。"""

from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


class AreaCreate(BaseModel):
    area_code: str
    area_name: str
    area_type: str | None = None
    parent_id: int | None = None
    sort_no: int = 0
    status: int = 1


class AreaUpdate(BaseModel):
    area_code: str | None = None
    area_name: str | None = None
    area_type: str | None = None
    parent_id: int | None = None
    sort_no: int | None = None
    status: int | None = None


class DeviceCreate(BaseModel):
    device_code: str
    device_name: str
    device_type_id: int | None = None
    area_id: int | None = None
    protocol_id: int | None = None
    install_location: str | None = None
    remark: str | None = None
    # 通信参数键值对
    params: dict[str, Any] = Field(default_factory=dict)
    # 测点模板（可选）：选择后按模板生成测点
    point_template_id: int | None = None
    # 是否保存后直接上线
    enable_online: bool = True


class DeviceUpdate(BaseModel):
    device_name: str | None = None
    device_type_id: int | None = None
    area_id: int | None = None
    protocol_id: int | None = None
    install_location: str | None = None
    remark: str | None = None
    params: dict[str, Any] | None = None


class TestConnectionRequest(BaseModel):
    protocol_id: int | None = None
    device_type_id: int | None = None
    params: dict[str, Any] = Field(default_factory=dict)


class PointCreate(BaseModel):
    device_id: int | None = None
    point_code: str
    point_name: str
    data_type: str | None = None
    unit: str | None = None
    range_min: Decimal | None = None
    range_max: Decimal | None = None
    point_type: str | None = None
    sort_no: int = 0
    status: int = 1


class PointUpdate(BaseModel):
    device_id: int | None = None
    point_code: str | None = None
    point_name: str | None = None
    data_type: str | None = None
    unit: str | None = None
    range_min: Decimal | None = None
    range_max: Decimal | None = None
    point_type: str | None = None
    sort_no: int | None = None
    status: int | None = None


class CollectTaskCreate(BaseModel):
    device_id: int | None = None
    task_name: str
    collect_mode: str | None = None
    period_sec: int = 60
    range_desc: str | None = None
    enable_status: int = 1


class CollectTaskUpdate(BaseModel):
    device_id: int | None = None
    task_name: str | None = None
    collect_mode: str | None = None
    period_sec: int | None = None
    range_desc: str | None = None
    enable_status: int | None = None


class DataPatchRequest(BaseModel):
    data_id: int
    patch_value: Decimal
    reason: str | None = None


class DataQualityRequest(BaseModel):
    data_quality: str
