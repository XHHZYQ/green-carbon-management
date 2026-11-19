"""诊断：检查各测点最近 1 小时是否有数据。"""

import asyncio
from datetime import datetime, timedelta

from sqlalchemy import func, select

from app.db.session import SessionLocal
from app.models.dev import DevData, DevPoint, DevDevice


async def main() -> None:
    now = datetime.now().astimezone()
    since = now - timedelta(hours=1)
    async with SessionLocal() as session:
        total_points = (await session.execute(select(func.count()).select_from(DevPoint))).scalar_one()
        total_data = (await session.execute(select(func.count()).select_from(DevData))).scalar_one()
        mx = (await session.execute(select(func.max(DevData.collect_time)))).scalar_one()
        mn = (await session.execute(select(func.min(DevData.collect_time)))).scalar_one()
        print(f"now         = {now:%Y-%m-%d %H:%M:%S}")
        print(f"points      = {total_points}")
        print(f"data rows   = {total_data}")
        print(f"data range  = {mn} ~ {mx}")

        # 最近 1 小时有数据的测点数
        rows = (
            await session.execute(
                select(DevData.point_id, func.count()).where(DevData.collect_time >= since).group_by(DevData.point_id)
            )
        ).all()
        print(f"近 1 小时有数据的测点数 = {len(rows)} / {total_points}")

        # 无数据测点示例（关联设备名）
        have = {pid for pid, _ in rows}
        pts = (await session.execute(select(DevPoint))).scalars().all()
        devs = {d.id: d.device_name for d in (await session.execute(select(DevDevice))).scalars().all()}
        missing = [p for p in pts if p.id not in have]
        print(f"近 1 小时无数据测点数 = {len(missing)}")
        for p in missing[:10]:
            last = (
                await session.execute(
                    select(func.max(DevData.collect_time)).where(DevData.point_id == p.id)
                )
            ).scalar_one()
            print(f"  - {devs.get(p.device_id)} / {p.point_name} 最后一条={last}")


if __name__ == "__main__":
    asyncio.run(main())
