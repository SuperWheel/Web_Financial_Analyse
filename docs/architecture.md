# 架构说明

> 本文档是架构总览入口，详细的技术决策记录在 Spec 变更包的 `design.md` 中。  
> 当前基线：**v1.0.0**（Phase 0–5 + 变更包 001–009 已交付）。

## 架构全景

```
前端 (Vite :5173)  ──/api 代理──▶  后端 (FastAPI :9000)  ──SQLAlchemy──▶  SQLite (data/finance.db)
   Vue3 + ElementPlus                  api → services → models
   + ECharts                           schemas 校验 / core 横切
   + Pinia
```

### 能力切片（按数据流）

```
录入 / 导入                         分析（只读、不落库）
─────────────────                   ──────────────────
手工 CRUD  ──┐                      ratio_service  → AnalysisView
Excel 导入 ──┼─▶ L1 三表 + L0 披露   compare_service → CompareView
PDF 导入  ──┤   (SQLite)            export_service  → .xlsx（含比率）
巨潮/URL ──┘
```

## 分层职责

| 层 | 目录 | 职责 | 禁止 |
|----|------|------|------|
| 路由 | `backend/app/api/` | 请求/响应转换、依赖注入 | 写业务逻辑、写 SQL |
| 业务 | `backend/app/services/` | 业务规则与编排 | 直接被前端调用 |
| 数据 | `backend/app/models/` | ORM 实体 | 写业务逻辑 |
| 校验 | `backend/app/schemas/` | Pydantic 请求/响应模型 | — |
| 横切 | `backend/app/core/` | 常量、比率公式、配置 | — |

### 主要后端切片对照

| 能力 | api | services | 备注 |
|------|-----|----------|------|
| 企业 | `companies.py` | `company_service.py` | 范式切片 |
| 三表 CRUD | `statements.py` | `statement_service.py` | L1 科目 |
| PDF 导入 | `imports.py` | `import_service` + `importing/*` | 人审后 commit |
| 在线拉取 | `fetch.py` | `fetching/*` | 下载后进 import job，不自动 commit |
| 比率 | `ratios.py` | `ratio_service.py` | 动态计算 |
| 多期对比 | `compare.py` | `compare_service.py` | 科目矩阵 |
| Excel 导出 | `export.py` | `export_service.py` | 含比率 sheet |
| Excel 导入 | `excel_io.py` | `excel_import_service.py` | 不导入比率 |
| L0 披露 | — | `disclosure_service.py` | commit 时写入 |

### 前端视图

| 路由视图 | 职责 |
|----------|------|
| `Dashboard.vue` | 企业档案 |
| `StatementsView.vue` | 三表录入 / 列表 |
| `ImportView.vue` | PDF / Excel / 巨潮在线拉取 + 人审 |
| `AnalysisView.vue` | 比率 KPI / 较上期 / 趋势 |
| `CompareView.vue` | 科目多期矩阵与趋势 |

## 数据模型要点

1. **报告期**：`(year, period_type, quarter)` 三元组。`period_type` = `annual` | `quarterly`；年报 `quarter` 必须为 `null`。
2. **L1 标准科目**：三表 ORM 列（CAS-simplified-v2），供比率与对比。
3. **L0 披露明细**：`statement_disclosure_lines` 保留年报原文行与映射关系；手工录入不强制写 L0。
4. **比率 / 对比结果不落库**：按公式或矩阵动态计算；Excel 导出时即时写入比率 sheet。
5. **同 `period_type` 内对比**：年报与季报不混比。

## 关键决策摘要

1. **单机无认证**（本地 SQLite）；API 全部本地公开。
2. **财务数字必须人审**：导入 job 默认 `review`，不自动 commit。
3. **CAS 主路径优先**：A 股数字 PDF + 词典映射；港股 / US GAAP / 难解析 PDF 为后续增强，不阻塞主路径。
4. **比率与对比只读动态算**：避免双写不一致；导出时物化到 Excel。
5. **开发代理**：Vite `/api` → `:9000`；后端端口默认 9000（避开部分系统保留段）。

## 变更包索引（001–010）

| 包 | 主题 | 状态 |
|----|------|------|
| 001 | 项目框架 | ✅ v1.0 |
| 002 | 三表 CRUD | ✅ |
| 003 | 公开年报 PDF 导入 | ✅ CAS 主路径；港股/EDGAR 待增强 |
| 004 | COA v2 + L0 披露层 | ✅ |
| 005 | 财务比率分析 | ✅ |
| 006 | 科目级多期对比 | ✅ |
| 007 | Excel 导出（含比率） | ✅ |
| 008 | Excel 模板导入 | ✅ |
| 009 | 年报在线拉取（URL + 巨潮） | ✅ |
| 010 | 巨潮批量多年拉取 | ✅（同步批，最多 12 年；不自动 commit） |

## Post-1.0 架构边界

- **批量拉取**：已复用 `fetching/*` + import job（010）；不引入 batch 任务表 / 异步队列。
- **港股 / EDGAR**：独立 extractor + 词典，经同一 import review 管道；勿污染 CAS 主路径。
- **体验修补**：优先前端与 `importing` 映射反馈，不改 L1 契约除非开 Spec。

## 详见

- [项目范围](../openspec/project.md)
- [Phase 0 架构决策](../openspec/changes/001-init-project/design.md)
- [Phase 1 报表科目与 API](../openspec/changes/002-statements-crud/design.md)
- [公开年报导入](../openspec/changes/003-public-filing-import/design.md)
- [COA v2 / L0](../openspec/changes/004-coa-v2-disclosure-layers/design.md)
- [比率](../openspec/changes/005-ratio-analysis/design.md)
- [多期对比](../openspec/changes/006-multi-period-compare/design.md)
- [Excel 导出 / 导入](../openspec/changes/007-excel-export/design.md) · [008](../openspec/changes/008-excel-import/design.md)
- [在线拉取](../openspec/changes/009-filing-fetch/design.md) · [批量多年 010](../openspec/changes/010-batch-filing-fetch/design.md)
- [API 文档](api.md)
- [开发日志](dev-log.md)
