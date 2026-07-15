# Design 002: 三大报表录入与存储

## 1. 架构与分层

延续 Phase 0 分层，新增领域切片：

```
api/statements.py          # 三表路由（或拆分 balance_sheets.py 等，本期单文件 statements.py）
services/statement_service.py
schemas/statement.py       # 共用报告期 + 三表 Create/Update/Read
models/{balance_sheet,income_statement,cash_flow}.py  # 扩字段
core/constants.py          # 科目元数据（分组标签，供前端/文档）
```

路由挂载：`api_router.include_router(statements_router)`。

## 2. API 契约

前缀均在 `/api` 下。`{kind}` 表示三表之一。

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/companies/{company_id}/balance-sheets` | 列表，`?year=&period_type=` |
| POST | `/companies/{company_id}/balance-sheets` | 创建 201 |
| GET | `/companies/{company_id}/balance-sheets/{id}` | 详情 |
| PATCH | `/companies/{company_id}/balance-sheets/{id}` | 部分更新 |
| DELETE | `/companies/{company_id}/balance-sheets/{id}` | 204 |

同构：`income-statements`、`cash-flow-statements`。

请求体：报告期字段 + 科目字段（均可选，允许空壳期再补数）。  
响应：含 `id`、`company_id`、报告期、全部科目。

## 3. 报告期规则

| period_type | quarter | 说明 |
|-------------|---------|------|
| `annual` | 必须 `null` | 年报 |
| `quarterly` | 必须 1/2/3/4 | 季报 |

唯一性：同 `company_id + year + period_type + quarter` 不可重复。  
SQLite 对 UNIQUE 中 NULL 不判等 → **service 层显式查询防重**（年报 `quarter IS NULL`）。

## 4. 科目集合（完整 CAS 简化版）

金额单位：元；类型：`Numeric(18,2)` 可空。字段名 `snake_case`，注释中文科目名。

### 4.1 资产负债表 BalanceSheet（32 项）

**流动资产**
| 字段 | 中文 |
|------|------|
| monetary_funds | 货币资金 |
| trading_financial_assets | 交易性金融资产 |
| notes_receivable | 应收票据 |
| accounts_receivable | 应收账款 |
| prepayments | 预付款项 |
| other_receivables | 其他应收款 |
| inventories | 存货 |
| other_current_assets | 其他流动资产 |
| total_current_assets | 流动资产合计 |

**非流动资产**
| 字段 | 中文 |
|------|------|
| long_term_equity_investments | 长期股权投资 |
| fixed_assets | 固定资产 |
| construction_in_progress | 在建工程 |
| intangible_assets | 无形资产 |
| goodwill | 商誉 |
| deferred_tax_assets | 递延所得税资产 |
| other_non_current_assets | 其他非流动资产 |
| total_non_current_assets | 非流动资产合计 |
| total_assets | 资产总计 |

**流动负债**
| 字段 | 中文 |
|------|------|
| short_term_borrowings | 短期借款 |
| notes_payable | 应付票据 |
| accounts_payable | 应付账款 |
| contract_liabilities | 合同负债 |
| employee_benefits_payable | 应付职工薪酬 |
| taxes_payable | 应交税费 |
| other_payables | 其他应付款 |
| non_current_liab_due_one_year | 一年内到期的非流动负债 |
| total_current_liabilities | 流动负债合计 |

**非流动负债 / 负债合计**
| 字段 | 中文 |
|------|------|
| long_term_borrowings | 长期借款 |
| bonds_payable | 应付债券 |
| lease_liabilities | 租赁负债 |
| deferred_tax_liabilities | 递延所得税负债 |
| total_non_current_liabilities | 非流动负债合计 |
| total_liabilities | 负债合计 |

**所有者权益**
| 字段 | 中文 |
|------|------|
| paid_in_capital | 实收资本（或股本） |
| capital_reserve | 资本公积 |
| surplus_reserve | 盈余公积 |
| retained_earnings | 未分配利润 |
| total_equity | 所有者权益合计 |

> 合计类字段由用户录入（不自动勾稽），便于与外部报表对齐；勾稽校验可后续增强。

### 4.2 利润表 IncomeStatement（18 项）

| 字段 | 中文 |
|------|------|
| operating_revenue | 营业收入 |
| operating_cost | 营业成本 |
| taxes_and_surcharges | 税金及附加 |
| selling_expenses | 销售费用 |
| admin_expenses | 管理费用 |
| rd_expenses | 研发费用 |
| financial_expenses | 财务费用 |
| other_income | 其他收益 |
| investment_income | 投资收益 |
| credit_impairment_loss | 信用减值损失 |
| asset_impairment_loss | 资产减值损失 |
| operating_profit | 营业利润 |
| non_operating_income | 营业外收入 |
| non_operating_expense | 营业外支出 |
| total_profit | 利润总额 |
| income_tax_expense | 所得税费用 |
| net_profit | 净利润 |
| other_comprehensive_income | 其他综合收益 |

### 4.3 现金流量表 CashFlowStatement（15 项）

| 字段 | 中文 |
|------|------|
| cash_from_sales | 销售商品、提供劳务收到的现金 |
| cash_paid_for_goods | 购买商品、接受劳务支付的现金 |
| cash_paid_to_employees | 支付给职工以及为职工支付的现金 |
| taxes_paid | 支付的各项税费 |
| net_cash_flow_operating | 经营活动产生的现金流量净额 |
| cash_from_investments | 收回投资收到的现金 |
| cash_from_asset_disposal | 处置固定资产等收回的现金净额 |
| cash_paid_for_assets | 购建固定资产等支付的现金 |
| cash_paid_for_investments | 投资支付的现金 |
| net_cash_flow_investing | 投资活动产生的现金流量净额 |
| cash_from_financing | 吸收投资/取得借款收到的现金 |
| cash_paid_for_debt | 偿还债务支付的现金 |
| cash_paid_for_dividends | 分配股利、利润或偿付利息支付的现金 |
| net_cash_flow_financing | 筹资活动产生的现金流量净额 |
| net_increase_in_cash | 现金及现金等价物净增加额 |

## 5. 前端交互

- 顶部：企业 `el-select` + 刷新。
- `el-tabs`：三表。
- 工具栏：新建报告期、刷新列表。
- 表格列：年份、类型、季度、关键合计字段、操作（编辑/删除）。
- 对话框：报告期选择 + `el-collapse` 按分组渲染数字输入（`el-input-number`，精度 2，可空）。
- 科目元数据：`core/constants.py` 的 `STATEMENT_FIELDS` 与前端 `src/constants/statementFields.ts` 对齐（本期双端各维护一份常量，避免额外 BFF）。

## 6. Schema 迁移

- 启动：`create_all`。
- 附加：`database.ensure_sqlite_columns()` —— 用 `PRAGMA table_info` 对比模型，对缺失列 `ALTER TABLE ... ADD COLUMN`（仅增列，不删不改类型）。
- 若本地库结构严重偏离：删除 `data/finance.db` 重启即可。

## 7. 风险与权衡

- **不自动勾稽合计**：降低录入摩擦；分析用户通常已有外部合计。
- **字段双端常量**：短期可接受；Phase 4 模板导出时可抽公共 JSON。
- **单文件 statements API**：三表 CRUD 高度同构，用泛型 service 助手减少重复。
