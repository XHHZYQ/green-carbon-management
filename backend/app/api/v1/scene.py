"""场景与联动域接口（B4-2）。"""

from fastapi import APIRouter, Depends, Query

from app.core.deps import CurrentUser, SessionDep, require_perm
from app.core.pagination import PageDep
from app.core.response import paginate, success
from app.schemas.scene import (
    EnableUpdate,
    LinkRuleCreate,
    LinkRuleUpdate,
    SceneActionCreate,
    SceneActionUpdate,
    SceneCreate,
    SceneScheduleConfig,
    SceneUpdate,
)
from app.services import scene_service as svc

router = APIRouter(tags=["场景与联动"])


# ---------------- 场景 ----------------


@router.get("/scenes", summary="场景列表", dependencies=[Depends(require_perm("scene:list:view"))])
async def list_scenes(
    session: SessionDep,
    params: PageDep,
    keyword: str | None = Query(None),
    enable_status: int | None = Query(None),
):
    return success(paginate(**await svc.page_scenes(session, params, keyword, enable_status)))


@router.get("/scenes/{scene_id}", summary="场景详情", dependencies=[Depends(require_perm("scene:list:view"))])
async def scene_detail(scene_id: int, session: SessionDep):
    return success(await svc.get_scene(session, scene_id))


@router.post("/scenes", summary="新建场景", dependencies=[Depends(require_perm("scene:list:exec"))])
async def create_scene(session: SessionDep, user: CurrentUser, payload: SceneCreate):
    return success(await svc.save_scene(session, None, payload.model_dump(), user.id), message="新增成功")


@router.put("/scenes/{scene_id}", summary="编辑场景", dependencies=[Depends(require_perm("scene:list:exec"))])
async def update_scene(session: SessionDep, user: CurrentUser, scene_id: int, payload: SceneUpdate):
    return success(
        await svc.save_scene(session, scene_id, payload.model_dump(exclude_unset=True), user.id), message="修改成功"
    )


@router.delete("/scenes/{scene_id}", summary="删除场景", dependencies=[Depends(require_perm("scene:list:exec"))])
async def delete_scene(scene_id: int, session: SessionDep):
    await svc.delete_scene(session, scene_id)
    return success(None, message="删除成功")


@router.put("/scenes/{scene_id}/enable", summary="启停场景", dependencies=[Depends(require_perm("scene:list:exec"))])
async def enable_scene(scene_id: int, session: SessionDep, payload: EnableUpdate):
    return success(await svc.set_scene_enable(session, scene_id, payload.enable_status), message="操作成功")


@router.post("/scenes/{scene_id}/exec", summary="一键执行场景", dependencies=[Depends(require_perm("scene:list:exec"))])
async def exec_scene(scene_id: int, session: SessionDep, user: CurrentUser):
    return success(await svc.execute_scene(session, scene_id, user.id), message="场景已执行")


@router.post("/scenes/{scene_id}/schedule", summary="配置场景定时", dependencies=[Depends(require_perm("scene:list:exec"))])
async def save_schedule(scene_id: int, session: SessionDep, payload: SceneScheduleConfig):
    return success(await svc.save_schedule(session, scene_id, payload.model_dump()), message="保存成功")


# ---------------- 场景动作 ----------------


@router.get("/scenes/{scene_id}/actions", summary="场景动作列表", dependencies=[Depends(require_perm("scene:list:view"))])
async def list_actions(scene_id: int, session: SessionDep):
    return success(await svc.list_actions(session, scene_id))


@router.post("/scenes/{scene_id}/actions", summary="新增场景动作", dependencies=[Depends(require_perm("scene:list:exec"))])
async def create_action(scene_id: int, session: SessionDep, payload: SceneActionCreate):
    return success(await svc.save_action(session, scene_id, None, payload.model_dump()), message="新增成功")


@router.put("/scenes/actions/{action_id}", summary="编辑场景动作", dependencies=[Depends(require_perm("scene:list:exec"))])
async def update_action(action_id: int, session: SessionDep, payload: SceneActionUpdate):
    return success(
        await svc.save_action(session, 0, action_id, payload.model_dump(exclude_unset=True)), message="修改成功"
    )


@router.delete("/scenes/actions/{action_id}", summary="删除场景动作", dependencies=[Depends(require_perm("scene:list:exec"))])
async def delete_action(action_id: int, session: SessionDep):
    await svc.delete_action(session, action_id)
    return success(None, message="删除成功")


# ---------------- 联动规则 ----------------


@router.get("/link-rules", summary="联动规则列表", dependencies=[Depends(require_perm("scene:link:view"))])
async def list_link_rules(
    session: SessionDep,
    params: PageDep,
    keyword: str | None = Query(None),
    enable_status: int | None = Query(None),
):
    return success(paginate(**await svc.page_link_rules(session, params, keyword, enable_status)))


@router.post("/link-rules", summary="新增联动规则", dependencies=[Depends(require_perm("scene:link:edit"))])
async def create_link_rule(session: SessionDep, user: CurrentUser, payload: LinkRuleCreate):
    return success(await svc.save_link_rule(session, None, payload.model_dump(), user.id), message="新增成功")


@router.put("/link-rules/{rule_id}", summary="编辑联动规则", dependencies=[Depends(require_perm("scene:link:edit"))])
async def update_link_rule(session: SessionDep, rule_id: int, payload: LinkRuleUpdate):
    return success(
        await svc.save_link_rule(session, rule_id, payload.model_dump(exclude_unset=True), None), message="修改成功"
    )


@router.delete("/link-rules/{rule_id}", summary="删除联动规则", dependencies=[Depends(require_perm("scene:link:edit"))])
async def delete_link_rule(rule_id: int, session: SessionDep):
    await svc.delete_link_rule(session, rule_id)
    return success(None, message="删除成功")


@router.put("/link-rules/{rule_id}/enable", summary="启停联动规则", dependencies=[Depends(require_perm("scene:link:edit"))])
async def enable_link_rule(rule_id: int, session: SessionDep, payload: EnableUpdate):
    return success(await svc.set_rule_enable(session, rule_id, payload.enable_status), message="操作成功")


# ---------------- 执行记录 ----------------


@router.get("/scene-exec-logs", summary="场景执行记录", dependencies=[Depends(require_perm("scene:log:view"))])
async def list_exec_logs(
    session: SessionDep,
    params: PageDep,
    exec_type: str | None = Query(None),
    scene_id: int | None = Query(None),
    result: str | None = Query(None),
):
    return success(paginate(**await svc.page_exec_logs(session, params, exec_type, scene_id, result)))
