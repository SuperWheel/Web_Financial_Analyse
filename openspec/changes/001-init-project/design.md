# Design 001: 架构与技术决策

## 1. 整体架构

```
┌─────────────────────────────────────────────┐
│  前端 (frontend/, Vite dev: :5173)          │
│  Vue3 + ElementPlus + ECharts               │
│  开发态通过 /api 代理 → 后端                 │
└──────────────────┬──────────────────────────┘
                   │ HTTP /api/*
┌──────────────────▼──────────────────────────┐
│  后端 (backend/, uvicorn: :9000)            │
│  FastAPI                                    │
│  ┌─────────────────────────────────────┐    │
│  │ api/   路由层 (只做转换/注入)        │    │
│  │   ↓                                 │    │
│  │ services/ 业务层 (规则/编排)         │    │
│  │   ↓                                 │    │
│  │ models/  数据层 (SQLAlchemy ORM)     │    │
│  └─────────────────────────────────────┘    │
│  schemas/ 边界校验 (Pydantic)               │
│  core/   常量/公式/配置                     │
└──────────────────┬──────────────────────────┘
                   │ SQLAlchemy
┌──────────────────▼──────────────────────────┐
│  data/finance.db  (SQLite 单文件)           │
└─────────────────────────────────────────────┘
```

## 2. 关键设计决策

### 决策 1：后端分层架构
- **选择**：`api → services → models`，外加 `schemas`（Pydantic）与 `core`（横切）。
- **理由**：财务分析逻辑（比率计算、多期对比）天然复杂，分层避免业务逻辑散落到路由里，便于测试与维护。
- **范式**：由 `companies` 切片确立，后续模块照抄。

### 决策 2：单机无认证
- **选择**：不引入用户/权限/会话。
- **理由**：定位为单机本地工具，认证是过度设计。SQLite 文件落在本地 `data/finance.db`。
- **后果**：API 全部公开；后续若要 Web 化，再以独立变更包引入。

### 决策 3：比率计算不落库
- **选择**：三大报表的**会计科目**存表，财务比率**按公式动态计算**（pandas）。
- **理由**：比率是科目的派生值，落库会引入冗余与一致性问题；动态算保证始终与原始数据一致。
- **实现**：`core/constants.py` 集中定义比率公式（分子/分母对应的科目字段）。

### 决策 4：报告期建模
- **选择**：用 `(year, period_type, quarter)` 三元组标识一期报表。
  - `period_type ∈ {annual, quarterly}`
  - `quarter` 仅季报有效（1/2/3/4），年报为 NULL。
- **理由**：兼容年报与季报，天然支持多期对比。每张报表表设 `UNIQUE(company_id, year, period_type, quarter)`。

### 决策 5：前端开发代理
- **选择**：Vite dev server 代理 `/api` → `:9000`。
- **理由**：开发态零跨域配置；生产态可由 FastAPI 托管 `frontend/dist` 静态资源（后续 Phase 决定是否启用）。
- **端口说明**：后端默认 9000，避开 Windows Hyper-V 保留端口范围（7985–8084 / 8134–8233 会排除常见的 8000/8080，导致 bind 报 Errno 13）。端口集中配置于 `backend/app/config.py` 的 `BACKEND_PORT`。

### 决策 6：TypeScript
- **选择**：前端使用 TypeScript。
- **理由**：财务数据强类型能减少字段拼写类 bug；ElementPlus / ECharts 对 TS 支持良好。

## 3. 数据模型（本期实现 + 占位）

### 本期实现

**Company（企业）**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | 主键 |
| name | String(200) | 企业名称，必填非空 |
| code | String(50) | 股票代码/统一编号，唯一（可空） |
| industry | String(100) | 所属行业（可空） |
| created_at | DateTime | 创建时间，默认 now |

### 本期占位（建表，不开 API）

**BalanceSheet / IncomeStatement / CashFlowStatement**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | 主键 |
| company_id | FK→companies.id | 企业外键 |
| year | Integer | 年份 |
| period_type | String | annual / quarterly |
| quarter | Integer NULL | 季报季度 |
| + 科目字段 | Numeric | 各表特有，本期仅放代表性字段 |

约束：`UNIQUE(company_id, year, period_type, quarter)`。

## 4. 目录树（完整）

见 proposal.md / CLAUDE.md。本 design 不重复展开。

## 5. 依赖清单

### 后端（backend/requirements.txt）
- `fastapi`、`uvicorn[standard]` —— Web
- `sqlalchemy` —— ORM
- `pydantic` —— 校验（随 FastAPI）
- `pandas` —— 多期计算（本期引入，供后续使用）
- `openpyxl` —— Excel（后续阶段使用，提前引入便于 Phase 4）
- `python-multipart` —— 文件上传（后续 Excel 导入用）
- dev：`pytest`、`httpx`

### 前端（frontend/package.json）
- runtime：`vue@3`、`vue-router`、`pinia`、`element-plus`、`echarts`、`vue-echarts`、`axios`
- dev：`vite`、`@vitejs/plugin-vue`、`typescript`、`vue-tsc`、`@types/node`

## 6. 风险与权衡

- **SQLite 并发**：单机足够；若未来 Web 化需换 Postgres，分层架构使迁移成本可控。
- **科目口径**：本期报表表仅放代表性字段，完整科目集留到 Phase 1 与用户确认后细化（可能涉及字段迁移）。
