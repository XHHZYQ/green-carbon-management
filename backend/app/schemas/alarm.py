"""告警与工单域请求模型（B6）。"""

from pydantic import BaseModel


class AlarmConfirmRequest(BaseModel):
    """告警确认请求。"""

    remark: str | None = None


class AlarmHandleRequest(BaseModel):
    """告警处理请求。"""

    remark: str | None = None


class WorkOrderCreate(BaseModel):
    """工单新建请求。"""

    title: str
    type: str | None = None
    level: str | None = None
    device_id: int | None = None
    content: str | None = None
    assignee_id: int | None = None


class WorkOrderUpdate(BaseModel):
    """工单编辑请求（字段均可选）。"""

    title: str | None = None
    type: str | None = None
    level: str | None = None
    device_id: int | None = None
    content: str | None = None
    assignee_id: int | None = None


class WorkOrderAssignRequest(BaseModel):
    """工单指派请求。"""

    assignee_id: int


class WorkOrderHandleRequest(BaseModel):
    """工单处理请求。"""

    handle_result: str
