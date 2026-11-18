"""认证业务逻辑。"""

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.deps import get_user_menus, get_user_perm_codes, get_user_roles
from app.core.exceptions import BizException
from app.core.security import create_access_token, hash_password, verify_password
from app.models.sys import SysLoginLog, SysMenu, SysUser


async def authenticate(session: AsyncSession, username: str, password: str, ip: str = "") -> SysUser:
    user = (await session.execute(select(SysUser).where(SysUser.username == username))).scalars().first()
    if not user:
        raise BizException("用户名或密码错误")
    if user.status != 1:
        raise BizException("账号已被停用，请联系管理员")
    if not verify_password(password, user.password_hash):
        session.add(SysLoginLog(user_id=user.id, username=username, ip=ip, status=0, msg="密码错误"))
        await session.commit()
        raise BizException("用户名或密码错误")

    user.last_login_time = datetime.now().astimezone()
    user.fail_count = 0
    session.add(user)
    session.add(SysLoginLog(user_id=user.id, username=username, ip=ip, status=1, msg="登录成功"))
    await session.commit()
    await session.refresh(user)
    return user


async def build_user_info(session: AsyncSession, user: SysUser) -> dict:
    roles = await get_user_roles(session, user.id)
    perms = await get_user_perm_codes(session, user.id)
    return {
        "id": user.id,
        "username": user.username,
        "real_name": user.real_name,
        "phone": user.phone,
        "email": user.email,
        "dept_name": user.dept_name,
        "avatar": user.avatar,
        "roles": [r.role_code for r in roles],
        "perms": sorted(perms),
    }


async def issue_token(user: SysUser) -> str:
    return create_access_token(user.id, extra={"username": user.username})


async def change_password(session: AsyncSession, user: SysUser, old_password: str, new_password: str) -> None:
    if not verify_password(old_password, user.password_hash):
        raise BizException("原密码不正确")
    if len(new_password) < 6:
        raise BizException("新密码长度不能少于 6 位")
    user.password_hash = hash_password(new_password)
    user.updated_at = datetime.now().astimezone()
    session.add(user)
    await session.commit()


async def build_menu_tree(session: AsyncSession, user: SysUser) -> list[dict]:
    """构建当前用户菜单树（仅目录与菜单，不含按钮）。"""
    menus: list[SysMenu] = await get_user_menus(session, user.id)
    nodes = {}
    for m in menus:
        if m.menu_type == "button":
            continue
        nodes[m.id] = {
            "id": m.id,
            "parent_id": m.parent_id,
            "menu_name": m.menu_name,
            "route_path": m.route_path,
            "component": m.component,
            "icon": m.icon,
            "perm_code": m.perm_code,
            "sort_no": m.sort_no,
            "visible": m.visible,
            "children": [],
        }
    roots: list[dict] = []
    for node in nodes.values():
        if node["parent_id"] and node["parent_id"] in nodes:
            nodes[node["parent_id"]]["children"].append(node)
        else:
            roots.append(node)

    def _sort(items: list[dict]) -> list[dict]:
        items.sort(key=lambda x: x["sort_no"])
        for it in items:
            _sort(it["children"])
        return items

    return _sort(roots)
