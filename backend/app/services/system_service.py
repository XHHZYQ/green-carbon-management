"""系统管理业务逻辑（用户 / 角色 / 菜单权限 / 日志）。"""

from datetime import datetime

from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BizException
from app.core.pagination import PageParams, paginate_query
from app.core.security import hash_password
from app.models.sys import (
    SysLoginLog,
    SysMenu,
    SysOperLog,
    SysRole,
    SysRoleMenu,
    SysUser,
    SysUserRole,
)
from app.schemas.system import RoleCreate, RoleUpdate, UserCreate, UserUpdate


def _now() -> datetime:
    return datetime.now().astimezone()


# ---------------------------------------------------------------- 用户

async def _roles_of(session: AsyncSession, user_ids: list[int]) -> dict[int, list[SysRole]]:
    if not user_ids:
        return {}
    stmt = (
        select(SysUserRole.user_id, SysRole)
        .join(SysRole, SysRole.id == SysUserRole.role_id)
        .where(SysUserRole.user_id.in_(user_ids))
    )
    result: dict[int, list[SysRole]] = {}
    for user_id, role in (await session.execute(stmt)).all():
        result.setdefault(user_id, []).append(role)
    return result


def _user_dict(user: SysUser, roles: list[SysRole]) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "real_name": user.real_name,
        "phone": user.phone,
        "email": user.email,
        "dept_name": user.dept_name,
        "status": user.status,
        "avatar": user.avatar,
        "last_login_time": user.last_login_time,
        "created_at": user.created_at,
        "role_ids": [r.id for r in roles],
        "role_names": [r.role_name for r in roles],
    }


async def page_users(session: AsyncSession, params: PageParams, keyword: str | None, status: int | None):
    stmt = select(SysUser)
    if keyword:
        stmt = stmt.where(or_(SysUser.username.ilike(f"%{keyword}%"), SysUser.real_name.ilike(f"%{keyword}%")))
    if status is not None:
        stmt = stmt.where(SysUser.status == status)
    total, rows = await paginate_query(session, stmt.order_by(SysUser.id), params)
    role_map = await _roles_of(session, [u.id for u in rows])
    return total, [_user_dict(u, role_map.get(u.id, [])) for u in rows]


async def _save_user_roles(session: AsyncSession, user_id: int, role_ids: list[int]) -> None:
    await session.execute(delete(SysUserRole).where(SysUserRole.user_id == user_id))
    for role_id in set(role_ids):
        session.add(SysUserRole(user_id=user_id, role_id=role_id))


async def create_user(session: AsyncSession, payload: UserCreate) -> None:
    exists = (await session.execute(select(SysUser).where(SysUser.username == payload.username))).scalars().first()
    if exists:
        raise BizException("用户名已存在")
    user = SysUser(
        username=payload.username,
        password_hash=hash_password(payload.password),
        real_name=payload.real_name,
        phone=payload.phone,
        email=payload.email,
        dept_name=payload.dept_name,
        status=payload.status,
    )
    session.add(user)
    await session.flush()
    await _save_user_roles(session, user.id, payload.role_ids)
    await session.commit()


async def update_user(session: AsyncSession, user_id: int, payload: UserUpdate) -> None:
    user = await session.get(SysUser, user_id)
    if not user:
        raise BizException("用户不存在")
    for field in ("real_name", "phone", "email", "dept_name", "status"):
        value = getattr(payload, field)
        if value is not None:
            setattr(user, field, value)
    user.updated_at = _now()
    session.add(user)
    if payload.role_ids is not None:
        await _save_user_roles(session, user_id, payload.role_ids)
    await session.commit()


async def delete_user(session: AsyncSession, user_id: int) -> None:
    user = await session.get(SysUser, user_id)
    if not user:
        raise BizException("用户不存在")
    if user.username == "admin":
        raise BizException("内置管理员账号不可删除")
    await session.execute(delete(SysUserRole).where(SysUserRole.user_id == user_id))
    await session.delete(user)
    await session.commit()


async def set_user_status(session: AsyncSession, user_id: int, status: int) -> None:
    user = await session.get(SysUser, user_id)
    if not user:
        raise BizException("用户不存在")
    if user.username == "admin" and status != 1:
        raise BizException("内置管理员账号不可停用")
    user.status = status
    user.updated_at = _now()
    session.add(user)
    await session.commit()


async def reset_user_password(session: AsyncSession, user_id: int, password: str) -> None:
    user = await session.get(SysUser, user_id)
    if not user:
        raise BizException("用户不存在")
    if len(password) < 6:
        raise BizException("密码长度不能少于 6 位")
    user.password_hash = hash_password(password)
    user.updated_at = _now()
    session.add(user)
    await session.commit()


# ---------------------------------------------------------------- 角色

async def page_roles(session: AsyncSession, params: PageParams, keyword: str | None):
    stmt = select(SysRole)
    if keyword:
        stmt = stmt.where(or_(SysRole.role_code.ilike(f"%{keyword}%"), SysRole.role_name.ilike(f"%{keyword}%")))
    return await paginate_query(session, stmt.order_by(SysRole.sort_no, SysRole.id), params)


async def _save_role_menus(session: AsyncSession, role_id: int, menu_ids: list[int]) -> None:
    await session.execute(delete(SysRoleMenu).where(SysRoleMenu.role_id == role_id))
    for menu_id in set(menu_ids):
        session.add(SysRoleMenu(role_id=role_id, menu_id=menu_id))


async def create_role(session: AsyncSession, payload: RoleCreate) -> None:
    exists = (await session.execute(select(SysRole).where(SysRole.role_code == payload.role_code))).scalars().first()
    if exists:
        raise BizException("角色编码已存在")
    role = SysRole(
        role_code=payload.role_code,
        role_name=payload.role_name,
        description=payload.description,
        sort_no=payload.sort_no,
        status=payload.status,
    )
    session.add(role)
    await session.flush()
    await _save_role_menus(session, role.id, payload.menu_ids)
    await session.commit()


async def update_role(session: AsyncSession, role_id: int, payload: RoleUpdate) -> None:
    role = await session.get(SysRole, role_id)
    if not role:
        raise BizException("角色不存在")
    for field in ("role_name", "description", "sort_no", "status"):
        value = getattr(payload, field)
        if value is not None:
            setattr(role, field, value)
    role.updated_at = _now()
    session.add(role)
    if payload.menu_ids is not None:
        await _save_role_menus(session, role_id, payload.menu_ids)
    await session.commit()


async def delete_role(session: AsyncSession, role_id: int) -> None:
    role = await session.get(SysRole, role_id)
    if not role:
        raise BizException("角色不存在")
    if role.role_code == "admin":
        raise BizException("内置管理员角色不可删除")
    used = (await session.execute(select(func.count()).select_from(SysUserRole).where(SysUserRole.role_id == role_id))).scalar_one()
    if used:
        raise BizException("该角色下仍有用户，无法删除")
    await session.execute(delete(SysRoleMenu).where(SysRoleMenu.role_id == role_id))
    await session.delete(role)
    await session.commit()


async def get_role_menu_ids(session: AsyncSession, role_id: int) -> list[int]:
    rows = (await session.execute(select(SysRoleMenu.menu_id).where(SysRoleMenu.role_id == role_id))).scalars().all()
    return list(rows)


async def save_role_menus(session: AsyncSession, role_id: int, menu_ids: list[int]) -> None:
    role = await session.get(SysRole, role_id)
    if not role:
        raise BizException("角色不存在")
    await _save_role_menus(session, role_id, menu_ids)
    await session.commit()


# ---------------------------------------------------------------- 菜单

async def build_all_menu_tree(session: AsyncSession) -> list[dict]:
    menus = (await session.execute(select(SysMenu).order_by(SysMenu.sort_no, SysMenu.id))).scalars().all()
    nodes = {
        m.id: {
            "id": m.id,
            "parent_id": m.parent_id,
            "menu_name": m.menu_name,
            "menu_type": m.menu_type,
            "perm_code": m.perm_code,
            "children": [],
        }
        for m in menus
    }
    roots: list[dict] = []
    for node in nodes.values():
        parent = nodes.get(node["parent_id"]) if node["parent_id"] else None
        if parent:
            parent["children"].append(node)
        else:
            roots.append(node)
    return roots


# ---------------------------------------------------------------- 日志

async def page_oper_logs(session: AsyncSession, params: PageParams, keyword: str | None, module: str | None, status: int | None):
    stmt = select(SysOperLog)
    if keyword:
        stmt = stmt.where(or_(SysOperLog.username.ilike(f"%{keyword}%"), SysOperLog.request_url.ilike(f"%{keyword}%")))
    if module:
        stmt = stmt.where(SysOperLog.module == module)
    if status is not None:
        stmt = stmt.where(SysOperLog.status == status)
    return await paginate_query(session, stmt.order_by(SysOperLog.id.desc()), params)


async def page_login_logs(session: AsyncSession, params: PageParams, keyword: str | None, status: int | None):
    stmt = select(SysLoginLog)
    if keyword:
        stmt = stmt.where(SysLoginLog.username.ilike(f"%{keyword}%"))
    if status is not None:
        stmt = stmt.where(SysLoginLog.status == status)
    return await paginate_query(session, stmt.order_by(SysLoginLog.id.desc()), params)
