"""节能定额域请求模型（B6）。"""

from pydantic import BaseModel


class QuotaMonitorRefreshRequest(BaseModel):
    """定额监控刷新请求。period_value 为空则刷新当月。"""

    period_value: str | None = None


class QuotaAssessGenerateRequest(BaseModel):
    """定额考核生成请求。"""

    period_value: str
