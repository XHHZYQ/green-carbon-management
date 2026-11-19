"""设备域示例数据（B3-1）。

覆盖：区域分组、设备台账、连接参数、测点模板与测点、控制点、采集任务、
历史数据（近 7 天）、数据补录、接入记录。

用法：
    uv run python -m app.seed.run_seed
"""

import random
from datetime import datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cfg import CfgDeviceType, CfgProtocol
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
from app.models.sys import SysUser

random.seed(20260101)

# ---------------------------------------------------------------- 区域

AREAS = [
    # (编码, 名称, 类型, 上级编码, 排序)
    ("AREA_ROOT", "园区", "园区", None, 1),
    ("AREA_BLDG", "办公楼", "楼栋", "AREA_ROOT", 1),
    ("AREA_F1", "一层配电间", "房间", "AREA_BLDG", 1),
    ("AREA_F3", "三层空调机房", "房间", "AREA_BLDG", 2),
    ("AREA_SHOP", "生产车间", "楼栋", "AREA_ROOT", 2),
    ("AREA_SHOP_A", "车间A", "区域", "AREA_SHOP", 1),
    ("AREA_SHOP_B", "车间B", "区域", "AREA_SHOP", 2),
    ("AREA_PV", "光伏电站", "站点", "AREA_ROOT", 3),
    ("AREA_ESS", "储能站", "站点", "AREA_ROOT", 4),
]

# ---------------------------------------------------------------- 设备分组
# (类型编码, 区域编码, 安装位置, 数量, 名称前缀)

DEVICE_GROUPS = [
    ("DT_METER_E", "AREA_F1", "一层配电间", 4, "一层配电间智能电表"),
    ("DT_POWER_CABINET", "AREA_F1", "一层配电间", 2, "一层配电柜监测装置"),
    ("DT_GATEWAY", "AREA_F1", "一层配电间", 1, "一层配电间采集网关"),
    ("DT_CHILLER", "AREA_F3", "三层空调机房", 2, "三层空调机组"),
    ("DT_AHU", "AREA_F3", "三层空调机房", 2, "三层新风机组"),
    ("DT_TEMP_HUMI", "AREA_F3", "三层空调机房", 1, "三层温湿度传感器"),
    ("DT_GATEWAY", "AREA_F3", "三层空调机房", 1, "三层空调机房采集网关"),
    ("DT_METER_E", "AREA_SHOP_A", "车间A", 4, "车间A智能电表"),
    ("DT_COMPRESSOR", "AREA_SHOP_A", "车间A", 2, "车间A空气压缩机"),
    ("DT_PUMP", "AREA_SHOP_A", "车间A", 2, "车间A循环水泵"),
    ("DT_CO2", "AREA_SHOP_A", "车间A", 1, "车间A二氧化碳传感器"),
    ("DT_TEMP_HUMI", "AREA_SHOP_A", "车间A", 1, "车间A温湿度传感器"),
    ("DT_METER_E", "AREA_SHOP_B", "车间B", 3, "车间B智能电表"),
    ("DT_LIGHT_CTRL", "AREA_SHOP_B", "车间B", 6, "车间B智能照明控制器"),
    ("DT_SOCKET", "AREA_SHOP_B", "车间B", 2, "车间B智能插座"),
    ("DT_ELEVATOR", "AREA_SHOP_B", "车间B", 1, "车间B电梯监控终端"),
    ("DT_INVERTER", "AREA_PV", "光伏电站", 3, "光伏电站逆变器"),
    ("DT_ENV_STATION", "AREA_PV", "光伏电站", 1, "光伏电站环境监测仪"),
    ("DT_GATEWAY", "AREA_PV", "光伏电站", 1, "光伏电站采集网关"),
    ("DT_STORAGE", "AREA_ESS", "储能站", 2, "储能站储能系统"),
    ("DT_GATEWAY", "AREA_ESS", "储能站", 1, "储能站采集网关"),
]

# ---------------------------------------------------------------- 测点规格
# 类型编码 -> [(编码, 名称, 数据类型, 单位, 下限, 上限, 类型 measure/cumulative)]

POINT_SPECS = {
    "DT_METER_E": [
        ("VoltageA", "A相电压", "float", "V", 210, 240, "measure"),
        ("VoltageB", "B相电压", "float", "V", 210, 240, "measure"),
        ("VoltageC", "C相电压", "float", "V", 210, 240, "measure"),
        ("CurrentA", "A相电流", "float", "A", 0, 80, "measure"),
        ("ActivePower", "有功功率", "float", "kW", 0, 50, "measure"),
        ("ActiveEnergy", "正向有功电量", "float", "kWh", 0, 999999, "cumulative"),
    ],
    "DT_POWER_CABINET": [
        ("Voltage", "母线电压", "float", "V", 370, 400, "measure"),
        ("Current", "母线电流", "float", "A", 0, 300, "measure"),
        ("ActivePower", "有功功率", "float", "kW", 0, 200, "measure"),
        ("Temperature", "柜内温度", "float", "℃", 15, 45, "measure"),
    ],
    "DT_GATEWAY": [
        ("OnlineCnt", "在线设备数", "int", "个", 0, 60, "measure"),
        ("Signal", "信号强度", "int", "dBm", -90, -40, "measure"),
    ],
    "DT_CHILLER": [
        ("SupplyTemp", "供水温度", "float", "℃", 5, 12, "measure"),
        ("ReturnTemp", "回水温度", "float", "℃", 10, 18, "measure"),
        ("Power", "机组功率", "float", "kW", 0, 120, "measure"),
        ("RunStatus", "运行状态", "int", "", 0, 1, "measure"),
    ],
    "DT_AHU": [
        ("SupplyTemp", "送风温度", "float", "℃", 16, 26, "measure"),
        ("FanSpeed", "风机转速", "float", "rpm", 600, 1400, "measure"),
        ("Power", "机组功率", "float", "kW", 0, 15, "measure"),
    ],
    "DT_TEMP_HUMI": [
        ("Temperature", "环境温度", "float", "℃", 18, 32, "measure"),
        ("Humidity", "相对湿度", "float", "%RH", 35, 75, "measure"),
    ],
    "DT_COMPRESSOR": [
        ("AirPressure", "排气压力", "float", "MPa", 0.6, 1.0, "measure"),
        ("Temperature", "排气温度", "float", "℃", 60, 95, "measure"),
        ("Power", "运行功率", "float", "kW", 0, 75, "measure"),
        ("RunHours", "累计运行时长", "float", "h", 0, 99999, "cumulative"),
    ],
    "DT_PUMP": [
        ("Flow", "流量", "float", "m³/h", 0, 120, "measure"),
        ("Pressure", "出口压力", "float", "MPa", 0.2, 0.8, "measure"),
        ("Power", "功率", "float", "kW", 0, 30, "measure"),
    ],
    "DT_CO2": [
        ("CO2", "二氧化碳浓度", "float", "ppm", 400, 1500, "measure"),
        ("Temperature", "环境温度", "float", "℃", 18, 32, "measure"),
    ],
    "DT_LIGHT_CTRL": [
        ("Brightness", "亮度", "float", "%", 0, 100, "measure"),
        ("Power", "回路功率", "float", "kW", 0, 3, "measure"),
        ("Energy", "回路电量", "float", "kWh", 0, 99999, "cumulative"),
    ],
    "DT_SOCKET": [
        ("Power", "用电功率", "float", "kW", 0, 3.5, "measure"),
        ("Energy", "累计电量", "float", "kWh", 0, 9999, "cumulative"),
    ],
    "DT_ELEVATOR": [
        ("RunCount", "今日运行次数", "int", "次", 0, 600, "measure"),
        ("Load", "载重", "float", "kg", 0, 1000, "measure"),
    ],
    "DT_INVERTER": [
        ("DCVoltage", "直流电压", "float", "V", 500, 800, "measure"),
        ("ACPower", "交流功率", "float", "kW", 0, 100, "measure"),
        ("Frequency", "频率", "float", "Hz", 49.5, 50.5, "measure"),
        ("DailyEnergy", "当日发电量", "float", "kWh", 0, 600, "cumulative"),
        ("TotalEnergy", "累计发电量", "float", "kWh", 0, 9999999, "cumulative"),
    ],
    "DT_ENV_STATION": [
        ("Irradiance", "辐照度", "float", "W/m²", 0, 1000, "measure"),
        ("Temperature", "环境温度", "float", "℃", -10, 40, "measure"),
        ("WindSpeed", "风速", "float", "m/s", 0, 15, "measure"),
    ],
    "DT_STORAGE": [
        ("SOC", "荷电状态", "float", "%", 10, 95, "measure"),
        ("ChargePower", "充电功率", "float", "kW", 0, 200, "measure"),
        ("DischargePower", "放电功率", "float", "kW", 0, 200, "measure"),
        ("Voltage", "堆电压", "float", "V", 600, 900, "measure"),
    ],
}

# 测点模板（针对主要设备类型）
TEMPLATE_TYPES = ["DT_METER_E", "DT_INVERTER", "DT_CHILLER", "DT_PUMP", "DT_TEMP_HUMI"]

# 控制点规格：类型编码 -> [(编码, 名称, 类型, 下限, 上限, 危险)]
CONTROL_SPECS = {
    "DT_LIGHT_CTRL": [
        ("switch", "开关", "enum", 0, 1, False),
        ("brightness_set", "亮度设定", "number", 0, 100, False),
    ],
    "DT_SOCKET": [("switch", "开关", "enum", 0, 1, False)],
    "DT_PUMP": [
        ("switch", "启停", "enum", 0, 1, True),
        ("frequency", "频率设定", "number", 0, 50, True),
    ],
    "DT_CHILLER": [("setpoint", "温度设定", "number", 5, 15, False)],
}

ENUM_SWITCH = [{"label": "关", "value": 0}, {"label": "开", "value": 1}]

# 协议默认参数
PROTO_DEFAULTS = {
    "MODBUS_TCP": lambda ip, i: {"ip": ip, "port": "502", "slave_id": str(i), "timeout": "3000"},
    "MODBUS_RTU": lambda ip, i: {"serial_port": f"COM{i % 4 + 1}", "baudrate": "9600", "parity": "N", "slave_id": str(i)},
    "MQTT": lambda ip, i: {
        "broker": f"tcp://{ip}", "port": "1883", "client_id": f"gc-{i:03d}",
        "topic": f"device/{i}/data", "qos": "1",
    },
    "BACNET_IP": lambda ip, i: {"ip": ip, "port": "47808", "device_id": str(1000 + i)},
    "OPC_UA": lambda ip, i: {"endpoint": f"opc.tcp://{ip}:4840", "username": "admin", "password": "******"},
    "HTTP_JSON": lambda ip, i: {"base_url": f"http://{ip}/api", "interval": "60"},
    "IEC104": lambda ip, i: {"ip": ip, "port": "2404", "common_addr": "1"},
}


async def _reset(session: AsyncSession) -> None:
    """清理设备域数据（按外键依赖顺序）。"""
    for model in (
        DevDataPatch, DevData, DevAccessLog, DevCollectTask, DevControlPoint, DevPoint,
        DevPointTemplateItem, DevPointTemplate, DevDeviceConn, DevDevice, DevArea,
    ):
        await session.execute(delete(model))
    await session.commit()


def _gen_value(kind: str, lo: float, hi: float, hour: int, prev: float | None) -> float:
    """按类型生成贴近真实的值。"""
    if kind == "cumulative":
        step = (hi - lo) * 0.0002
        return round((prev if prev is not None else lo + random.uniform(100, 5000)) + random.uniform(0, step * 4), 3)
    mid = (lo + hi) / 2
    amp = (hi - lo) / 2 * 0.6
    hour_factor = 0.6 + 0.4 * (1 - abs(hour - 14) / 14)  # 白天偏高
    value = mid + amp * (hour_factor - 0.6) + random.uniform(-amp * 0.15, amp * 0.15)
    return round(min(max(value, lo), hi), 3)


async def seed_device_domain(session: AsyncSession) -> dict[str, int]:
    """写入设备域示例数据（先重置后写入）。"""
    await _reset(session)
    now = datetime.now().astimezone()
    result: dict[str, int] = {}

    types = {t.type_code: t for t in (await session.execute(select(CfgDeviceType))).scalars().all()}
    protos = {p.protocol_code: p for p in (await session.execute(select(CfgProtocol))).scalars().all()}
    proto_by_id = {p.id: code for code, p in protos.items()}
    admin = (await session.execute(select(SysUser).where(SysUser.username == "admin"))).scalars().first()
    operator_id = admin.id if admin else None

    # 区域
    area_map: dict[str, DevArea] = {}
    for code, name, atype, parent_code, sort_no in AREAS:
        area = DevArea(
            area_code=code, area_name=name, area_type=atype,
            parent_id=area_map[parent_code].id if parent_code else None, sort_no=sort_no, status=1,
        )
        session.add(area)
        await session.flush()
        area_map[code] = area
    result["areas"] = len(area_map)

    # 测点模板
    tpl_count = item_count = 0
    for type_code in TEMPLATE_TYPES:
        dt = types.get(type_code)
        tpl = DevPointTemplate(
            template_code=f"TPL_{type_code.replace('DT_', '')}",
            template_name=f"{dt.type_name}标准测点模板" if dt else type_code,
            device_type_id=dt.id if dt else None,
            description=f"{dt.type_name}默认测点集合" if dt else "",
            status=1,
        )
        session.add(tpl)
        await session.flush()
        tpl_count += 1
        for idx, (code, name, dtype, unit, lo, hi, _kind) in enumerate(POINT_SPECS[type_code]):
            session.add(DevPointTemplateItem(
                template_id=tpl.id, point_code=code, point_name=name, data_type=dtype,
                unit=unit, range_min=lo, range_max=hi, sort_no=idx + 1,
            ))
            item_count += 1
    result["point_templates"] = tpl_count
    result["point_template_items"] = item_count

    # 设备 + 连接参数 + 测点 + 控制点 + 采集任务
    devices: list[DevDevice] = []
    points: list[tuple[DevPoint, str]] = []
    dev_count = conn_count = point_count = ctrl_count = task_count = 0
    for type_code, area_code, location, num, name_prefix in DEVICE_GROUPS:
        dt = types.get(type_code)
        proto_code = proto_by_id.get(dt.default_protocol_id, "MODBUS_TCP") if dt else "MODBUS_TCP"
        proto = protos.get(proto_code)
        for i in range(1, num + 1):
            dev_count += 1
            seq = dev_count
            ip = f"192.168.1.{10 + seq}"
            online = random.random() > 0.15
            device = DevDevice(
                device_code=f"GC-{type_code.replace('DT_', '')}-{seq:03d}",
                device_name=f"{name_prefix}{i:02d}",
                device_type_id=dt.id if dt else None,
                area_id=area_map[area_code].id,
                protocol_id=proto.id if proto else None,
                install_location=location,
                status="normal",
                online_status="online" if online else "offline",
                access_time=now - timedelta(days=random.randint(30, 180)),
                last_online_time=now - timedelta(minutes=random.randint(1, 600)) if online else now - timedelta(days=3),
                remark=None,
            )
            session.add(device)
            await session.flush()
            devices.append(device)

            # 连接参数
            params = PROTO_DEFAULTS.get(proto_code, PROTO_DEFAULTS["MODBUS_TCP"])(ip, seq)
            for k, v in params.items():
                session.add(DevDeviceConn(device_id=device.id, param_key=k, param_value=str(v)))
                conn_count += 1

            # 测点
            for idx, (code, name, dtype, unit, lo, hi, kind) in enumerate(POINT_SPECS.get(type_code, [])):
                pt = DevPoint(
                    device_id=device.id, point_code=code, point_name=name, data_type=dtype,
                    unit=unit, range_min=lo, range_max=hi, point_type="collect", sort_no=idx + 1, status=1,
                )
                session.add(pt)
                points.append((pt, kind))
                point_count += 1

            # 控制点
            for idx, (code, name, ptype, lo, hi, dangerous) in enumerate(CONTROL_SPECS.get(type_code, [])):
                session.add(DevControlPoint(
                    device_id=device.id, point_key=code, point_name=name, point_type=ptype,
                    value_min=lo, value_max=hi, enum_options=ENUM_SWITCH if ptype == "enum" else None,
                    dangerous=dangerous, sort_no=idx + 1, status=1,
                ))
                ctrl_count += 1

            # 采集任务
            session.add(DevCollectTask(
                device_id=device.id, task_name=f"{device.device_name}采集任务", collect_mode="period",
                period_sec=60, range_desc="全天", enable_status=1 if online else 0,
                last_run_time=now - timedelta(minutes=random.randint(1, 5)),
            ))
            task_count += 1
    await session.flush()
    result["devices"] = dev_count
    result["device_conns"] = conn_count
    result["points"] = point_count
    result["control_points"] = ctrl_count
    result["collect_tasks"] = task_count

    # 历史数据（近 7 天，每小时一条）
    hours = 24 * 7
    data_count = patch_count = 0
    patch_candidates: list[DevData] = []
    batch: list[DevData] = []
    start = (now - timedelta(hours=hours - 1)).replace(minute=0, second=0, microsecond=0)
    for pt, kind in points:
        prev = None
        for h in range(hours):
            ts = start + timedelta(hours=h)
            value = _gen_value(kind, float(pt.range_min or 0), float(pt.range_max or 100), ts.hour, prev)
            prev = value
            quality = "normal"
            roll = random.random()
            if roll < 0.004:
                quality = "missing"
            elif roll < 0.007:
                quality = "abnormal"
            row = DevData(
                device_id=pt.device_id, point_id=pt.id, collect_value=value,
                unit=pt.unit, data_quality=quality, collect_time=ts,
            )
            batch.append(row)
            data_count += 1
            if quality == "abnormal" and len(patch_candidates) < 3:
                patch_candidates.append(row)
        if len(batch) >= 4000:
            session.add_all(batch)
            await session.flush()
            batch = []
    if batch:
        session.add_all(batch)
        await session.flush()
    result["data"] = data_count

    # 数据补录（选择若干异常数据补录）
    for row in patch_candidates:
        patch_value = round(float(row.collect_value or 0) * 0.98, 3)
        session.add(DevDataPatch(
            data_id=row.id, patch_value=patch_value, reason="仪表异常，人工补录",
            operator_id=operator_id, patched_at=row.collect_time,
        ))
        row.collect_value = patch_value
        row.data_quality = "patched"
        session.add(row)
        patch_count += 1
    result["data_patches"] = patch_count

    # 接入记录
    log_count = 0
    for device in devices:
        session.add(DevAccessLog(
            device_id=device.id, action="接入",
            result="成功", message="设备接入并上线成功" if device.online_status == "online" else "设备接入成功（未上线）",
            operator_id=operator_id, cost_ms=random.randint(60, 260), access_time=device.access_time,
        ))
        log_count += 1
        if random.random() < 0.3:
            online = random.random() > 0.5
            session.add(DevAccessLog(
                device_id=device.id, action="上线" if online else "下线",
                result="成功", message="设备已上线" if online else "设备已下线",
                operator_id=operator_id, cost_ms=random.randint(40, 180),
                access_time=now - timedelta(days=random.randint(1, 20)),
            ))
            log_count += 1
    session.add(DevAccessLog(
        device_id=None, action="批量导入", result="成功",
        message="成功 12 条，失败 0 条", operator_id=operator_id, cost_ms=1860,
        access_time=now - timedelta(days=15),
    ))
    log_count += 1
    result["access_logs"] = log_count

    await session.commit()
    return result
