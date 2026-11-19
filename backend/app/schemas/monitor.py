"""实时监控域请求模型。"""

from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


class TopologyNodeIn(BaseModel):
    id: int | None = None
    node_key: str
    node_type: str | None = "device"
    device_id: int | None = None
    point_id: int | None = None
    pos_x: Decimal | None = None
    pos_y: Decimal | None = None
    width: Decimal | None = None
    height: Decimal | None = None
    style_json: dict[str, Any] | None = None
    link_json: dict[str, Any] | None = None


class TopologyCreate(BaseModel):
    topo_code: str
    topo_name: str
    topo_type: str = "topology"
    area_id: int | None = None
    background: str | None = None
    remark: str | None = None
    status: int = 1
    nodes: list[TopologyNodeIn] = Field(default_factory=list)


class TopologyUpdate(BaseModel):
    topo_name: str | None = None
    topo_type: str | None = None
    area_id: int | None = None
    background: str | None = None
    remark: str | None = None
    status: int | None = None
    nodes: list[TopologyNodeIn] | None = None
