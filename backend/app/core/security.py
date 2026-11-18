"""安全相关：密码加密、JWT 签发与校验、图形验证码。"""

import base64
import random
import string
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import settings


# ---------- 密码 ----------
def hash_password(password: str) -> str:
    """使用 bcrypt 生成密码哈希。"""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


# ---------- JWT ----------
def create_access_token(subject: str | int, extra: dict | None = None) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(subject),
        "iat": now,
        "exp": now + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])


# ---------- 图形验证码 ----------
_captcha_store: dict[str, str] = {}


def generate_captcha(length: int = 4) -> tuple[str, str]:
    """生成验证码，返回 (captcha_key, base64 图片)。验证码答案存入内存。"""
    chars = string.ascii_uppercase + string.digits
    code = "".join(random.choices(chars, k=length))
    key = "".join(random.choices(string.ascii_lowercase + string.digits, k=16))
    _captcha_store[key] = code.lower()

    from PIL import Image, ImageDraw

    width, height = 120, 44
    image = Image.new("RGB", (width, height), (30, 80, 200))
    draw = ImageDraw.Draw(image)
    for _ in range(6):
        draw.line(
            (random.randint(0, width), random.randint(0, height), random.randint(0, width), random.randint(0, height)),
            fill=(255, 255, 255),
            width=1,
        )
    draw.text((28, 12), code, fill=(255, 255, 255))

    from io import BytesIO

    buf = BytesIO()
    image.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    return key, f"data:image/png;base64,{b64}"


def verify_captcha(key: str, code: str) -> bool:
    expected = _captcha_store.pop(key, None)
    if expected is None:
        return False
    return expected == (code or "").lower()
