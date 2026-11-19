"""消息通知域请求模型（B6）。"""

from pydantic import BaseModel


class NotifySendRequest(BaseModel):
    """发送通知请求。"""

    title: str
    content: str | None = None
    msg_type: str = "internal"
    level: str = "info"
    receiver_ids: list[int]
    channel_ids: list[int] | None = None
