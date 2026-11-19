"""消息通知域服务（渠道 / 模板 / 规则 / 站内消息 / 发送记录）。"""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BizException
from app.models.notify import (
    NotifyChannel,
    NotifyMessage,
    NotifyRule,
    NotifySendLog,
    NotifyTemplate,
)
from app.models.sys import SysUser


def _user_name(user: SysUser | None) -> str | None:
    if not user:
        return None
    return user.real_name or user.username


# ==================== 站内消息 ====================


async def page_messages(
    session: AsyncSession,
    page: int = 1,
    page_size: int = 10,
    msg_type: str | None = None,
    level: str | None = None,
    read_status: int | None = None,
    keyword: str | None = None,
) -> tuple[int, list[dict]]:
    conds = []
    if msg_type:
        conds.append(NotifyMessage.msg_type == msg_type)
    if level:
        conds.append(NotifyMessage.level == level)
    if read_status is not None:
        conds.append(NotifyMessage.read_status == read_status)
    if keyword:
        conds.append(NotifyMessage.title.ilike(f"%{keyword}%"))

    count_stmt = select(func.count(NotifyMessage.id))
    stmt = select(NotifyMessage)
    for c in conds:
        count_stmt = count_stmt.where(c)
        stmt = stmt.where(c)

    total = int((await session.execute(count_stmt)).scalar_one() or 0)
    rows = (
        await session.execute(
            stmt.order_by(NotifyMessage.send_time.desc(), NotifyMessage.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).scalars().all()

    receiver_ids = {r.receiver_id for r in rows if r.receiver_id}
    name_map: dict[int, str] = {}
    if receiver_ids:
        users = (
            await session.execute(select(SysUser).where(SysUser.id.in_(receiver_ids)))
        ).scalars().all()
        name_map = {u.id: (u.real_name or u.username) for u in users}

    items = []
    for r in rows:
        item = r.model_dump()
        item["receiver_name"] = name_map.get(r.receiver_id) if r.receiver_id else None
        items.append(item)
    return total, items


async def mark_read(session: AsyncSession, message_id: int) -> dict:
    msg = await session.get(NotifyMessage, message_id)
    if not msg:
        raise BizException("消息不存在")
    if msg.read_status != 1:
        msg.read_status = 1
        msg.read_time = datetime.now().astimezone()
        session.add(msg)
        await session.commit()
    return {"id": message_id, "read_status": 1}


async def mark_all_read(session: AsyncSession, receiver_id: int) -> dict:
    now = datetime.now().astimezone()
    rows = (
        await session.execute(
            select(NotifyMessage).where(
                NotifyMessage.receiver_id == receiver_id,
                NotifyMessage.read_status == 0,
            )
        )
    ).scalars().all()
    for msg in rows:
        msg.read_status = 1
        msg.read_time = now
        session.add(msg)
    await session.commit()
    return {"updated": len(rows)}


async def unread_count(session: AsyncSession, receiver_id: int) -> int:
    stmt = select(func.count(NotifyMessage.id)).where(
        NotifyMessage.receiver_id == receiver_id,
        NotifyMessage.read_status == 0,
    )
    return int((await session.execute(stmt)).scalar_one() or 0)


async def send_message(session: AsyncSession, data: dict, sender_id: int) -> dict:
    """发送站内消息：为每个接收人写一条消息，为每个渠道写一条发送记录。"""
    receiver_ids = list(data.get("receiver_ids") or [])
    if not receiver_ids:
        raise BizException("请至少选择一个接收人")

    title = data.get("title")
    content = data.get("content")
    msg_type = data.get("msg_type") or "internal"
    level = data.get("level") or "info"
    now = datetime.now().astimezone()

    users = (
        await session.execute(select(SysUser).where(SysUser.id.in_(receiver_ids)))
    ).scalars().all()
    name_map = {u.id: (u.real_name or u.username) for u in users}

    # 站内消息
    for rid in receiver_ids:
        session.add(
            NotifyMessage(
                title=title,
                content=content,
                msg_type=msg_type,
                level=level,
                receiver_id=rid,
                read_status=0,
                send_time=now,
            )
        )

    # 发送渠道：未指定则使用全部启用的渠道
    channel_ids = data.get("channel_ids")
    if channel_ids:
        channels = (
            await session.execute(select(NotifyChannel).where(NotifyChannel.id.in_(channel_ids)))
        ).scalars().all()
    else:
        channels = (
            await session.execute(select(NotifyChannel).where(NotifyChannel.enable_status == 1))
        ).scalars().all()

    log_count = 0
    for ch in channels:
        for rid in receiver_ids:
            session.add(
                NotifySendLog(
                    channel_id=ch.id,
                    receiver=name_map.get(rid),
                    title=title,
                    content=content,
                    send_status="success",
                    send_time=now,
                )
            )
            log_count += 1

    await session.commit()
    return {"message_count": len(receiver_ids), "log_count": log_count}


# ==================== 发送记录 ====================


async def page_send_logs(
    session: AsyncSession,
    page: int = 1,
    page_size: int = 10,
    send_status: str | None = None,
) -> tuple[int, list[dict]]:
    conds = []
    if send_status:
        conds.append(NotifySendLog.send_status == send_status)

    count_stmt = select(func.count(NotifySendLog.id))
    stmt = select(NotifySendLog)
    for c in conds:
        count_stmt = count_stmt.where(c)
        stmt = stmt.where(c)

    total = int((await session.execute(count_stmt)).scalar_one() or 0)
    rows = (
        await session.execute(
            stmt.order_by(NotifySendLog.send_time.desc(), NotifySendLog.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).scalars().all()

    rule_names = {r.id: r.rule_name for r in (await session.execute(select(NotifyRule))).scalars().all()}
    template_names = {
        t.id: t.template_name for t in (await session.execute(select(NotifyTemplate))).scalars().all()
    }
    channel_names = {
        c.id: c.channel_name for c in (await session.execute(select(NotifyChannel))).scalars().all()
    }

    items = []
    for r in rows:
        item = r.model_dump()
        item["rule_name"] = rule_names.get(r.rule_id) if r.rule_id else None
        item["template_name"] = template_names.get(r.template_id) if r.template_id else None
        item["channel_name"] = channel_names.get(r.channel_id) if r.channel_id else None
        items.append(item)
    return total, items
