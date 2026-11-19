"""认证与用户相关请求/响应模型。"""

from datetime import datetime

from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str
    captcha_key: str | None = None
    captcha_code: str | None = None


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserInfo"


class UserInfo(BaseModel):
    id: int
    username: str
    real_name: str | None = None
    phone: str | None = None
    email: str | None = None
    dept_name: str | None = None
    avatar: str | None = None
    roles: list[str] = []
    perms: list[str] = []


class CaptchaResponse(BaseModel):
    captcha_key: str = ""
    captcha_image: str = ""
    enabled: bool = True


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class MenuRoute(BaseModel):
    id: int
    parent_id: int | None = None
    menu_name: str
    route_path: str | None = None
    component: str | None = None
    icon: str | None = None
    perm_code: str | None = None
    sort_no: int = 0
    visible: bool = True
    children: list["MenuRoute"] = []


class ProfileUpdateRequest(BaseModel):
    real_name: str | None = None
    phone: str | None = None
    email: str | None = None
    avatar: str | None = None


LoginResponse.model_rebuild()
MenuRoute.model_rebuild()
