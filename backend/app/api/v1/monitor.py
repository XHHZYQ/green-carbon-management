"""实时监控域接口（实时数据 / 组态图 / 平面图）。"""

from fastapi import APIRouter, Depends, Query

from app.core.deps import SessionDep, require_perm
from app.core.pagination import PageDep
from app.core.response import paginate, success
from app.schemas.monitor import TopologyCreate, TopologyUpdate
from app.services import monitor_service as svc

router = APIRouter(prefix="/monitor", tags=["实时监控"])


@router.get("/realtime", summary="设备实时测点值", dependencies=[Depends(require_perm("monitor:view"))])
async def realtime(
    session: SessionDep,
    device_id: int | None = Query(None),
    area_id: int | None = Query(None),
    keyword: str | None = Query(None),
):
    return success(await svc.realtime(session, device_id, area_id, keyword))


@router.get("/curve", summary="测点实时曲线", dependencies=[Depends(require_perm("monitor:view"))])
async def curve(
    session: SessionDep,
    point_id: int = Query(..., description="测点ID"),
    hours: int = Query(1, ge=1, le=168, description="最近N小时"),
):
    return success(await svc.curve(session, point_id, hours))


@router.get("/topology", summary="组态/平面图列表", dependencies=[Depends(require_perm("monitor:view"))])
async def list_topology(
    session: SessionDep,
    params: PageDep,
    keyword: str | None = Query(None),
    topo_type: str | None = Query(None, description="topology / plan"),
):
    return success(paginate(**await svc.page_topologies(session, params, keyword, topo_type)))


@router.get("/topology/{topo_id}", summary="组态图详情", dependencies=[Depends(require_perm("monitor:view"))])
async def topology_detail(topo_id: int, session: SessionDep):
    return success(await svc.get_topology(session, topo_id))


@router.post("/topology", summary="新建组态图", dependencies=[Depends(require_perm("monitor:topology:edit"))])
async def create_topology(session: SessionDep, payload: TopologyCreate):
    return success(await svc.create_topology(session, payload), message="新建成功")


@router.put("/topology/{topo_id}", summary="保存组态图", dependencies=[Depends(require_perm("monitor:topology:edit"))])
async def update_topology(topo_id: int, session: SessionDep, payload: TopologyUpdate):
    return success(await svc.update_topology(session, topo_id, payload), message="保存成功")


@router.delete("/topology/{topo_id}", summary="删除组态图", dependencies=[Depends(require_perm("monitor:topology:edit"))])
async def delete_topology(topo_id: int, session: SessionDep):
    await svc.delete_topology(session, topo_id)
    return success(None, message="删除成功")
