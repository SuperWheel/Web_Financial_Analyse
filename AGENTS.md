# AGENTS.md —— Web_Financial_Analyse 财务分析系统

> 本文件是项目的**导航地图**，遵循《AI Coding 开发规范》地图式导航原则——只指路、不含全部细节。详细内容请跟随链接到对应文档。

## 一句话简介

轻量级**企业财务报表分析系统**：录入三大报表、计算财务比率、多期对比，单机本地运行。

## 技术栈

- **后端**：Python + FastAPI + SQLAlchemy + SQLite + pandas（见 `backend/requirements.txt`）
- **前端**：Vue3 + TypeScript + Element Plus + ECharts + Vite（见 `frontend/package.json`）
- **形态**：单机本地，无认证，SQLite 落地于 `data/finance.db`

## 目录结构（地图）

```
Web_Financial_Analyse/
├── AGENTS.md            ← 你在这里（导航地图）
├── openspec/            ← Spec 模式产物（架构变更在此发起）
│   ├── project.md         项目背景与范围
│   ├── AGENTS.md          AI 协作约定（分层铁律、命名、自检清单）
│   └── changes/           每个变更包一个目录（proposal/spec/design/tasks）
├── docs/                ← 开发文档
│   ├── dev-log.md         开发日志（每次对话后追加）
│   ├── architecture.md    架构说明
│   └── api.md             API 文档
├── backend/             ← FastAPI 后端
│   └── app/
│       ├── api/           路由层（只做转换/注入）
│       ├── services/      业务层（规则/编排）
│       ├── models/        数据层（ORM）
│       ├── schemas/       边界校验（Pydantic）
│       └── core/          常量/公式/配置
├── frontend/            ← Vue3 前端
│   └── src/{views,layouts,stores,api,router}
└── data/                ← SQLite 数据文件落地处
```

## 开发规范（摘要，完整版见 `openspec/AGENTS.md`）

- **分层铁律**：`api → services → models`，`schemas` 校验边界，`core` 放横切。禁止越层。
- **三金律**：先对齐再动手 / 小步快跑步步验证 / 文档即副产品。
- **模式选择**：小改 Vibe、功能 Plan、模块/架构 Spec（详见根目录《AI Coding 开发规范参考文档》）。
- **改动后**：必须追加 `docs/dev-log.md`。

## 当前状态

- ✅ Phase 0：项目框架已建立。
- ✅ Phase 1：三大报表录入与存储（变更包 002）+ 会计表格式 UI。
- ✅ Phase 2：公开年报导入（变更包 003：PDF 识别映射 + 人审入库；CAS 主路径已通）。
- ✅ 变更包 004：CAS-simplified-v2 标准科目扩列 + L0 披露明细层 + 别名/rollup。
- ✅ Phase 3：财务比率分析与可视化（变更包 005）。
- ✅ Phase 4：科目级多期对比（变更包 006）。
- ✅ Phase 5：Excel 导出/导入（007/008）；年报在线拉取 URL+巨潮（009）。港股/EDGAR 与批量任务待增强。

## 启动方式

```bash
# 后端
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 9000   # http://127.0.0.1:9000

# 前端（另开终端）
cd frontend
npm install
npm run dev                             # http://127.0.0.1:5173
```

## 关键参考（深入阅读入口）

- 架构与技术决策：[[openspec/changes/001-init-project/design.md]] / [[openspec/changes/002-statements-crud/design.md]]
- 需求规格：[[openspec/changes/001-init-project/spec.md]]
- 项目范围：[[openspec/project.md]]
- 协作约定：[[openspec/AGENTS.md]]
- 开发规范总纲：[[AI Coding 开发规范参考文档.md]]

## 前端开发范式参照

- 视图组件：`frontend/src/views/Dashboard.vue`、`StatementsView.vue`、`AnalysisView.vue`、`CompareView.vue`
- 状态管理：`frontend/src/stores/{company,statement}.ts`
- API 封装：`frontend/src/api/{http,company,statement,ratio,compare}.ts`
- 科目元数据：`frontend/src/constants/statementFields.ts`
- 路由：`frontend/src/router/index.ts`

## 后端开发范式参照

- 企业切片：`api/companies.py` → `services/company_service.py` → `models/company.py` → `schemas/company.py`
- 报表切片：`api/statements.py` → `services/statement_service.py` → `models/{balance_sheet,income_statement,cash_flow}.py` → `schemas/statement.py`
- 比率/对比：`api/{ratios,compare}.py` → `services/{ratio,compare}_service.py` → `schemas/{ratio,compare}.py`（只读，不落库）

新增功能请按上述范式复刻分层。
