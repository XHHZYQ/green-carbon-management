"""建表 + 基础数据初始化入口。

用法：
    uv run python -m app.seed.run_seed
"""

import asyncio

from app.db.session import SessionLocal, create_db_and_tables
from app.seed.base_data import seed_all


async def main() -> None:
    print("== 开始初始化数据库 ==")
    await create_db_and_tables()
    print("[1/2] 数据表创建/检查完成")

    async with SessionLocal() as session:
        result = await seed_all(session)
    print("[2/2] 基础数据初始化完成：")
    for key, value in result.items():
        print(f"    - {key}: 写入 {value} 条（已存在则跳过）")
    print("== 初始化结束 ==")


if __name__ == "__main__":
    asyncio.run(main())
