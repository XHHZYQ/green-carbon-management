# 绿色低碳智慧管控系统

面向园区 / 企业办公楼场景的绿色低碳智慧管控系统，提供设备接入、设备台账、远程控制、能耗监测、碳排放核算、告警运维与数据可视化能力。

## 目录结构

```
green-carbon/
├─ docs/        需求与设计文档
├─ scripts/     文档生成等辅助脚本
├─ backend/     后端工程（FastAPI + SQLModel + PostgreSQL）
└─ frontend/    前端工程（Vue 3 + TS + Vite + Element Plus + ECharts）
```

## 技术栈

- 后端：Python 3.12 + FastAPI + SQLModel（异步）+ asyncpg + APScheduler，依赖用 `uv` 管理
- 前端：Vue 3 + TypeScript + Vite + Element Plus + ECharts + Pinia + Vue Router，包管理器 `pnpm`
- 数据库：PostgreSQL

## 快速开始

### 后端

```bash
cd backend
uv sync                 # 安装依赖
cp .env.example .env    # 按需修改数据库连接
uv run python -m app.seed.run_seed   # 建表 + 基础数据
uv run uvicorn app.main:app --reload --port 8000
```

### 前端

```bash
cd frontend
pnpm install
pnpm dev
```

默认访问 http://localhost:5173 ，初始管理员账号见 `backend/app/seed/base_data.py`。
