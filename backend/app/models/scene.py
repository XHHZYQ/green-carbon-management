"""场景与联动域模型（scene，5 张表）。"""

from datetime import datetime
from typing import Any

from sqlmodel import Field

from app.models.base import IdModel, TimeModel, jsonb_field


class SceneInfo(TimeModel, table=True):
    __tablename__ = "scene_info"

    scene_code: str = Field(max_length=64)
    scene_name: str = Field(max_length=64)
    icon: str | None = Field(default=None, max_length=64)
    description: str | None = Field(default=None, max_length=255)
    enable_status: int = Field(default=1)
    last_exec_time: datetime | None = None
    operator_id: int | None = Field(default=None, foreign_key="sys_user.id")


class SceneAction(IdModel, table=True):
    __tablename__ = "scene_action"

    scene_id: int | None = Field(default=None, foreign_key="scene_info.id")
    device_id: int | None = Field(default=None, foreign_key="dev_device.id")
    point_key: str | None = Field(default=None, max_length=64)
    target_value: str | None = Field(default=None, max_length=64)
    delay_sec: int = Field(default=0)
    sort_no: int = Field(default=0)


class SceneSchedule(IdModel, table=True):
    __tablename__ = "scene_schedule"

    scene_id: int | None = Field(default=None, foreign_key="scene_info.id")
    cron_expr: str | None = Field(default=None, max_length=64)
    repeat_desc: str | None = Field(default=None, max_length=128)
    enable_status: int = Field(default=1)
    next_run_time: datetime | None = None


class SceneLinkRule(IdModel, table=True):
    __tablename__ = "scene_link_rule"

    rule_name: str = Field(max_length=64)
    condition_text: str | None = Field(default=None, max_length=255)
    condition_json: Any | None = Field(default=None, sa_column=jsonb_field())
    action_type: str | None = Field(default=None, max_length=32)
    target_scene_id: int | None = Field(default=None, foreign_key="scene_info.id")
    target_device_id: int | None = Field(default=None, foreign_key="dev_device.id")
    target_point_key: str | None = Field(default=None, max_length=64)
    target_value: str | None = Field(default=None, max_length=64)
    enable_status: int = Field(default=1)
    operator_id: int | None = Field(default=None, foreign_key="sys_user.id")
    created_at: datetime | None = Field(default_factory=lambda: datetime.now().astimezone())


class SceneExecLog(IdModel, table=True):
    __tablename__ = "scene_exec_log"

    exec_type: str | None = Field(default=None, max_length=32)
    scene_id: int | None = Field(default=None, foreign_key="scene_info.id")
    rule_id: int | None = Field(default=None, foreign_key="scene_link_rule.id")
    trigger_source: str | None = Field(default=None, max_length=64)
    total_count: int = Field(default=0)
    success_count: int = Field(default=0)
    fail_count: int = Field(default=0)
    result: str | None = Field(default=None, max_length=64)
    exec_time: datetime | None = Field(default_factory=lambda: datetime.now().astimezone())
