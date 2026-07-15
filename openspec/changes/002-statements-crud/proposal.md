# Change Proposal 002: 三大报表录入与存储

> 对应 Phase 1。模式：Spec（新模块 + API 设计）。

## Why（为什么做）

Phase 0 仅建立了三大报表 ORM stub（代表性字段、无 API）。财务分析的核心数据载体是资产负债表 / 利润表 / 现金流量表；没有完整科目与 CRUD，后续比率分析与多期对比无法落地。

## What I Want（要什么）

1. **科目集合**：完整 CAS 简化版（资产负债表约 30 项、利润表约 18 项、现金流量表约 15 项），覆盖常用年报科目与 Phase 2 比率所需字段。
2. **报告期**：支持年报 + 季报，`(company_id, year, period_type, quarter)` 唯一；业务层强制年报 `quarter=null`、季报 `quarter∈{1,2,3,4}`。
3. **后端**：三表完整 ORM + schemas + services + REST CRUD，范式复刻 companies 切片。
4. **前端**：`StatementsView` 支持选企业、报表类型 Tab、报告期列表、分组表单录入/编辑/删除。
5. **文档与测试**：API 文档更新、pytest 覆盖 CRUD/校验/冲突/404、dev-log 追加。

## What I Know（已知）

- 分层铁律：`api → services → models`，schemas 校验边界。
- 比率不落库（Phase 2）；本期只做科目存储与 CRUD。
- 开发期 `create_all`；SQLite 扩列需处理（重建或补列）。
- 无认证、单机本地。

## What I Don't Know / 已决策

| 项 | 决策 |
|----|------|
| 科目口径 | **完整 CAS 简化版**（用户确认） |
| 报告期 | **年报 + 季报**（用户确认） |
| 迁移策略 | 开发期：启动时 `create_all` + SQLite 缺失列 `ALTER` 补齐；破坏性结构变更时提示重建 `data/finance.db` |
| 比率公式 | Phase 2，本期不实现 |
| Excel 导入 | Phase 4 |
