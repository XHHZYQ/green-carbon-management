"""建表 + 基础数据初始化入口。

用法：
    uv run python -m app.seed.run_seed
"""

import asyncio

from sqlalchemy import delete

from app.db.session import SessionLocal, create_db_and_tables
from app.models.alarm import AlarmInfo, AlarmRule
from app.models.carbon import CarbonEmission, CarbonReport
from app.models.ctrl import CtrlCommand, CtrlTimedTask
from app.models.energy import EnergyFeeStat, EnergyPriceHistory, EnergyPricePeriod, EnergyPricePlan, EnergyStat
from app.models.notify import NotifyChannel, NotifyMessage, NotifyRule, NotifySendLog, NotifyTemplate
from app.models.quota import EnergyQuota, QuotaAssess, QuotaMonitor
from app.models.report import ReportRecord, ReportSubscribe, ReportTemplate
from app.models.scene import SceneAction, SceneExecLog, SceneInfo, SceneLinkRule, SceneSchedule
from app.models.wo import WoWorkOrder
from app.seed.alarm_data import seed_alarm_domain
from app.seed.base_data import seed_all
from app.seed.carbon_data import seed_carbon_domain
from app.seed.control_data import seed_control_domain
from app.seed.device_data import seed_device_domain
from app.seed.energy_data import seed_energy_domain
from app.seed.notify_data import seed_notify_domain
from app.seed.price_data import seed_price_domain
from app.seed.quota_data import seed_quota_domain
from app.seed.report_data import seed_report_domain
from app.seed.scene_data import seed_scene_domain


async def _clear_dependents() -> None:
    """清理依赖设备的数据（能耗/费用/碳排、控制、场景、告警/工单、定额），避免重建设备时外键冲突。"""
    async with SessionLocal() as session:
        for model in (
            ReportRecord, ReportSubscribe, ReportTemplate,
            CarbonReport, CarbonEmission,
            EnergyFeeStat, EnergyPriceHistory, EnergyPricePeriod, EnergyPricePlan, EnergyStat,
            SceneExecLog, SceneLinkRule, SceneSchedule, SceneAction, SceneInfo,
            CtrlCommand, CtrlTimedTask,
            WoWorkOrder, AlarmInfo, AlarmRule,
            QuotaAssess, QuotaMonitor, EnergyQuota,
            NotifySendLog, NotifyMessage, NotifyRule, NotifyTemplate, NotifyChannel,
        ):
            await session.execute(delete(model))
        await session.commit()


async def _print_section(title: str, result: dict[str, int]) -> None:
    print(title)
    for key, value in result.items():
        print(f"    - {key}: 写入 {value} 条")


async def main() -> None:
    print("== 开始初始化数据库 ==")
    await create_db_and_tables()
    print("[1/12] 数据表创建/检查完成")

    async with SessionLocal() as session:
        result = await seed_all(session)
    print("[2/12] 基础数据初始化完成：")
    for key, value in result.items():
        print(f"    - {key}: 写入 {value} 条（已存在则跳过）")

    await _clear_dependents()
    async with SessionLocal() as session:
        dev_result = await seed_device_domain(session)
    await _print_section("[3/12] 设备域示例数据初始化完成：", dev_result)

    async with SessionLocal() as session:
        ctrl_result = await seed_control_domain(session)
    await _print_section("[4/12] 控制域示例数据初始化完成：", ctrl_result)

    async with SessionLocal() as session:
        scene_result = await seed_scene_domain(session)
    await _print_section("[5/12] 场景与联动域示例数据初始化完成：", scene_result)

    async with SessionLocal() as session:
        energy_result = await seed_energy_domain(session)
    await _print_section("[6/12] 能耗域示例数据初始化完成：", energy_result)

    async with SessionLocal() as session:
        price_result = await seed_price_domain(session)
    await _print_section("[7/12] 电价与费用域示例数据初始化完成：", price_result)

    async with SessionLocal() as session:
        carbon_result = await seed_carbon_domain(session)
    await _print_section("[8/12] 碳排域示例数据初始化完成：", carbon_result)

    async with SessionLocal() as session:
        notify_result = await seed_notify_domain(session)
    await _print_section("[9/12] 消息通知域示例数据初始化完成：", notify_result)

    async with SessionLocal() as session:
        alarm_result = await seed_alarm_domain(session)
    await _print_section("[10/12] 告警与工单域示例数据初始化完成：", alarm_result)

    async with SessionLocal() as session:
        quota_result = await seed_quota_domain(session)
    await _print_section("[11/12] 节能定额域示例数据初始化完成：", quota_result)

    async with SessionLocal() as session:
        report_result = await seed_report_domain(session)
    await _print_section("[12/12] 报表域示例数据初始化完成：", report_result)

    print("== 初始化结束 ==")


if __name__ == "__main__":
    asyncio.run(main())
