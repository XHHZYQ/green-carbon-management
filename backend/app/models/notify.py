"""消息通知域模型（notify，5 张表）。"""

from datetime import datetime
from typing import Any

from sqlmodel import Field

from app.models.base import IdModel, jsonb_field


class NotifyChannel(IdModel, table=True):
    __tablename__ = "notify_channel"

    channel_code: str = Field(max_length=64)
    channel_name: str = Field(max_length=64)
    channel_type: str | None = Field(default=None, max_length=32)  # email / sms / webhook / internal
    config_json: Any | None = Field(default=None, sa_column=jsonb_field())
    enable_status: int = Field(default=1)
    created_at: datetime | None = Field(default_factory=lambda: datetime.now().astimezone())


class NotifyTemplate(IdModel, table=True):
    __tablename__ = "notify_template"

    template_code: str = Field(max_length=64)
    template_name: str = Field(max_length=64)
    channel_type: str | None = Field(default=None, max_length=32)
    title: str | None = Field(default=None, max_length=128)
    content: str | None = None
    variables: str | None = Field(default=None, max_length=255)
    status: int = Field(default=1)
    created_at: datetime | None = Field(default_factory=lambda: datetime.now().astimezone())


class NotifyRule(IdModel, table=True):
    __tablename__ = "notify_rule"

    rule_name: str = Field(max_length=64)
    event_type: str | None = Field(default=None, max_length=64)
    condition_json: Any | None = Field(default=None, sa_column=jsonb_field())
    channel_ids: str | None = Field(default=None, max_length=255)
    receiver_ids: str | None = Field(default=None, max_length=255)
    enable_status: int = Field(default=1)
    created_at: datetime | None = Field(default_factory=lambda: datetime.now().astimezone())


class NotifyMessage(IdModel, table=True):
    __tablename__ = "notify_message"

    title: str = Field(max_length=128)
    content: str | None = None
    msg_type: str | None = Field(default=None, max_length=32)
    level: str | None = Field(default=None, max_length=32)
    receiver_id: int | None = Field(default=None, foreign_key="sys_user.id")
    read_status: int = Field(default=0)
    read_time: datetime | None = None
    send_time: datetime | None = Field(default_factory=lambda: datetime.now().astimezone())


class NotifySendLog(IdModel, table=True):
    __tablename__ = "notify_send_log"

    rule_id: int | None = Field(default=None, foreign_key="notify_rule.id")
    template_id: int | None = Field(default=None, foreign_key="notify_template.id")
    channel_id: int | None = Field(default=None, foreign_key="notify_channel.id")
    receiver: str | None = Field(default=None, max_length=128)
    title: str | None = Field(default=None, max_length=128)
    content: str | None = None
    send_status: str | None = Field(default=None, max_length=32)
    error_msg: str | None = None
    send_time: datetime | None = Field(default_factory=lambda: datetime.now().astimezone())
