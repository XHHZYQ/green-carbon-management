"""统一响应体与分页封装。"""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


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
