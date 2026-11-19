"""统一响应体、分页封装与 JSON 编码（统一时间格式）。"""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"


class ApiResponse(BaseModel, Generic[T]):
    """统一响应结构：{ code, message, data }。成功 code=0。"""

    code: int = 0
    message: str = "ok"
    data: T | None = None


def success(data: Any = None, message: str = "ok") -> dict:
    return {"code": 0, "message": message, "data": data}


def fail(code: int = 1, message: str = "操作失败", data: Any = None) -> dict:
    return {"code": code, "message": message, "data": data}


def paginate(total: int, items: list) -> dict:
    """分页响应体：{ total, items }。"""
    return {"total": total, "items": items}


def json_encode(obj: Any, **_: Any) -> Any:
    """递归编码为可 JSON 序列化的结构，统一时间格式为 YYYY-MM-dd hh:mm:ss。"""
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, BaseModel):
        return json_encode(obj.model_dump())
    if isinstance(obj, dict):
        return {k: json_encode(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [json_encode(v) for v in obj]
    if isinstance(obj, datetime):
        return obj.strftime(DATETIME_FORMAT)
    if isinstance(obj, date):
        return obj.strftime(DATE_FORMAT)
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, Enum):
        return obj.value
    return str(obj)
