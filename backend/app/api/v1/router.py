"""v1 路由汇总。"""

from fastapi import APIRouter

from app.api.v1 import (
    auth,
    carbon,
    config,
    control,
    devices,
    energy,
    fee,
    menus,
    monitor,
    points,
    price,
    scene,
    system,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(menus.router)
api_router.include_router(config.router)
api_router.include_router(system.router)
api_router.include_router(devices.router)
api_router.include_router(points.router)
api_router.include_router(monitor.router)
api_router.include_router(control.router)
api_router.include_router(scene.router)
api_router.include_router(energy.router)
api_router.include_router(price.router)
api_router.include_router(fee.router)
api_router.include_router(carbon.router)
