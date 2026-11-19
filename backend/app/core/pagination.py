"""分页查询工具。"""

from typing import Annotated, Any, Sequence

from fastapi import Depends, Query
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession


class PageParams:
    """通用分页参数依赖：?page=1&page_size=20。"""

    def __init__(
        self,
        page: int = Query(1, ge=1, description="页码，从 1 开始"),
        page_size: int = Query(20, ge=1, le=200, description="每页条数"),
    ):
        self.page = page
        self.page_size = page_size


PageDep = Annotated[PageParams, Depends()]


async def paginate_query(
    session: AsyncSession, stmt: Select, params: PageParams
) -> tuple[int, Sequence[Any]]:
    """对 select 语句执行分页，返回 (总数, 当前页数据)。"""
    count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    total = (await session.execute(count_stmt)).scalar_one()
    rows = (
        await session.execute(stmt.offset((params.page - 1) * params.page_size).limit(params.page_size))
    ).scalars().all()
    return total, rows
