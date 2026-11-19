"""写操作自动记录操作日志（纯 ASGI 中间件，捕获请求体后继续透传）。"""

import json
import time
from typing import Any

from app.core.security import decode_access_token

WRITE_METHODS = {"POST", "PUT", "DELETE", "PATCH"}
ACTION_MAP = {"POST": "新增", "PUT": "修改", "DELETE": "删除", "PATCH": "修改"}
MODULE_MAP = {"config": "基础配置", "system": "系统管理", "auth": "认证"}
SKIP_PREFIXES = ("/api/v1/auth",)


class OperLogMiddleware:
    """记录 /api/v1 下写操作的请求信息到 sys_oper_log。"""

    def __init__(self, app, prefix: str = "/api/v1"):
        self.app = app
        self.prefix = prefix

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            return await self.app(scope, receive, send)

        method = scope.get("method", "")
        path = scope.get("path", "")
        if method not in WRITE_METHODS or not path.startswith(self.prefix) or path.startswith(SKIP_PREFIXES):
            return await self.app(scope, receive, send)

        body = b""

        async def receive_wrapper():
            nonlocal body
            message = await receive()
            if message["type"] == "http.request":
                body += message.get("body", b"")
            return message

        holder: dict[str, Any] = {}
        start = time.perf_counter()

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                holder["status"] = message["status"]
            await send(message)

        try:
            await self.app(scope, receive_wrapper, send_wrapper)
        finally:
            cost_ms = int((time.perf_counter() - start) * 1000)
            try:
                await self._write_log(scope, method, path, body, holder.get("status", 200), cost_ms)
            except Exception:  # noqa: BLE001 日志失败不影响业务
                pass

    async def _write_log(self, scope, method: str, path: str, body: bytes, status: int, cost_ms: int) -> None:
        from app.db.session import SessionLocal
        from app.models.sys import SysOperLog

        user_id, username = self._parse_user(scope)
        segments = [s for s in path[len(self.prefix):].split("/") if s]
        module_key = segments[0] if segments else ""
        request_param = body.decode("utf-8", "ignore")[:2000] if body else ""

        async with SessionLocal() as session:
            session.add(
                SysOperLog(
                    user_id=user_id,
                    username=username,
                    module=MODULE_MAP.get(module_key, module_key or "其他"),
                    action=ACTION_MAP.get(method, method),
                    method=method,
                    request_url=path[:255],
                    request_param=request_param or None,
                    ip=scope.get("client", ("", 0))[0] if scope.get("client") else "",
                    status=1 if status < 400 else 0,
                    error_msg=None if status < 400 else f"HTTP {status}",
                    cost_ms=cost_ms,
                )
            )
            await session.commit()

    @staticmethod
    def _parse_user(scope) -> tuple[int | None, str | None]:
        for name, value in scope.get("headers", []):
            if name.lower() == b"authorization":
                token = value.decode("latin-1")
                if token.lower().startswith("bearer "):
                    try:
                        payload = decode_access_token(token[7:].strip())
                        return int(payload["sub"]), payload.get("username")
                    except Exception:  # noqa: BLE001
                        return None, None
        return None, None
