"""建表 + 基础数据初始化入口。

用法：
    uv run python -m app.seed.run_seed
"""

import asyncio

from app.db.session import SessionLocal, create_db_and_tables
from app.seed.base_data import seed_all
from app.seed.control_data import seed_control_domain
from app.seed.device_data import seed_device_domain


async def main() -> None:
    print("== 开始初始化数据库 ==")
    await create_db_and_tables()
    print("[1/4] 数据表创建/检查完成")

    async with SessionLocal() as session:
        result = await seed_all(session)
    print("[2/4] 基础数据初始化完成：")
    for key, value in result.items():
        print(f"    - {key}: 写入 {value} 条（已存在则跳过）")

    async with SessionLocal() as session:
        dev_result = await seed_device_domain(session)
    print("[3/4] 设备域示例数据初始化完成：")
    for key, value in dev_result.items():
        print(f"    - {key}: 写入 {value} 条")

    async with SessionLocal() as session:
        ctrl_result = await seed_control_domain(session)
    print("[4/4] 控制域示例数据初始化完成：")
    for key, value in ctrl_result.items():
        print(f"    - {key}: 写入 {value} 条")
    print("== 初始化结束 ==")


if __name__ == "__main__":
    asyncio.run(main())
