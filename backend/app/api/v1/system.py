"""系统管理接口（/system/*）。"""

from fastapi import APIRouter, Depends, Query

from app.core.deps import CurrentUser, SessionDep, require_perm
from app.core.pagination import PageDep
from app.core.response import paginate, success
from app.schemas.system import (
    ProfileUpdate,
    ResetPasswordRequest,
    RoleCreate,
    RoleMenuSave,
    RoleUpdate,
    StatusUpdate,
    UserCreate,
    UserUpdate,
)
from app.services import auth_service, system_service

router = APIRouter(prefix="/system", tags=["系统管理"])


# ---------------------------------------------------------------- 用户管理

@router.get("/users", summary="用户列表", dependencies=[Depends(require_perm("system:user:view"))])
async def list_users(
    session: SessionDep,
    params: PageDep,
    keyword: str | None = Query(None, description="用户名/姓名"),
    status: int | None = Query(None),
):
    total, items = await system_service.page_users(session, params, keyword, status)
    return success(paginate(total, items))


@router.post("/users", summary="新增用户", dependencies=[Depends(require_perm("system:user:add"))])
async def create_user(session: SessionDep, payload: UserCreate):
    await system_service.create_user(session, payload)
    return success(message="新增成功")


@router.put("/users/{user_id}", summary="编辑用户", dependencies=[Depends(require_perm("system:user:edit"))])
async def update_user(user_id: int, session: SessionDep, payload: UserUpdate):
    await system_service.update_user(session, user_id, payload)
    return success(message="修改成功")


@router.delete("/users/{user_id}", summary="删除用户", dependencies=[Depends(require_perm("system:user:delete"))])
async def delete_user(user_id: int, session: SessionDep):
    await system_service.delete_user(session, user_id)
    return success(message="删除成功")


@router.put("/users/{user_id}/status", summary="启用/停用用户", dependencies=[Depends(require_perm("system:user:edit"))])
async def set_user_status(user_id: int, session: SessionDep, payload: StatusUpdate):
    await system_service.set_user_status(session, user_id, payload.status)
    return success(message="操作成功")


@router.put("/users/{user_id}/reset-password", summary="重置密码", dependencies=[Depends(require_perm("system:user:reset"))])
async def reset_password(user_id: int, session: SessionDep, payload: ResetPasswordRequest):
    await system_service.reset_user_password(session, user_id, payload.password)
    return success(message="密码已重置")


# ---------------------------------------------------------------- 角色管理

@router.get("/roles", summary="角色列表", dependencies=[Depends(require_perm("system:role:view"))])
async def list_roles(session: SessionDep, params: PageDep, keyword: str | None = Query(None)):
    total, items = await system_service.page_roles(session, params, keyword)
    return success(paginate(total, items))


@router.post("/roles", summary="新增角色", dependencies=[Depends(require_perm("system:role:add"))])
async def create_role(session: SessionDep, payload: RoleCreate):
    await system_service.create_role(session, payload)
    return success(message="新增成功")


@router.put("/roles/{role_id}", summary="编辑角色", dependencies=[Depends(require_perm("system:role:edit"))])
async def update_role(role_id: int, session: SessionDep, payload: RoleUpdate):
    await system_service.update_role(session, role_id, payload)
    return success(message="修改成功")


@router.delete("/roles/{role_id}", summary="删除角色", dependencies=[Depends(require_perm("system:role:delete"))])
async def delete_role(role_id: int, session: SessionDep):
    await system_service.delete_role(session, role_id)
    return success(message="删除成功")


# ---------------------------------------------------------------- 菜单权限

@router.get("/menus", summary="全部菜单（权限树）", dependencies=[Depends(require_perm("system:role:view"))])
async def list_menus(session: SessionDep):
    return success(await system_service.build_all_menu_tree(session))


@router.get("/roles/{role_id}/menus", summary="角色已分配菜单", dependencies=[Depends(require_perm("system:role:view"))])
async def get_role_menus(role_id: int, session: SessionDep):
    return success(await system_service.get_role_menu_ids(session, role_id))


@router.put("/roles/{role_id}/menus", summary="保存角色菜单权限", dependencies=[Depends(require_perm("system:role:edit"))])
async def save_role_menus(role_id: int, session: SessionDep, payload: RoleMenuSave):
    await system_service.save_role_menus(session, role_id, payload.menu_ids)
    return success(message="权限保存成功")


# ---------------------------------------------------------------- 日志

@router.get("/oper-logs", summary="操作日志", dependencies=[Depends(require_perm("system:log:view"))])
async def list_oper_logs(
    session: SessionDep,
    params: PageDep,
    keyword: str | None = Query(None),
    module: str | None = Query(None),
    status: int | None = Query(None),
):
    total, items = await system_service.page_oper_logs(session, params, keyword, module, status)
    return success(paginate(total, items))


@router.get("/login-logs", summary="登录日志", dependencies=[Depends(require_perm("system:log:view"))])
async def list_login_logs(
    session: SessionDep,
    params: PageDep,
    keyword: str | None = Query(None),
    status: int | None = Query(None),
):
    total, items = await system_service.page_login_logs(session, params, keyword, status)
    return success(paginate(total, items))


# ---------------------------------------------------------------- 个人中心

@router.get("/profile", summary="个人信息")
async def get_profile(user: CurrentUser, session: SessionDep):
    return success(await auth_service.build_user_info(session, user))


@router.put("/profile", summary="修改个人信息")
async def update_profile(payload: ProfileUpdate, user: CurrentUser, session: SessionDep):
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return success(await auth_service.build_user_info(session, user), message="资料更新成功")
