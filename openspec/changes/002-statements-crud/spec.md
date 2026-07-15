# Spec 002: 三大报表录入与存储

> ADDED 风格描述本变更新增需求。仅约束 Phase 1；比率/多期/Excel 不在范围。

## ADDED 需求

### ADDED-1：完整 CAS 简化版科目模型

- **要求**：扩展 `BalanceSheet` / `IncomeStatement` / `CashFlowStatement` 至 design.md 定义的完整字段集；金额字段 `Numeric(18,2)` 可空（允许分步录入）。
- **要求**：保留 `UNIQUE(company_id, year, period_type, quarter)`；业务层额外保证年报 `quarter is null`、季报 `quarter in 1..4`，并拦截同企业同报告期重复。
- **验收**：`Base.metadata.create_all` 可建表；模型字段与 design 科目表一致。

### ADDED-2：报告期校验

- **要求**：`period_type ∈ {annual, quarterly}`。
- **要求**：`annual` → `quarter` 必须为 `null`；`quarterly` → `quarter ∈ {1,2,3,4}`。
- **要求**：`year` 为合理整数（例如 1990–2100）。
- **验收**：非法组合返回 422；合法数据可创建。

### ADDED-3：三表 REST CRUD

- **要求**：嵌套于企业资源下：
  - `GET/POST /api/companies/{company_id}/balance-sheets`
  - `GET/PATCH/DELETE /api/companies/{company_id}/balance-sheets/{statement_id}`
  - 利润表、现金流量表路径同构（`income-statements` / `cash-flow-statements`）。
- **要求**：列表支持可选查询参数 `year`、`period_type`。
- **要求**：企业不存在 → 404；报告期冲突 → 409；语句不存在或不属于该企业 → 404。
- **要求**：分层：`api → services → models`，service 抛 `ServiceError` 族。
- **验收**：pytest 覆盖创建/列表/详情/更新/删除/404/409/422。

### ADDED-4：前端三大报表页

- **要求**：`StatementsView` 支持：
  1. 选择企业；
  2. Tab 切换：资产负债表 / 利润表 / 现金流量表；
  3. 展示该企业该类型报告期列表；
  4. 新建/编辑分组表单（按科目分组折叠）；
  5. 删除确认。
- **要求**：年报隐藏季度；季报必选 1–4。
- **验收**：开发态经 `/api` 代理完成端到端录入与列表刷新。

### ADDED-5：文档同步

- **要求**：更新 `docs/api.md`、`docs/architecture.md`（如需）、`AGENTS.md` 当前状态、追加 `docs/dev-log.md`。
- **验收**：文档与实现一致。

## 非本变更范围

- 财务比率计算与图表（Phase 2）。
- 多期对比 / 同比环比（Phase 3）。
- Excel 导入导出（Phase 4）。
- 用户认证、科目自定义配置 UI。
