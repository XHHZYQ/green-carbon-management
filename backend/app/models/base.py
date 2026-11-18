"""SQLModel 公共基类与字段工具。"""

from datetime import datetime

from sqlalchemy import Column
from sqlmodel import Field, SQLModel


class IdModel(SQLModel):
    """统一主键：id 自增。"""

    id: int | None = Field(default=None, primary_key=True)


class TimeModel(IdModel):
    """带创建/更新时间的基类。"""

    created_at: datetime | None = Field(default_factory=lambda: datetime.now().astimezone())
    updated_at: datetime | None = Field(default_factory=lambda: datetime.now().astimezone())


def jsonb_field():
    """jsonb 列字段（PostgreSQL），每次调用返回独立 Column 实例。"""
    from sqlalchemy.dialects.postgresql import JSONB

    return Column(JSONB)
