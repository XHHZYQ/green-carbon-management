"""系统管理请求/响应模型。"""

from sqlmodel import SQLModel


class UserCreate(SQLModel):
    username: str
    password: str
    real_name: str | None = None
    phone: str | None = None
    email: str | None = None
    dept_name: str | None = None
    status: int = 1
    role_ids: list[int] = []


class UserUpdate(SQLModel):
    real_name: str | None = None
    phone: str | None = None
    email: str | None = None
    dept_name: str | None = None
    status: int | None = None
    role_ids: list[int] | None = None


class StatusUpdate(SQLModel):
    status: int


class ResetPasswordRequest(SQLModel):
    password: str = "123456"


class RoleCreate(SQLModel):
    role_code: str
    role_name: str
    description: str | None = None
    sort_no: int = 0
    status: int = 1
    menu_ids: list[int] = []


class RoleUpdate(SQLModel):
    role_name: str | None = None
    description: str | None = None
    sort_no: int | None = None
    status: int | None = None
    menu_ids: list[int] | None = None


class RoleMenuSave(SQLModel):
    menu_ids: list[int] = []


class ProfileUpdate(SQLModel):
    real_name: str | None = None
    phone: str | None = None
    email: str | None = None
    dept_name: str | None = None
    avatar: str | None = None
