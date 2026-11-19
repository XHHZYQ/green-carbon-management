"""建表 + 基础数据初始化入口。

用法：
    uv run python -m app.seed.run_seed
"""

import asyncio

from sqlalchemy import delete

from app.db.session import SessionLocal, create_db_and_tables
from app.models.ctrl import CtrlCommand, CtrlTimedTask
from app.models.scene import SceneAction, SceneExecLog, SceneInfo, SceneLinkRule, SceneSchedule
from app.seed.base_data import seed_all
from app.seed.control_data import seed_control_domain
from app.seed.device_data import seed_device_domain
from app.seed.scene_data import seed_scene_domain


async def _clear_dependents() -> None:
    """清理依赖设备的数据（控制、场景），避免重建设备时外键冲突。"""
    async with SessionLocal() as session:
        for model in (
            SceneExecLog, SceneLinkRule, SceneSchedule, SceneAction, SceneInfo,
            CtrlCommand, CtrlTimedTask,
        ):
            await session.execute(delete(model))
        await session.commit()


async def main() -> None:
    print("== 开始初始化数据库 ==")
    await create_db_and_tables()
    print("[1/5] 数据表创建/检查完成")

    async with SessionLocal() as session:
        result = await seed_all(session)
    print("[2/5] 基础数据初始化完成：")
    for key, value in result.items():
        print(f"    - {key}: 写入 {value} 条（已存在则跳过）")

    await _clear_dependents()
    async with SessionLocal() as session:
        dev_result = await seed_device_domain(session)
    print("[3/5] 设备域示例数据初始化完成：")
    for key, value in dev_result.items():
        print(f"    - {key}: 写入 {value} 条")

    async with SessionLocal() as session:
        ctrl_result = await seed_control_domain(session)
    print("[4/5] 控制域示例数据初始化完成：")
    for key, value in ctrl_result.items():
        print(f"    - {key}: 写入 {value} 条")

    async with SessionLocal() as session:
        scene_result = await seed_scene_domain(session)
    print("[5/5] 场景与联动域示例数据初始化完成：")
    for key, value in scene_result.items():
        print(f"    - {key}: 写入 {value} 条")
    print("== 初始化结束 ==")


if __name__ == "__main__":
    asyncio.run(main())
