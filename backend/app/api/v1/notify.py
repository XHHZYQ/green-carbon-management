"""消息通知域接口（B6：渠道 / 模板 / 规则 / 站内消息 / 发送记录）。"""

from fastapi import APIRouter, Depends, Query

from app.api.v1._crud import crud_router
from app.core.deps import CurrentUser, SessionDep, require_perm
from app.core.pagination import PageDep
from app.core.response import paginate, success
from app.models.notify import NotifyChannel, NotifyRule, NotifyTemplate
from app.schemas.notify import NotifySendRequest
from app.services import notify_service as svc

READ = "notify:view"
SEND = "notify:message:send"
MSG_VIEW = "notify:message:view"

router = APIRouter(prefix="/notify", tags=["消息通知"])

# 通用 CRUD 子路由（渠道 / 模板 / 规则）
for _sub in (
    crud_router(model=NotifyChannel, prefix="/channels", tag="通知渠道",
                read_perm=READ, write_perm=SEND, search_fields=("channel_code", "channel_name")),
    crud_router(model=NotifyTemplate, prefix="/templates", tag="通知模板",
                read_perm=READ, write_perm=SEND, search_fields=("template_code", "template_name")),
    crud_router(model=NotifyRule, prefix="/rules", tag="通知规则",
                read_perm=READ, write_perm=SEND, search_fields=("rule_name",)),
):
    router.include_router(_sub)


# ==================== 站内消息 ====================


@router.get("/messages/unread-count", summary="未读消息数", dependencies=[Depends(require_perm(MSG_VIEW))])
async def message_unread_count(
    session: SessionDep,
    user: CurrentUser,
    receiver_id: int | None = Query(None, description="接收人，默认当前登录用户"),
):
    return success({"count": await svc.unread_count(session, receiver_id or user.id)})


@router.put("/messages/read-all", summary="全部标记已读", dependencies=[Depends(require_perm(MSG_VIEW))])
async def message_mark_all_read(
    session: SessionDep,
    user: CurrentUser,
    receiver_id: int | None = Query(None, description="接收人，默认当前登录用户"),
):
    return success(await svc.mark_all_read(session, receiver_id or user.id), message="操作成功")


@router.get("/messages", summary="消息列表", dependencies=[Depends(require_perm(MSG_VIEW))])
async def message_list(
    session: SessionDep,
    params: PageDep,
    msg_type: str | None = Query(None),
    level: str | None = Query(None),
    read_status: int | None = Query(None),
    keyword: str | None = Query(None),
):
    total, items = await svc.page_messages(
        session, params.page, params.page_size, msg_type, level, read_status, keyword
    )
    return success(paginate(total, items))


@router.post("/messages", summary="发送通知", dependencies=[Depends(require_perm(SEND))])
async def message_send(session: SessionDep, user: CurrentUser, payload: NotifySendRequest):
    return success(await svc.send_message(session, payload.model_dump(), user.id), message="发送成功")


@router.put("/messages/{message_id}/read", summary="标记已读", dependencies=[Depends(require_perm(MSG_VIEW))])
async def message_mark_read(message_id: int, session: SessionDep):
    return success(await svc.mark_read(session, message_id), message="操作成功")


# ==================== 发送记录 ====================


@router.get("/send-logs", summary="发送记录", dependencies=[Depends(require_perm(MSG_VIEW))])
async def send_log_list(
    session: SessionDep,
    params: PageDep,
    send_status: str | None = Query(None),
):
    total, items = await svc.page_send_logs(session, params.page, params.page_size, send_status)
    return success(paginate(total, items))
