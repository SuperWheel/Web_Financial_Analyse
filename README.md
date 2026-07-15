# Web_Financial_Analyse

轻量级**企业财务报表分析系统**：三大报表录入、公开年报 PDF/Excel 导入、财务比率分析、科目级多期对比。单机本地运行，无认证。

## 功能概览

- 企业档案与三大报表（资产负债表 / 利润表 / 现金流量表）CRUD
- 年报 PDF 识别导入（CAS 主路径）+ 人审入库
- Excel 模板导入 / 导出（导出含财务比率）
- 巨潮资讯 A 股年报检索下载（代码或公司名称）
- 财务比率分析（趋势图、较上期变动、角色视图）
- 科目级多期对比看板（KPI、变动榜、可调坐标轴趋势图）

## 技术栈

| 层 | 选型 |
|----|------|
| 后端 | Python · FastAPI · SQLAlchemy · SQLite · pandas · openpyxl · pdfplumber |
| 前端 | Vue3 · TypeScript · Element Plus · ECharts · Vite |

## 快速开始

### 环境要求

- Python **3.10+**（推荐 3.12；`Mapped[int \| None]` 等注解需 3.10+）
- Node.js 18+（或 bun / pnpm）

### 一键启动 / 关闭（macOS）

双击根目录：

- `启动财务分析系统.command` → 启动后端 + 前端并打开页面  
- `关闭财务分析系统.command` → 停止本项目服务  

日志与 PID：`.runtime/`

### 手动启动

```bash
# 后端
cd backend
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 9000
```

```bash
# 前端（另开终端）
cd frontend
npm install                 # 或 bun install / pnpm install
npm run dev
```

| 服务 | 地址 |
|------|------|
| 前端 | http://127.0.0.1:5173 |
| 后端健康检查 | http://127.0.0.1:9000/api/health |
| API 文档 | http://127.0.0.1:9000/docs |

> 默认后端端口 **9000**（避开部分系统保留端口）。修改见 `backend/app/config.py` 与 `frontend/vite.config.ts` 代理。

## 目录结构

```
Web_Financial_Analyse/
├── AGENTS.md / CLAUDE.md     # 项目导航
├── openspec/                 # Spec 变更包
├── docs/                     # api / architecture / dev-log
├── backend/app/              # FastAPI：api → services → models
├── frontend/src/             # Vue3 视图与 API 封装
├── data/                     # SQLite 与导入文件（本地，默认不入库）
├── scripts/                  # start/stop-dev
└── 启动/关闭财务分析系统.command
```

## 测试

```bash
cd backend
source .venv/bin/activate
pytest -q
```

```bash
cd frontend
npm run type-check
# 或 bun run type-check
```

## 开发约定

- 分层：`api → services → models`，`schemas` 校验，`core` 横切
- 模式：小改 Vibe / 功能 Plan / 模块 Spec（见《AI Coding 开发规范参考文档》）
- 改动后追加 `docs/dev-log.md`

## 说明

- 本地 SQLite，**无多用户认证**
- 年报 PDF 样例目录 `年报参考/` 中的 PDF **默认不纳入 Git**（体积大）；可自行放入后通过「年报导入」使用
- 巨潮拉取请控制频率，遵守网站使用条款；仅支持 A 股主路径

## License

本项目默认以私有/本地使用为目的提供；若需开源协议可自行补充 `LICENSE`。
