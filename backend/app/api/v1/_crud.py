"""通用 CRUD 路由工厂：按模型自动生成列表/新增/编辑/删除接口。"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Sequence

from fastapi import APIRouter, Body, Depends, Request
from pydantic import ValidationError
from sqlalchemy import or_
from sqlmodel import SQLModel, select

from app.core.deps import SessionDep, require_perm
from app.core.exceptions import BizException
from app.core.pagination import PageDep, paginate_query
from app.core.response import paginate, success

# 只读列（前端提交时忽略）
READONLY_COLUMNS = {"id", "created_at"}


def _coerce(column, value: Any) -> Any:
    """按数据库列类型把入参转换为 Python 值。"""
    if value is None or value == "":
        return None
    try:
        py_type = column.type.python_type
    except (AttributeError, NotImplementedError):
        return value
    try:
        if py_type is datetime and isinstance(value, str):
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        if py_type is date and isinstance(value, str):
            return date.fromisoformat(value[:10])
        if py_type is Decimal:
            return Decimal(str(value))
        if py_type is int:
            return int(value)
        if py_type is float:
            return float(value)
        if py_type is bool:
            return value if isinstance(value, bool) else str(value).lower() in ("1", "true", "yes")
    except (ValueError, TypeError):
        raise BizException(f"字段 [{column.name}] 的值格式不正确") from None
    return value


def _build_payload(model: type[SQLModel], payload: dict) -> dict:
    """过滤非法字段并按列类型转换。"""
    columns = model.__table__.columns
    data: dict[str, Any] = {}
    for key, value in payload.items():
        if key in columns and key not in READONLY_COLUMNS:
            data[key] = _coerce(columns[key], value)
    if not data:
        raise BizException("没有可保存的字段")
    return data


def crud_router(
    *,
    model: type[SQLModel],
    prefix: str,
    tag: str,
    read_perm: str,
    write_perm: str,
    order_by: str = "id",
    search_fields: Sequence[str] = (),
) -> APIRouter:
    """生成标准 CRUD 路由：GET(分页/过滤) / POST / PUT / DELETE。"""
    router = APIRouter(prefix=prefix, tags=[tag])
    columns = model.__table__.columns

    @router.get("", summary=f"{tag}列表", dependencies=[Depends(require_perm(read_perm))])
    async def list_items(session: SessionDep, params: PageDep, request: Request):
        stmt = select(model)
        for key, value in request.query_params.items():
            if key in ("page", "page_size", "keyword") or value == "" or key not in columns:
                continue
            stmt = stmt.where(columns[key] == _coerce(columns[key], value))
        keyword = request.query_params.get("keyword")
        if keyword and search_fields:
            conditions = [columns[f].ilike(f"%{keyword}%") for f in search_fields if f in columns]
            if conditions:
                stmt = stmt.where(or_(*conditions))
        order_column = columns[order_by] if order_by in columns else columns["id"]
        total, rows = await paginate_query(session, stmt.order_by(order_column), params)
        return success(paginate(total, rows))

    @router.post("", summary=f"新增{tag}", dependencies=[Depends(require_perm(write_perm))])
    async def create_item(session: SessionDep, payload: dict = Body(...)):
        try:
            obj = model(**_build_payload(model, payload))
        except ValidationError as exc:
            raise BizException(f"参数不合法：{exc.errors()[0].get('msg', '')}") from None
        session.add(obj)
        await session.commit()
        await session.refresh(obj)
        return success(obj, message="新增成功")

    @router.put("/{item_id}", summary=f"编辑{tag}", dependencies=[Depends(require_perm(write_perm))])
    async def update_item(item_id: int, session: SessionDep, payload: dict = Body(...)):
        obj = await session.get(model, item_id)
        if not obj:
            raise BizException("记录不存在")
        for key, value in _build_payload(model, payload).items():
            setattr(obj, key, value)
        if "updated_at" in columns:
            obj.updated_at = datetime.now().astimezone()
        session.add(obj)
        await session.commit()
        await session.refresh(obj)
        return success(obj, message="修改成功")

    @router.delete("/{item_id}", summary=f"删除{tag}", dependencies=[Depends(require_perm(write_perm))])
    async def delete_item(item_id: int, session: SessionDep):
        obj = await session.get(model, item_id)
        if not obj:
            raise BizException("记录不存在")
        await session.delete(obj)
        await session.commit()
        return success(message="删除成功")

    return router
