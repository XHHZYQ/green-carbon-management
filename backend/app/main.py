"""FastAPI 应用入口。"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.response import success
from app.db.session import create_db_and_tables
from app.scheduler import shutdown_scheduler, start_scheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 建表（幂等）
    try:
        await create_db_and_tables()
        logger.info("数据表检查/创建完成")
    except Exception as exc:  # noqa: BLE001
        logger.error("数据库初始化失败：%s", exc)
    start_scheduler()
    yield
    shutdown_scheduler()


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="绿色低碳智慧管控系统 后端 API",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(api_router, prefix=settings.API_PREFIX)


@app.get("/", tags=["系统"], summary="服务健康检查")
async def root():
    return success({"app": settings.APP_NAME, "status": "running"})


@app.get(f"{settings.API_PREFIX}/health", tags=["系统"], summary="健康检查")
async def health():
    return success({"status": "ok"})
