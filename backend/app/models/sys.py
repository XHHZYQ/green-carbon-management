"""系统与权限域模型（sys，7 张表）。"""

from datetime import datetime

from sqlmodel import Field

from app.models.base import IdModel, TimeModel


class SysUser(TimeModel, table=True):
    __tablename__ = "sys_user"

    username: str = Field(max_length=64, index=True)
    password_hash: str = Field(max_length=255)
    real_name: str | None = Field(default=None, max_length=64)
    phone: str | None = Field(default=None, max_length=32)
    email: str | None = Field(default=None, max_length=128)
    dept_name: str | None = Field(default=None, max_length=128)
    status: int = Field(default=1)
    fail_count: int = Field(default=0)
    lock_until: datetime | None = None
    last_login_time: datetime | None = None
    avatar: str | None = Field(default=None, max_length=255)


class SysRole(TimeModel, table=True):
    __tablename__ = "sys_role"

    role_code: str = Field(max_length=64)
    role_name: str = Field(max_length=64)
    description: str | None = Field(default=None, max_length=255)
    status: int = Field(default=1)
    sort_no: int = Field(default=0)


class SysUserRole(IdModel, table=True):
    __tablename__ = "sys_user_role"

    user_id: int | None = Field(default=None, foreign_key="sys_user.id")
    role_id: int | None = Field(default=None, foreign_key="sys_role.id")
    created_at: datetime | None = Field(default_factory=lambda: datetime.now().astimezone())


class SysMenu(IdModel, table=True):
    __tablename__ = "sys_menu"

    parent_id: int | None = Field(default=None, foreign_key="sys_menu.id")
    menu_name: str = Field(max_length=64)
    menu_type: str = Field(default="menu", max_length=16)  # dir / menu / button
    route_path: str | None = Field(default=None, max_length=255)
    component: str | None = Field(default=None, max_length=255)
    icon: str | None = Field(default=None, max_length=64)
    perm_code: str | None = Field(default=None, max_length=128)
    sort_no: int = Field(default=0)
    visible: bool = Field(default=True)
    status: int = Field(default=1)
    created_at: datetime | None = Field(default_factory=lambda: datetime.now().astimezone())


class SysRoleMenu(IdModel, table=True):
    __tablename__ = "sys_role_menu"

    role_id: int | None = Field(default=None, foreign_key="sys_role.id")
    menu_id: int | None = Field(default=None, foreign_key="sys_menu.id")
    created_at: datetime | None = Field(default_factory=lambda: datetime.now().astimezone())


class SysOperLog(IdModel, table=True):
    __tablename__ = "sys_oper_log"

    user_id: int | None = Field(default=None, foreign_key="sys_user.id")
    username: str | None = Field(default=None, max_length=64)
    module: str | None = Field(default=None, max_length=64)
    action: str | None = Field(default=None, max_length=64)
    method: str | None = Field(default=None, max_length=16)
    request_url: str | None = Field(default=None, max_length=255)
    request_param: str | None = None
    ip: str | None = Field(default=None, max_length=64)
    status: int = Field(default=1)
    error_msg: str | None = None
    cost_ms: int = Field(default=0)
    oper_time: datetime | None = Field(default_factory=lambda: datetime.now().astimezone())


class SysLoginLog(IdModel, table=True):
    __tablename__ = "sys_login_log"

    user_id: int | None = Field(default=None, foreign_key="sys_user.id")
    username: str | None = Field(default=None, max_length=64)
    ip: str | None = Field(default=None, max_length=64)
    browser: str | None = Field(default=None, max_length=64)
    os: str | None = Field(default=None, max_length=64)
    status: int = Field(default=1)
    msg: str | None = Field(default=None, max_length=255)
    login_time: datetime | None = Field(default_factory=lambda: datetime.now().astimezone())
