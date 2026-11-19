"""建表 + 基础数据初始化入口。

用法：
    uv run python -m app.seed.run_seed
"""

import asyncio

from sqlalchemy import delete

from app.db.session import SessionLocal, create_db_and_tables
from app.models.carbon import CarbonEmission, CarbonReport
from app.models.ctrl import CtrlCommand, CtrlTimedTask
from app.models.energy import EnergyFeeStat, EnergyPriceHistory, EnergyPricePeriod, EnergyPricePlan, EnergyStat
from app.models.scene import SceneAction, SceneExecLog, SceneInfo, SceneLinkRule, SceneSchedule
from app.seed.base_data import seed_all
from app.seed.carbon_data import seed_carbon_domain
from app.seed.control_data import seed_control_domain
from app.seed.device_data import seed_device_domain
from app.seed.energy_data import seed_energy_domain
from app.seed.price_data import seed_price_domain
from app.seed.scene_data import seed_scene_domain


async def _clear_dependents() -> None:
    """清理依赖设备的数据（能耗/费用/碳排、控制、场景），避免重建设备时外键冲突。"""
    async with SessionLocal() as session:
        for model in (
            CarbonReport, CarbonEmission,
            EnergyFeeStat, EnergyPriceHistory, EnergyPricePeriod, EnergyPricePlan, EnergyStat,
            SceneExecLog, SceneLinkRule, SceneSchedule, SceneAction, SceneInfo,
            CtrlCommand, CtrlTimedTask,
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
    print("[1/8] 数据表创建/检查完成")

    async with SessionLocal() as session:
        result = await seed_all(session)
    print("[2/8] 基础数据初始化完成：")
    for key, value in result.items():
        print(f"    - {key}: 写入 {value} 条（已存在则跳过）")

    await _clear_dependents()
    async with SessionLocal() as session:
        dev_result = await seed_device_domain(session)
    await _print_section("[3/8] 设备域示例数据初始化完成：", dev_result)

    async with SessionLocal() as session:
        ctrl_result = await seed_control_domain(session)
    await _print_section("[4/8] 控制域示例数据初始化完成：", ctrl_result)

    async with SessionLocal() as session:
        scene_result = await seed_scene_domain(session)
    await _print_section("[5/8] 场景与联动域示例数据初始化完成：", scene_result)

    async with SessionLocal() as session:
        energy_result = await seed_energy_domain(session)
    await _print_section("[6/8] 能耗域示例数据初始化完成：", energy_result)

    async with SessionLocal() as session:
        price_result = await seed_price_domain(session)
    await _print_section("[7/8] 电价与费用域示例数据初始化完成：", price_result)

    async with SessionLocal() as session:
        carbon_result = await seed_carbon_domain(session)
    await _print_section("[8/8] 碳排域示例数据初始化完成：", carbon_result)

    print("== 初始化结束 ==")


if __name__ == "__main__":
    asyncio.run(main())
