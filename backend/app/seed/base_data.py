"""基础数据初始化（字典、能源类型、碳因子、设备类型、协议、菜单、用户角色）。"""

from datetime import date, datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import func, select

from app.core.security import hash_password
from app.models import (
    CfgCarbonFactor,
    CfgDeviceType,
    CfgDictItem,
    CfgDictType,
    CfgEnergyItem,
    CfgEnergyType,
    CfgProtocol,
    CfgProtocolParam,
    CfgSystemParam,
    SysMenu,
    SysRole,
    SysRoleMenu,
    SysUser,
    SysUserRole,
)

# ---------------------------------------------------------------- 角色

ROLES = [
    ("admin", "系统管理员", "系统最高管理者，拥有全部功能权限", 1),
    ("energy_admin", "能源管理员", "负责能耗、费用与碳排管理", 2),
    ("ops", "运维人员", "负责设备管理与告警处理", 3),
    ("viewer", "普通用户", "只读查看驾驶舱、台账与报表", 4),
]

# ---------------------------------------------------------------- 用户

USERS = [
    ("admin", "admin123", "系统管理员", "13800000001", "admin@green.com", "信息中心"),
    ("energy", "energy123", "李能源", "13800000002", "energy@green.com", "能源管理部"),
    ("ops", "ops123", "王运维", "13800000003", "ops@green.com", "运维部"),
    ("viewer", "viewer123", "赵访客", "13800000004", "viewer@green.com", "行政部"),
]

# ---------------------------------------------------------------- 字典

DICT_TYPES = {
    "device_status": ("设备状态", [("正常", "normal"), ("停用", "disabled"), ("维修", "repair"), ("报废", "scrapped")]),
    "online_status": ("在线状态", [("在线", "online"), ("离线", "offline"), ("异常", "abnormal")]),
    "alarm_level": ("告警等级", [("紧急", "critical"), ("重要", "major"), ("次要", "minor"), ("提示", "info")]),
    "alarm_status": ("告警状态", [("待确认", "pending"), ("已确认", "confirmed"), ("已处理", "handled"), ("已忽略", "ignored")]),
    "work_order_status": ("工单状态", [("待处理", "pending"), ("处理中", "processing"), ("已完成", "finished"), ("已关闭", "closed")]),
    "work_order_type": ("工单类型", [("故障处理", "fault"), ("设备保养", "maintain"), ("巡检任务", "inspect"), ("其他", "other")]),
    "energy_period": ("电价时段", [("尖峰", "sharp"), ("高峰", "peak"), ("平段", "flat"), ("低谷", "valley")]),
    "collect_mode": ("采集方式", [("定时采集", "timed"), ("周期采集", "period"), ("触发采集", "trigger")]),
    "point_type": ("测点类型", [("模拟量", "analog"), ("数字量", "digital"), ("累积量", "accumulate"), ("状态量", "status")]),
    "data_quality": ("数据质量", [("正常", "normal"), ("可疑", "doubt"), ("补录", "patched"), ("缺失", "missing")]),
    "day_type": ("日期类型", [("工作日", "workday"), ("周末", "weekend"), ("节假日", "holiday")]),
    "enable_status": ("启用状态", [("启用", "enabled"), ("停用", "disabled")]),
    "report_type": ("报表类型", [("日报", "daily"), ("周报", "weekly"), ("月报", "monthly"), ("年报", "yearly")]),
    "notify_type": ("通知类型", [("站内消息", "internal"), ("邮件", "email"), ("短信", "sms"), ("Webhook", "webhook")]),
    "device_category": ("设备大类", [("计量类", "meter"), ("电源类", "power"), ("控制类", "control"), ("环境类", "env"), ("辅助类", "auxiliary")]),
}

# ---------------------------------------------------------------- 能源类型

ENERGY_TYPES = [
    ("electricity", "电力", "kWh", 1),
    ("water", "水", "m³", 2),
    ("gas", "天然气", "m³", 3),
    ("steam", "蒸汽", "t", 4),
    ("compressed_air", "压缩空气", "m³", 5),
    ("pv", "光伏发电", "kWh", 6),
    ("heating", "市政热力", "GJ", 7),
    ("gasoline", "汽油", "L", 8),
    ("diesel", "柴油", "L", 9),
]

# 分项计量（父项 -> 子项）
ENERGY_ITEMS = [
    ("lighting", "照明用电", None, "electricity", 1),
    ("hvac", "空调用电", None, "electricity", 2),
    ("elevator", "电梯用电", None, "electricity", 3),
    ("office", "办公设备用电", None, "electricity", 4),
    ("power", "动力用电", None, "electricity", 5),
    ("datacenter", "数据中心用电", "power", "electricity", 6),
    ("socket", "插座用电", None, "electricity", 7),
    ("pump", "给排水用电", "power", "electricity", 8),
    ("domestic_water", "生活用水", None, "water", 9),
    ("fire_water", "消防用水", None, "water", 10),
    ("boiler_gas", "锅炉用气", None, "gas", 11),
    ("canteen_gas", "食堂用气", None, "gas", 12),
    ("pv_generation", "光伏发电量", None, "pv", 13),
    ("pv_self_use", "光伏自用电", "pv_generation", "pv", 14),
    ("pv_grid", "光伏上网电量", "pv_generation", "pv", 15),
    ("ac_air", "空压机产气", None, "compressed_air", 16),
]

# ---------------------------------------------------------------- 碳因子（kgCO2e / 单位）

CARBON_FACTORS = [
    ("electricity", "电力碳排放因子（华北电网）", "0.5703", "kgCO2e/kWh", "范围二", date(2024, 1, 1), date(2026, 12, 31)),
    ("water", "自来水碳排放因子", "0.3440", "kgCO2e/m³", "范围三", date(2024, 1, 1), date(2026, 12, 31)),
    ("gas", "天然气碳排放因子", "2.1622", "kgCO2e/m³", "范围一", date(2024, 1, 1), date(2026, 12, 31)),
    ("steam", "外购蒸汽碳排放因子", "0.1100", "kgCO2e/kg", "范围二", date(2024, 1, 1), date(2026, 12, 31)),
    ("heating", "市政热力碳排放因子", "0.1100", "kgCO2e/MJ", "范围二", date(2024, 1, 1), date(2026, 12, 31)),
    ("gasoline", "汽油碳排放因子", "2.9251", "kgCO2e/L", "范围一", date(2024, 1, 1), date(2026, 12, 31)),
    ("diesel", "柴油碳排放因子", "3.0959", "kgCO2e/L", "范围一", date(2024, 1, 1), date(2026, 12, 31)),
    ("pv", "光伏减排因子", "0.5703", "kgCO2e/kWh", "减排量", date(2024, 1, 1), date(2026, 12, 31)),
]

# ---------------------------------------------------------------- 通信协议

PROTOCOLS = [
    ("MODBUS_TCP", "Modbus TCP", "有线", "工业以太网 Modbus 协议，默认端口 502"),
    ("MODBUS_RTU", "Modbus RTU", "总线", "串口 Modbus 协议，RS485 总线"),
    ("MQTT", "MQTT", "物联网", "面向物联网的轻量消息协议，默认端口 1883"),
    ("BACNET_IP", "BACnet/IP", "楼宇自控", "楼宇自动化协议，默认端口 47808"),
    ("OPC_UA", "OPC UA", "工业", "工业统一架构协议，默认端口 4840"),
    ("HTTP_JSON", "HTTP/JSON", "物联网", "基于 HTTP 的 JSON 接口，默认端口 80"),
    ("IEC104", "IEC 104", "电力", "电力系统远动规约，默认端口 2404"),
]

# 协议参数：param_key, label, type, required, default, options
PROTOCOL_PARAMS = {
    "MODBUS_TCP": [
        ("ip", "设备 IP", "text", True, "192.168.1.100", None),
        ("port", "端口", "number", True, "502", None),
        ("slave_id", "从站地址", "number", True, "1", None),
        ("timeout", "超时(ms)", "number", False, "3000", None),
    ],
    "MODBUS_RTU": [
        ("serial_port", "串口号", "text", True, "COM1", None),
        ("baudrate", "波特率", "select", True, "9600", ["4800", "9600", "19200", "38400"]),
        ("parity", "校验位", "select", True, "N", ["N", "E", "O"]),
        ("slave_id", "从站地址", "number", True, "1", None),
    ],
    "MQTT": [
        ("broker", "Broker 地址", "text", True, "tcp://192.168.1.10", None),
        ("port", "端口", "number", True, "1883", None),
        ("client_id", "客户端 ID", "text", True, "gc-device-001", None),
        ("topic", "订阅主题", "text", True, "device/data", None),
        ("qos", "QoS", "select", True, "1", ["0", "1", "2"]),
    ],
    "BACNET_IP": [
        ("ip", "设备 IP", "text", True, "192.168.1.120", None),
        ("port", "端口", "number", True, "47808", None),
        ("device_id", "设备实例号", "number", True, "1001", None),
    ],
    "OPC_UA": [
        ("endpoint", "服务地址", "text", True, "opc.tcp://192.168.1.130:4840", None),
        ("username", "用户名", "text", False, "", None),
        ("password", "密码", "password", False, "", None),
    ],
    "HTTP_JSON": [
        ("base_url", "接口地址", "text", True, "http://192.168.1.140/api", None),
        ("token", "访问令牌", "password", False, "", None),
        ("interval", "推送间隔(s)", "number", False, "60", None),
    ],
    "IEC104": [
        ("ip", "设备 IP", "text", True, "192.168.1.150", None),
        ("port", "端口", "number", True, "2404", None),
        ("common_addr", "公共地址", "number", True, "1", None),
    ],
}

# ---------------------------------------------------------------- 设备类型（17 种）

DEVICE_TYPES = [
    ("DT_METER_E", "智能电表", "meter", "MODBUS_TCP", "Odometer"),
    ("DT_METER_W", "智能水表", "meter", "MODBUS_RTU", "Odometer"),
    ("DT_METER_G", "燃气表", "meter", "MODBUS_RTU", "Odometer"),
    ("DT_INVERTER", "光伏逆变器", "power", "MODBUS_TCP", "Sunny"),
    ("DT_STORAGE", "储能系统", "power", "MODBUS_TCP", "Coin"),
    ("DT_LIGHT_CTRL", "智能照明控制器", "control", "MQTT", "Sunny"),
    ("DT_CHILLER", "空调机组", "control", "BACNET_IP", "IceCream"),
    ("DT_AHU", "新风机组", "control", "BACNET_IP", "WindPower"),
    ("DT_ELEVATOR", "电梯监控终端", "control", "MODBUS_TCP", "Top"),
    ("DT_TEMP_HUMI", "温湿度传感器", "env", "MQTT", "Cloudy"),
    ("DT_CO2", "二氧化碳传感器", "env", "MQTT", "Cloudy"),
    ("DT_GATEWAY", "数据采集网关", "auxiliary", "HTTP_JSON", "Connection"),
    ("DT_POWER_CABINET", "配电柜监测装置", "meter", "MODBUS_TCP", "Grid"),
    ("DT_COMPRESSOR", "空气压缩机", "control", "OPC_UA", "Odometer"),
    ("DT_PUMP", "水泵", "control", "MODBUS_RTU", "Odometer"),
    ("DT_ENV_STATION", "环境监测仪", "env", "HTTP_JSON", "Cloudy"),
    ("DT_SOCKET", "智能插座", "control", "MQTT", "Plug"),
]

# ---------------------------------------------------------------- 系统参数

SYSTEM_PARAMS = [
    ("sys.name", "绿色低碳智慧管控系统", "系统名称", "basic", "平台展示名称"),
    ("sys.copyright", "Green Carbon Platform", "版权信息", "basic", "页面底部版权"),
    ("alarm.default_level", "major", "告警默认等级", "alarm", "新建规则默认等级"),
    ("alarm.auto_work_order", "true", "告警自动转工单", "alarm", "紧急告警是否自动生成工单"),
    ("data.retain_days", "365", "数据保留天数", "data", "历史数据保留天数"),
    ("data.collect_interval", "60", "默认采集间隔(秒)", "data", "设备默认采集周期"),
    ("login.fail_lock_times", "5", "登录失败锁定次数", "security", "连续失败达到次数后锁定"),
    ("login.lock_minutes", "15", "锁定时长(分钟)", "security", "账号锁定时长"),
    ("dashboard.refresh_sec", "30", "驾驶舱刷新间隔(秒)", "dashboard", "首页数据刷新周期"),
    ("report.default_type", "monthly", "默认报表周期", "report", "报表默认统计周期"),
]

# ---------------------------------------------------------------- 菜单树

MENU_TREE = [
    {
        "name": "数据驾驶舱", "type": "menu", "path": "/dashboard", "component": "dashboard/index",
        "icon": "Odometer", "perm": "dashboard:view",
        "children": [
            {"name": "查看", "type": "button", "perm": "dashboard:view"},
            {"name": "导出", "type": "button", "perm": "dashboard:export"},
        ],
    },
    {
        "name": "实时监控", "type": "dir", "path": "/monitor", "icon": "Monitor", "perm": "monitor:view",
        "children": [
            {"name": "实时监控总览", "type": "menu", "path": "/monitor/overview", "component": "monitor/overview/index", "perm": "monitor:overview:view"},
            {"name": "设备组态图", "type": "menu", "path": "/monitor/topology", "component": "monitor/topology/index", "perm": "monitor:topology:view"},
            {"name": "区域平面图", "type": "menu", "path": "/monitor/plan", "component": "monitor/plan/index", "perm": "monitor:plan:view"},
        ],
    },
    {
        "name": "设备接入", "type": "dir", "path": "/access", "icon": "Connection", "perm": "access:view",
        "children": [
            {"name": "接入向导", "type": "menu", "path": "/access/wizard", "component": "access/wizard/index", "perm": "access:wizard:view"},
            {"name": "批量导入", "type": "menu", "path": "/access/import", "component": "access/import/index", "perm": "access:import:view"},
            {"name": "接入记录", "type": "menu", "path": "/access/log", "component": "access/log/index", "perm": "access:log:view"},
            {"name": "新增设备", "type": "button", "perm": "access:device:add"},
            {"name": "编辑设备", "type": "button", "perm": "access:device:edit"},
            {"name": "删除设备", "type": "button", "perm": "access:device:delete"},
        ],
    },
    {
        "name": "测点与数据", "type": "dir", "path": "/point", "icon": "DataLine", "perm": "point:view",
        "children": [
            {"name": "测点管理", "type": "menu", "path": "/point/list", "component": "point/list/index", "perm": "point:list:view"},
            {"name": "采集任务配置", "type": "menu", "path": "/point/task", "component": "point/task/index", "perm": "point:task:view"},
            {"name": "历史数据查询", "type": "menu", "path": "/point/history", "component": "point/history/index", "perm": "point:history:view"},
            {"name": "数据补录", "type": "menu", "path": "/point/patch", "component": "point/patch/index", "perm": "point:patch:view"},
            {"name": "编辑测点", "type": "button", "perm": "point:list:edit"},
            {"name": "数据补录操作", "type": "button", "perm": "point:patch:edit"},
        ],
    },
    {
        "name": "设备管理", "type": "dir", "path": "/device", "icon": "OfficeBuilding", "perm": "device:view",
        "children": [
            {"name": "设备台账", "type": "menu", "path": "/device/list", "component": "device/list/index", "perm": "device:list:view"},
            {"name": "设备详情", "type": "menu", "path": "/device/detail", "component": "device/detail/index", "perm": "device:detail:view", "visible": False},
            {"name": "区域分组", "type": "menu", "path": "/device/area", "component": "device/area/index", "perm": "device:area:view"},
            {"name": "编辑设备", "type": "button", "perm": "device:list:edit"},
            {"name": "删除设备", "type": "button", "perm": "device:list:delete"},
        ],
    },
    {
        "name": "设备控制", "type": "dir", "path": "/control", "icon": "Aim", "perm": "control:view",
        "children": [
            {"name": "控制面板", "type": "menu", "path": "/control/panel", "component": "control/panel/index", "perm": "control:panel:view"},
            {"name": "定时任务", "type": "menu", "path": "/control/timed", "component": "control/timed/index", "perm": "control:timed:view"},
            {"name": "控制记录", "type": "menu", "path": "/control/record", "component": "control/record/index", "perm": "control:record:view"},
            {"name": "下发控制指令", "type": "button", "perm": "control:command:send"},
            {"name": "新增定时任务", "type": "button", "perm": "control:timed:add"},
        ],
    },
    {
        "name": "场景与联动", "type": "dir", "path": "/scene", "icon": "MagicStick", "perm": "scene:view",
        "children": [
            {"name": "场景管理", "type": "menu", "path": "/scene/list", "component": "scene/list/index", "perm": "scene:list:view"},
            {"name": "联动规则", "type": "menu", "path": "/scene/link-rule", "component": "scene/link-rule/index", "perm": "scene:link:view"},
            {"name": "执行记录", "type": "menu", "path": "/scene/exec-log", "component": "scene/exec-log/index", "perm": "scene:log:view"},
            {"name": "执行场景", "type": "button", "perm": "scene:list:exec"},
            {"name": "编辑规则", "type": "button", "perm": "scene:link:edit"},
        ],
    },
    {
        "name": "能耗管理", "type": "dir", "path": "/energy", "icon": "Lightning", "perm": "energy:view",
        "children": [
            {"name": "能耗总览", "type": "menu", "path": "/energy/overview", "component": "energy/overview/index", "perm": "energy:overview:view"},
            {"name": "能耗分析", "type": "menu", "path": "/energy/analysis", "component": "energy/analysis/index", "perm": "energy:analysis:view"},
            {"name": "分项计量", "type": "menu", "path": "/energy/item", "component": "energy/item/index", "perm": "energy:item:view"},
            {"name": "导出", "type": "button", "perm": "energy:export"},
        ],
    },
    {
        "name": "电价与费用", "type": "dir", "path": "/price", "icon": "Money", "perm": "price:view",
        "children": [
            {"name": "电价方案", "type": "menu", "path": "/price/plan", "component": "price/plan/index", "perm": "price:plan:view"},
            {"name": "费用统计", "type": "menu", "path": "/price/fee-stat", "component": "price/fee-stat/index", "perm": "price:stat:view"},
            {"name": "费用报表", "type": "menu", "path": "/price/report", "component": "price/report/index", "perm": "price:report:view"},
            {"name": "编辑方案", "type": "button", "perm": "price:plan:edit"},
        ],
    },
    {
        "name": "碳排放管理", "type": "dir", "path": "/carbon", "icon": "Cloudy", "perm": "carbon:view",
        "children": [
            {"name": "碳排总览", "type": "menu", "path": "/carbon/overview", "component": "carbon/overview/index", "perm": "carbon:overview:view"},
            {"name": "碳排放核算", "type": "menu", "path": "/carbon/accounting", "component": "carbon/accounting/index", "perm": "carbon:accounting:view"},
            {"name": "碳报告", "type": "menu", "path": "/carbon/report", "component": "carbon/report/index", "perm": "carbon:report:view"},
            {"name": "生成报告", "type": "button", "perm": "carbon:report:generate"},
        ],
    },
    {
        "name": "节能与定额", "type": "dir", "path": "/quota", "icon": "Histogram", "perm": "quota:view",
        "children": [
            {"name": "能耗定额", "type": "menu", "path": "/quota/list", "component": "quota/list/index", "perm": "quota:list:view"},
            {"name": "定额监控", "type": "menu", "path": "/quota/monitor", "component": "quota/monitor/index", "perm": "quota:monitor:view"},
            {"name": "考核报表", "type": "menu", "path": "/quota/assess", "component": "quota/assess/index", "perm": "quota:assess:view"},
            {"name": "编辑定额", "type": "button", "perm": "quota:list:edit"},
        ],
    },
    {
        "name": "告警与工单", "type": "dir", "path": "/alarm", "icon": "Bell", "perm": "alarm:view",
        "children": [
            {"name": "告警中心", "type": "menu", "path": "/alarm/center", "component": "alarm/center/index", "perm": "alarm:center:view"},
            {"name": "工单管理", "type": "menu", "path": "/alarm/work-order", "component": "alarm/work-order/index", "perm": "alarm:work-order:view"},
            {"name": "确认告警", "type": "button", "perm": "alarm:center:confirm"},
            {"name": "处理工单", "type": "button", "perm": "alarm:work-order:handle"},
        ],
    },
    {
        "name": "消息通知", "type": "dir", "path": "/notify", "icon": "ChatDotSquare", "perm": "notify:view",
        "children": [
            {"name": "消息列表", "type": "menu", "path": "/notify/message", "component": "notify/message/index", "perm": "notify:message:view"},
            {"name": "通知模板", "type": "menu", "path": "/notify/template", "component": "notify/template/index", "perm": "notify:template:view"},
            {"name": "通知渠道", "type": "menu", "path": "/notify/channel", "component": "notify/channel/index", "perm": "notify:channel:view"},
            {"name": "发送通知", "type": "button", "perm": "notify:message:send"},
        ],
    },
    {
        "name": "报表中心", "type": "dir", "path": "/report", "icon": "Document", "perm": "report:view",
        "children": [
            {"name": "报表中心", "type": "menu", "path": "/report/center", "component": "report/center/index", "perm": "report:center:view"},
            {"name": "报表订阅", "type": "menu", "path": "/report/subscribe", "component": "report/subscribe/index", "perm": "report:subscribe:view"},
            {"name": "生成报表", "type": "button", "perm": "report:center:generate"},
        ],
    },
    {
        "name": "基础配置中心", "type": "dir", "path": "/config", "icon": "SetUp", "perm": "config:view",
        "children": [
            {"name": "数据字典", "type": "menu", "path": "/config/dict", "component": "config/dict/index", "perm": "config:dict:view"},
            {"name": "碳因子管理", "type": "menu", "path": "/config/carbon-factor", "component": "config/carbon-factor/index", "perm": "config:factor:view"},
            {"name": "设备类型/协议", "type": "menu", "path": "/config/device-type", "component": "config/device-type/index", "perm": "config:device-type:view"},
            {"name": "编辑配置", "type": "button", "perm": "config:edit"},
        ],
    },
    {
        "name": "系统管理", "type": "dir", "path": "/system", "icon": "Setting", "perm": "system:view",
        "children": [
            {"name": "用户管理", "type": "menu", "path": "/system/user", "component": "system/user/index", "perm": "system:user:view"},
            {"name": "角色权限", "type": "menu", "path": "/system/role", "component": "system/role/index", "perm": "system:role:view"},
            {"name": "操作日志", "type": "menu", "path": "/system/oper-log", "component": "system/oper-log/index", "perm": "system:log:view"},
            {"name": "个人中心", "type": "menu", "path": "/system/profile", "component": "system/profile/index", "perm": "system:profile:view", "visible": False},
            {"name": "新增用户", "type": "button", "perm": "system:user:add"},
            {"name": "编辑用户", "type": "button", "perm": "system:user:edit"},
            {"name": "删除用户", "type": "button", "perm": "system:user:delete"},
            {"name": "重置密码", "type": "button", "perm": "system:user:reset"},
            {"name": "新增角色", "type": "button", "perm": "system:role:add"},
            {"name": "编辑角色", "type": "button", "perm": "system:role:edit"},
            {"name": "删除角色", "type": "button", "perm": "system:role:delete"},
        ],
    },
]

# 角色 -> 菜单路径前缀
ROLE_MENU_PREFIXES = {
    "admin": ["*"],
    "energy_admin": ["/dashboard", "/monitor/overview", "/energy", "/price", "/carbon", "/quota", "/report", "/notify", "/system/profile"],
    "ops": ["/dashboard", "/monitor", "/access", "/point", "/device", "/control", "/scene", "/alarm", "/notify", "/system/profile"],
    "viewer": ["/dashboard", "/monitor/overview", "/device/list", "/device/detail", "/report", "/notify/message", "/system/profile"],
}


async def _is_empty(session: AsyncSession, model) -> bool:
    count = (await session.execute(select(func.count()).select_from(model))).scalar_one()
    return count == 0


async def seed_roles(session: AsyncSession) -> int:
    if not await _is_empty(session, SysRole):
        return 0
    for code, name, desc, sort_no in ROLES:
        session.add(SysRole(role_code=code, role_name=name, description=desc, sort_no=sort_no, status=1))
    await session.commit()
    return len(ROLES)


async def seed_users(session: AsyncSession) -> int:
    if not await _is_empty(session, SysUser):
        return 0
    roles = {r.role_code: r.id for r in (await session.execute(select(SysRole))).scalars().all()}
    role_of = {"admin": "admin", "energy": "energy_admin", "ops": "ops", "viewer": "viewer"}
    for username, pwd, real_name, phone, email, dept in USERS:
        user = SysUser(
            username=username, password_hash=hash_password(pwd), real_name=real_name,
            phone=phone, email=email, dept_name=dept, status=1,
        )
        session.add(user)
        await session.flush()
        role_id = roles.get(role_of[username])
        if role_id:
            session.add(SysUserRole(user_id=user.id, role_id=role_id))
    await session.commit()
    return len(USERS)


async def seed_menus(session: AsyncSession) -> int:
    if not await _is_empty(session, SysMenu):
        return 0
    total = 0

    # 递归写入（dir/menu → button），通过 flush 获取父 id
    async def _walk(nodes: list[dict], parent_id: int | None) -> None:
        nonlocal total
        for idx, node in enumerate(nodes):
            menu = SysMenu(
                parent_id=parent_id,
                menu_name=node["name"],
                menu_type=node.get("type", "menu"),
                route_path=node.get("path"),
                component=node.get("component"),
                icon=node.get("icon"),
                perm_code=node.get("perm"),
                sort_no=idx + 1,
                visible=node.get("visible", True),
                status=1,
            )
            session.add(menu)
            await session.flush()
            total += 1
            if node.get("children"):
                await _walk(node["children"], menu.id)

    await _walk(MENU_TREE, None)
    await session.commit()
    return total


async def seed_role_menu(session: AsyncSession) -> int:
    if not await _is_empty(session, SysRoleMenu):
        return 0
    roles = {r.role_code: r.id for r in (await session.execute(select(SysRole))).scalars().all()}
    menus = list((await session.execute(select(SysMenu))).scalars().all())
    by_id = {m.id: m for m in menus}

    def _collect(prefixes: list[str]) -> set[int]:
        ids: set[int] = set()
        if "*" in prefixes:
            return {m.id for m in menus}
        for m in menus:
            if m.route_path and any(m.route_path == p or m.route_path.startswith(p + "/") for p in prefixes):
                ids.add(m.id)
        # 补全祖先
        for mid in list(ids):
            cur = by_id[mid]
            while cur.parent_id and cur.parent_id in by_id:
                ids.add(cur.parent_id)
                cur = by_id[cur.parent_id]
        # 补全按钮子节点
        for m in menus:
            if m.menu_type == "button" and m.parent_id in ids:
                ids.add(m.id)
        return ids

    count = 0
    for role_code, prefixes in ROLE_MENU_PREFIXES.items():
        role_id = roles.get(role_code)
        if not role_id:
            continue
        for menu_id in _collect(prefixes):
            session.add(SysRoleMenu(role_id=role_id, menu_id=menu_id))
            count += 1
    await session.commit()
    return count


async def seed_dict(session: AsyncSession) -> int:
    if not await _is_empty(session, CfgDictType):
        return 0
    count = 0
    for code, (name, items) in DICT_TYPES.items():
        dt = CfgDictType(type_code=code, type_name=name, remark=f"{name}字典", status=1)
        session.add(dt)
        await session.flush()
        for idx, (label, value) in enumerate(items):
            session.add(CfgDictItem(type_id=dt.id, item_label=label, item_value=value, sort_no=idx + 1, status=1))
            count += 1
    await session.commit()
    return count


async def seed_energy_types(session: AsyncSession) -> int:
    if not await _is_empty(session, CfgEnergyType):
        return 0
    for code, name, unit, sort_no in ENERGY_TYPES:
        session.add(CfgEnergyType(type_code=code, type_name=name, unit=unit, sort_no=sort_no, status=1))
    await session.commit()
    return len(ENERGY_TYPES)


async def seed_energy_items(session: AsyncSession) -> int:
    if not await _is_empty(session, CfgEnergyItem):
        return 0
    types = {t.type_code: t.id for t in (await session.execute(select(CfgEnergyType))).scalars().all()}
    pending = list(ENERGY_ITEMS)
    created: dict[str, int] = {}
    # 两轮处理，解决父子依赖
    for _ in range(2):
        for code, name, parent, energy_type, sort_no in pending:
            if code in created:
                continue
            if parent and parent not in created:
                continue
            item = CfgEnergyItem(
                item_code=code, item_name=name, parent_id=created.get(parent),
                energy_type_id=types.get(energy_type), sort_no=sort_no, status=1,
            )
            session.add(item)
            await session.flush()
            created[code] = item.id
    await session.commit()
    return len(created)


async def seed_carbon_factors(session: AsyncSession) -> int:
    if not await _is_empty(session, CfgCarbonFactor):
        return 0
    types = {t.type_code: t.id for t in (await session.execute(select(CfgEnergyType))).scalars().all()}
    for type_code, name, value, unit, scope, eff, exp in CARBON_FACTORS:
        session.add(
            CfgCarbonFactor(
                energy_type_id=types.get(type_code), factor_name=name, factor_value=value,
                factor_unit=unit, scope=scope, effective_date=eff, expire_date=exp, status=1,
            )
        )
    await session.commit()
    return len(CARBON_FACTORS)


async def seed_protocols(session: AsyncSession) -> int:
    if not await _is_empty(session, CfgProtocol):
        return 0
    count = 0
    for code, name, category, desc in PROTOCOLS:
        proto = CfgProtocol(protocol_code=code, protocol_name=name, category=category, description=desc, status=1)
        session.add(proto)
        await session.flush()
        count += 1
        for idx, (key, label, ptype, required, default, options) in enumerate(PROTOCOL_PARAMS.get(code, [])):
            session.add(
                CfgProtocolParam(
                    protocol_id=proto.id, param_key=key, param_label=label, param_type=ptype,
                    required=required, default_value=default, options=options, sort_no=idx + 1,
                )
            )
    await session.commit()
    return count


async def seed_device_types(session: AsyncSession) -> int:
    if not await _is_empty(session, CfgDeviceType):
        return 0
    protocols = {p.protocol_code: p.id for p in (await session.execute(select(CfgProtocol))).scalars().all()}
    for idx, (code, name, category, protocol_code, icon) in enumerate(DEVICE_TYPES):
        session.add(
            CfgDeviceType(
                type_code=code, type_name=name, category=category,
                default_protocol_id=protocols.get(protocol_code), icon=icon, sort_no=idx + 1, status=1,
            )
        )
    await session.commit()
    return len(DEVICE_TYPES)


async def seed_system_params(session: AsyncSession) -> int:
    if not await _is_empty(session, CfgSystemParam):
        return 0
    now = datetime.now().astimezone()
    for key, value, name, group, remark in SYSTEM_PARAMS:
        session.add(CfgSystemParam(param_key=key, param_value=value, param_name=name, param_group=group, remark=remark, updated_at=now))
    await session.commit()
    return len(SYSTEM_PARAMS)


async def seed_all(session: AsyncSession) -> dict[str, int]:
    """按依赖顺序初始化全部基础数据，返回各步写入条数。"""
    result: dict[str, int] = {}
    result["roles"] = await seed_roles(session)
    result["users"] = await seed_users(session)
    result["menus"] = await seed_menus(session)
    result["role_menu"] = await seed_role_menu(session)
    result["dict"] = await seed_dict(session)
    result["energy_types"] = await seed_energy_types(session)
    result["energy_items"] = await seed_energy_items(session)
    result["carbon_factors"] = await seed_carbon_factors(session)
    result["protocols"] = await seed_protocols(session)
    result["device_types"] = await seed_device_types(session)
    result["system_params"] = await seed_system_params(session)
    return result
