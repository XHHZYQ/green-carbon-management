"""基础配置中心接口（/config/*）。"""

from datetime import datetime

from fastapi import APIRouter, Body, Depends
from sqlmodel import select

from app.api.v1._crud import crud_router
from app.core.deps import SessionDep, require_perm
from app.core.response import success
from app.models import (
    CfgCarbonFactor,
    CfgDeviceType,
    CfgDictItem,
    CfgDictType,
    CfgEnergyItem,
    CfgEnergyType,
    CfgProtocol,
    CfgProtocolParam,
    CfgSystemParam,
)

READ = "config:view"
WRITE = "config:edit"

router = APIRouter()

# 通用 CRUD 子路由
for _sub in (
    crud_router(model=CfgDictType, prefix="/config/dict-types", tag="字典类型",
                read_perm=READ, write_perm=WRITE, search_fields=("type_code", "type_name")),
    crud_router(model=CfgDictItem, prefix="/config/dict-items", tag="字典项",
                read_perm=READ, write_perm=WRITE, search_fields=("item_label",), order_by="sort_no"),
    crud_router(model=CfgEnergyType, prefix="/config/energy-types", tag="能源类型",
                read_perm=READ, write_perm=WRITE, search_fields=("type_code", "type_name"), order_by="sort_no"),
    crud_router(model=CfgEnergyItem, prefix="/config/energy-items", tag="分项分类",
                read_perm=READ, write_perm=WRITE, search_fields=("item_code", "item_name"), order_by="sort_no"),
    crud_router(model=CfgCarbonFactor, prefix="/config/carbon-factors", tag="碳因子",
                read_perm=READ, write_perm=WRITE, search_fields=("factor_name",)),
    crud_router(model=CfgDeviceType, prefix="/config/device-types", tag="设备类型",
                read_perm=READ, write_perm=WRITE, search_fields=("type_code", "type_name"), order_by="sort_no"),
    crud_router(model=CfgProtocol, prefix="/config/protocols", tag="通信协议",
                read_perm=READ, write_perm=WRITE, search_fields=("protocol_code", "protocol_name")),
    crud_router(model=CfgProtocolParam, prefix="/config/protocol-params", tag="协议参数",
                read_perm=READ, write_perm=WRITE, search_fields=("param_key", "param_label"), order_by="sort_no"),
):
    router.include_router(_sub)


@router.get("/config/system-params", tags=["系统参数"], summary="系统参数列表",
            dependencies=[Depends(require_perm(READ))])
async def list_system_params(session: SessionDep):
    rows = (await session.execute(select(CfgSystemParam).order_by(CfgSystemParam.id))).scalars().all()
    return success(rows)


@router.put("/config/system-params", tags=["系统参数"], summary="系统参数批量保存",
            dependencies=[Depends(require_perm(WRITE))])
async def save_system_params(session: SessionDep, payload: list[dict] = Body(...)):
    now = datetime.now().astimezone()
    for item in payload:
        if not item.get("id"):
            continue
        param = await session.get(CfgSystemParam, int(item["id"]))
        if param:
            param.param_value = item.get("param_value")
            param.updated_at = now
            session.add(param)
    await session.commit()
    return success(message="保存成功")
