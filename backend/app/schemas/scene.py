"""场景与联动请求模型（B4-2）。"""

from typing import Any

from pydantic import BaseModel


class SceneCreate(BaseModel):
    scene_code: str
    scene_name: str
    icon: str | None = None
    description: str | None = None
    enable_status: int = 1


class SceneUpdate(BaseModel):
    scene_code: str | None = None
    scene_name: str | None = None
    icon: str | None = None
    description: str | None = None
    enable_status: int | None = None


class EnableUpdate(BaseModel):
    """启用/停用。"""

    enable_status: int


class SceneActionCreate(BaseModel):
    device_id: int
    point_key: str
    target_value: str
    delay_sec: int = 0
    sort_no: int = 0


class SceneActionUpdate(BaseModel):
    device_id: int | None = None
    point_key: str | None = None
    target_value: str | None = None
    delay_sec: int | None = None
    sort_no: int | None = None


class SceneScheduleConfig(BaseModel):
    """场景定时配置。"""

    cron_expr: str
    repeat_desc: str | None = None
    enable_status: int = 1


class LinkRuleCreate(BaseModel):
    rule_name: str
    condition_text: str | None = None
    condition_json: dict[str, Any] | None = None
    action_type: str = "scene"  # scene=触发场景 / control=下发控制
    target_scene_id: int | None = None
    target_device_id: int | None = None
    target_point_key: str | None = None
    target_value: str | None = None
    enable_status: int = 1


class LinkRuleUpdate(BaseModel):
    rule_name: str | None = None
    condition_text: str | None = None
    condition_json: dict[str, Any] | None = None
    action_type: str | None = None
    target_scene_id: int | None = None
    target_device_id: int | None = None
    target_point_key: str | None = None
    target_value: str | None = None
    enable_status: int | None = None
