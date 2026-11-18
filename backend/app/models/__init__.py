"""SQLModel 表模型汇总（导入即注册到 SQLModel.metadata）。"""

from app.models.alarm import AlarmInfo, AlarmRule
from app.models.base import IdModel, TimeModel
from app.models.carbon import CarbonEmission, CarbonReport
from app.models.cfg import (
    CfgCarbonFactor,
    CfgDeviceType,
    CfgDictItem,
    CfgDictType,
    CfgEnergyItem,
    CfgEnergyType,
    CfgProtocol,
    CfgProtocolParam,
    CfgSystemParam,
)
from app.models.ctrl import CtrlCommand, CtrlTimedTask
from app.models.dev import (
    DevAccessLog,
    DevArea,
    DevCollectTask,
    DevControlPoint,
    DevData,
    DevDataPatch,
    DevDevice,
    DevDeviceConn,
    DevPoint,
    DevPointTemplate,
    DevPointTemplateItem,
)
from app.models.energy import (
    EnergyFeeStat,
    EnergyPriceHistory,
    EnergyPricePeriod,
    EnergyPricePlan,
    EnergyStat,
)
from app.models.mon import MonTopology, MonTopologyNode
from app.models.notify import (
    NotifyChannel,
    NotifyMessage,
    NotifyRule,
    NotifySendLog,
    NotifyTemplate,
)
from app.models.quota import EnergyQuota, QuotaAssess, QuotaMonitor
from app.models.report import ReportRecord, ReportSubscribe, ReportTemplate
from app.models.scene import (
    SceneAction,
    SceneExecLog,
    SceneInfo,
    SceneLinkRule,
    SceneSchedule,
)
from app.models.sys import (
    SysLoginLog,
    SysMenu,
    SysOperLog,
    SysRole,
    SysRoleMenu,
    SysUser,
    SysUserRole,
)
from app.models.wo import WoWorkOrder

__all__ = [
    "IdModel",
    "TimeModel",
    "SysUser",
    "SysRole",
    "SysUserRole",
    "SysMenu",
    "SysRoleMenu",
    "SysOperLog",
    "SysLoginLog",
    "CfgDictType",
    "CfgDictItem",
    "CfgEnergyType",
    "CfgEnergyItem",
    "CfgCarbonFactor",
    "CfgDeviceType",
    "CfgProtocol",
    "CfgProtocolParam",
    "CfgSystemParam",
    "DevArea",
    "DevDevice",
    "DevDeviceConn",
    "DevPoint",
    "DevPointTemplate",
    "DevPointTemplateItem",
    "DevControlPoint",
    "DevCollectTask",
    "DevData",
    "DevDataPatch",
    "DevAccessLog",
    "MonTopology",
    "MonTopologyNode",
    "CtrlCommand",
    "CtrlTimedTask",
    "SceneInfo",
    "SceneAction",
    "SceneSchedule",
    "SceneLinkRule",
    "SceneExecLog",
    "EnergyStat",
    "EnergyPricePlan",
    "EnergyPricePeriod",
    "EnergyFeeStat",
    "EnergyPriceHistory",
    "CarbonEmission",
    "CarbonReport",
    "EnergyQuota",
    "QuotaMonitor",
    "QuotaAssess",
    "AlarmRule",
    "AlarmInfo",
    "WoWorkOrder",
    "NotifyChannel",
    "NotifyTemplate",
    "NotifyRule",
    "NotifyMessage",
    "NotifySendLog",
    "ReportTemplate",
    "ReportRecord",
    "ReportSubscribe",
]
