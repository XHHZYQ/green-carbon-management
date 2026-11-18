"""建表入口。"""

import asyncio

from app.db.session import create_db_and_tables


async def init_db() -> None:
    await create_db_and_tables()
    print("[init_db] 数据表创建完成")


if __name__ == "__main__":
    asyncio.run(init_db())
