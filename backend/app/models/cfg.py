"""基础配置域模型（cfg，9 张表）。"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlmodel import Field

from app.models.base import IdModel, TimeModel, jsonb_field


class CfgDictType(IdModel, table=True):
    __tablename__ = "cfg_dict_type"

    type_code: str = Field(max_length=64, index=True)
    type_name: str = Field(max_length=64)
    remark: str | None = Field(default=None, max_length=255)
    status: int = Field(default=1)
    created_at: datetime | None = Field(default_factory=lambda: datetime.now().astimezone())


class CfgDictItem(IdModel, table=True):
    __tablename__ = "cfg_dict_item"

    type_id: int | None = Field(default=None, foreign_key="cfg_dict_type.id")
    item_label: str = Field(max_length=64)
    item_value: str = Field(max_length=64)
    sort_no: int = Field(default=0)
    status: int = Field(default=1)
    remark: str | None = Field(default=None, max_length=255)


class CfgEnergyType(IdModel, table=True):
    __tablename__ = "cfg_energy_type"

    type_code: str = Field(max_length=64)
    type_name: str = Field(max_length=64)
    unit: str | None = Field(default=None, max_length=32)
    sort_no: int = Field(default=0)
    status: int = Field(default=1)
    created_at: datetime | None = Field(default_factory=lambda: datetime.now().astimezone())


class CfgEnergyItem(IdModel, table=True):
    __tablename__ = "cfg_energy_item"

    item_code: str = Field(max_length=64)
    item_name: str = Field(max_length=64)
    parent_id: int | None = Field(default=None, foreign_key="cfg_energy_item.id")
    energy_type_id: int | None = Field(default=None, foreign_key="cfg_energy_type.id")
    sort_no: int = Field(default=0)
    status: int = Field(default=1)


class CfgCarbonFactor(IdModel, table=True):
    __tablename__ = "cfg_carbon_factor"

    energy_type_id: int | None = Field(default=None, foreign_key="cfg_energy_type.id")
    factor_name: str = Field(max_length=64)
    factor_value: Decimal | None = Field(default=None, max_digits=18, decimal_places=6)
    factor_unit: str | None = Field(default=None, max_length=64)
    scope: str | None = Field(default=None, max_length=32)  # 范围一/二/三
    effective_date: date | None = None
    expire_date: date | None = None
    status: int = Field(default=1)
    created_at: datetime | None = Field(default_factory=lambda: datetime.now().astimezone())


class CfgProtocol(IdModel, table=True):
    __tablename__ = "cfg_protocol"

    protocol_code: str = Field(max_length=64)
    protocol_name: str = Field(max_length=64)
    category: str | None = Field(default=None, max_length=32)
    description: str | None = Field(default=None, max_length=255)
    status: int = Field(default=1)


class CfgDeviceType(IdModel, table=True):
    __tablename__ = "cfg_device_type"

    type_code: str = Field(max_length=64)
    type_name: str = Field(max_length=64)
    category: str | None = Field(default=None, max_length=32)
    default_protocol_id: int | None = Field(default=None, foreign_key="cfg_protocol.id")
    icon: str | None = Field(default=None, max_length=64)
    sort_no: int = Field(default=0)
    status: int = Field(default=1)


class CfgProtocolParam(IdModel, table=True):
    __tablename__ = "cfg_protocol_param"

    protocol_id: int | None = Field(default=None, foreign_key="cfg_protocol.id")
    param_key: str = Field(max_length=64)
    param_label: str = Field(max_length=64)
    param_type: str = Field(default="text", max_length=32)
    required: bool = Field(default=False)
    default_value: str | None = Field(default=None, max_length=128)
    options: Any | None = Field(default=None, sa_column=jsonb_field())
    sort_no: int = Field(default=0)


class CfgSystemParam(IdModel, table=True):
    __tablename__ = "cfg_system_param"

    param_key: str = Field(max_length=64)
    param_value: str | None = Field(default=None, max_length=255)
    param_name: str = Field(max_length=64)
    param_group: str | None = Field(default=None, max_length=64)
    remark: str | None = Field(default=None, max_length=255)
    updated_at: datetime | None = Field(default_factory=lambda: datetime.now().astimezone())
