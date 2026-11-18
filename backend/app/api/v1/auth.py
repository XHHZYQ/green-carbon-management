"""认证接口。"""

from fastapi import APIRouter, Request

from app.core.deps import CurrentUser, SessionDep
from app.core.response import success
from app.core.security import generate_captcha, verify_captcha
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    ProfileUpdateRequest,
)
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["认证"])


@router.get("/captcha", summary="获取图形验证码")
async def get_captcha():
    key, image = generate_captcha()
    return success({"captcha_key": key, "captcha_image": image})


@router.post("/login", summary="账号密码登录")
async def login(payload: LoginRequest, request: Request, session: SessionDep):
    if payload.captcha_key and not verify_captcha(payload.captcha_key, payload.captcha_code or ""):
        return {"code": 1, "message": "验证码错误或已过期", "data": None}
    ip = request.client.host if request.client else ""
    user = await auth_service.authenticate(session, payload.username, payload.password, ip=ip)
    token = await auth_service.issue_token(user)
    info = await auth_service.build_user_info(session, user)
    return success({"access_token": token, "token_type": "bearer", "user": info})


@router.post("/logout", summary="退出登录")
async def logout(user: CurrentUser):
    return success(message="退出成功")


@router.get("/me", summary="获取当前登录用户信息")
async def me(user: CurrentUser, session: SessionDep):
    info = await auth_service.build_user_info(session, user)
    return success(info)


@router.put("/password", summary="修改密码")
async def change_password(payload: ChangePasswordRequest, user: CurrentUser, session: SessionDep):
    await auth_service.change_password(session, user, payload.old_password, payload.new_password)
    return success(message="密码修改成功")


@router.put("/profile", summary="更新个人资料")
async def update_profile(payload: ProfileUpdateRequest, user: CurrentUser, session: SessionDep):
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    session.add(user)
    await session.commit()
    info = await auth_service.build_user_info(session, user)
    return success(info, message="资料更新成功")
