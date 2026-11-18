"""依赖注入：数据库会话、当前用户、权限校验。"""

from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.exceptions import ForbiddenException, UnauthorizedException
from app.core.security import decode_access_token
from app.db.session import get_session
from app.models.sys import SysMenu, SysRole, SysRoleMenu, SysUser, SysUserRole

SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def get_current_user(
    session: SessionDep,
    authorization: Annotated[str | None, Header()] = None,
) -> SysUser:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise UnauthorizedException()
    token = authorization.split(" ", 1)[1].strip()
    try:
        payload = decode_access_token(token)
    except Exception:
        raise UnauthorizedException() from None

    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedException()

    user = await session.get(SysUser, int(user_id))
    if not user or user.status != 1:
        raise UnauthorizedException("账号不存在或已被停用")
    return user


CurrentUser = Annotated[SysUser, Depends(get_current_user)]


async def get_user_roles(session: AsyncSession, user_id: int) -> list[SysRole]:
    stmt = (
        select(SysRole)
        .join(SysUserRole, SysUserRole.role_id == SysRole.id)
        .where(SysUserRole.user_id == user_id, SysRole.status == 1)
    )
    return list((await session.execute(stmt)).scalars().all())


async def get_user_menus(session: AsyncSession, user_id: int) -> list[SysMenu]:
    """获取用户拥有的菜单（按角色汇总，去重，按 sort_no 排序）。"""
    role_ids = [r.id for r in await get_user_roles(session, user_id)]
    if not role_ids:
        return []
    stmt = (
        select(SysMenu)
        .join(SysRoleMenu, SysRoleMenu.menu_id == SysMenu.id)
        .where(SysRoleMenu.role_id.in_(role_ids), SysMenu.status == 1)
        .order_by(SysMenu.sort_no)
    )
    menus = list((await session.execute(stmt)).scalars().all())
    # 去重
    seen, result = set(), []
    for m in menus:
        if m.id not in seen:
            seen.add(m.id)
            result.append(m)
    return result


async def get_user_perm_codes(session: AsyncSession, user_id: int) -> set[str]:
    menus = await get_user_menus(session, user_id)
    return {m.perm_code for m in menus if m.perm_code}


def require_perm(perm_code: str):
    """接口权限校验依赖工厂。"""

    async def _checker(session: SessionDep, user: CurrentUser) -> SysUser:
        perms = await get_user_perm_codes(session, user.id)
        if perm_code not in perms and "*" not in perms:
            raise ForbiddenException(f"缺少权限：{perm_code}")
        return user

    return _checker
