"""实时监控域模型（mon，2 张表）。"""

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlmodel import Field

from app.models.base import IdModel, jsonb_field


class MonTopology(IdModel, table=True):
    __tablename__ = "mon_topology"

    topo_code: str = Field(max_length=64)
    topo_name: str = Field(max_length=64)
    topo_type: str | None = Field(default=None, max_length=32)  # topology / plan
    area_id: int | None = Field(default=None, foreign_key="dev_area.id")
    background: str | None = Field(default=None, max_length=255)
    remark: str | None = Field(default=None, max_length=255)
    status: int = Field(default=1)
    created_at: datetime | None = Field(default_factory=lambda: datetime.now().astimezone())


class MonTopologyNode(IdModel, table=True):
    __tablename__ = "mon_topology_node"

    topo_id: int | None = Field(default=None, foreign_key="mon_topology.id")
    node_key: str = Field(max_length=64)
    node_type: str | None = Field(default=None, max_length=32)
    device_id: int | None = Field(default=None, foreign_key="dev_device.id")
    point_id: int | None = Field(default=None, foreign_key="dev_point.id")
    pos_x: Decimal | None = Field(default=None, max_digits=18, decimal_places=4)
    pos_y: Decimal | None = Field(default=None, max_digits=18, decimal_places=4)
    width: Decimal | None = Field(default=None, max_digits=18, decimal_places=4)
    height: Decimal | None = Field(default=None, max_digits=18, decimal_places=4)
    style_json: Any | None = Field(default=None, sa_column=jsonb_field())
    link_json: Any | None = Field(default=None, sa_column=jsonb_field())
