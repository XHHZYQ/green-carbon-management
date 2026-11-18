"""业务异常与全局异常处理。"""

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.response import fail


class BizException(Exception):
    """业务异常，统一转换为 { code, message, data }。"""

    def __init__(self, message: str = "业务处理失败", code: int = 1, http_status: int = status.HTTP_200_OK):
        self.message = message
        self.code = code
        self.http_status = http_status
        super().__init__(message)


class UnauthorizedException(BizException):
    def __init__(self, message: str = "未登录或登录已过期"):
        super().__init__(message=message, code=401, http_status=status.HTTP_401_UNAUTHORIZED)


class ForbiddenException(BizException):
    def __init__(self, message: str = "无访问权限"):
        super().__init__(message=message, code=403, http_status=status.HTTP_403_FORBIDDEN)


def register_exception_handlers(app: FastAPI) -> None:
    """注册全局异常处理器。"""

    @app.exception_handler(BizException)
    async def _biz_handler(request: Request, exc: BizException):
        return JSONResponse(status_code=exc.http_status, content=fail(code=exc.code, message=exc.message))

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(request: Request, exc: RequestValidationError):
        errors = exc.errors()
        msg = errors[0].get("msg", "参数校验失败") if errors else "参数校验失败"
        return JSONResponse(status_code=status.HTTP_200_OK, content=fail(code=422, message=f"参数校验失败：{msg}"))

    @app.exception_handler(StarletteHTTPException)
    async def _http_handler(request: Request, exc: StarletteHTTPException):
        return JSONResponse(status_code=exc.status_code, content=fail(code=exc.status_code, message=str(exc.detail)))

    @app.exception_handler(Exception)
    async def _unhandled_handler(request: Request, exc: Exception):
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=fail(code=500, message=f"服务器内部错误：{exc}"))
