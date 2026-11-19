"""v1 路由汇总。"""

from fastapi import APIRouter

from app.api.v1 import auth, config, devices, menus, points, system

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(menus.router)
api_router.include_router(config.router)
api_router.include_router(system.router)
api_router.include_router(devices.router)
api_router.include_router(points.router)
