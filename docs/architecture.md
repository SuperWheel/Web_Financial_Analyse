# 架构说明

> 本文档是架构总览入口，详细的技术决策记录在 Spec 变更包的 `design.md` 中。

## 架构全景

```
前端 (Vite :5173)  ──/api 代理──▶  后端 (FastAPI :9000)  ──SQLAlchemy──▶  SQLite (data/finance.db)
   Vue3 + ElementPlus                  api → services → models
   + ECharts                           schemas 校验 / core 横切
```

## 分层职责

| 层 | 目录 | 职责 | 禁止 |
|----|------|------|------|
| 路由 | `backend/app/api/` | 请求/响应转换、依赖注入 | 写业务逻辑、写 SQL |
| 业务 | `backend/app/services/` | 业务规则与编排 | 直接被前端调用 |
| 数据 | `backend/app/models/` | ORM 实体 | 写业务逻辑 |
| 校验 | `backend/app/schemas/` | Pydantic 请求/响应模型 | — |
| 横切 | `backend/app/core/` | 常量、比率公式、配置 | — |

## 关键决策摘要

1. 单机无认证（本地 SQLite）。
2. 比率与多期对比结果均不落库，按公式/矩阵动态计算（pandas 可用于比率；对比矩阵为纯 Python）。
3. 报告期用 `(year, period_type, quarter)` 三元组，支持年报/季报与多期对比（同 `period_type` 内环比）。

详见：
- [Phase 0 架构决策](../openspec/changes/001-init-project/design.md)
- [Phase 1 报表科目与 API](../openspec/changes/002-statements-crud/design.md)
- [项目范围](../openspec/project.md)
- [开发日志](dev-log.md)
- [API 文档](api.md)
