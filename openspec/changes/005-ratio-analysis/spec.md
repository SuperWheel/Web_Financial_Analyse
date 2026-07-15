# Spec 005: 财务比率分析

## ADDED

### ADDED-1：比率定义

系统提供分组比率（偿债 / 营运 / 盈利 / 现金流），公式集中在 `core/constants.RATIO_DEFINITIONS`（或等价结构）。

### ADDED-2：动态计算

- 输入：企业 + `(year, period_type, quarter)`。
- 读取该期资产负债表、利润表（现金流按需）。
- 缺字段或分母为 0 → 该比率 `value=null` 并给出 `missing`/`reason`。
- ROE：优先 `net_profit_parent / total_equity_parent`，否则回退 `net_profit / total_equity`。

### ADDED-3：API

- `GET /api/companies/{id}/ratio-periods`：有报表数据的期间列表。
- `GET /api/companies/{id}/ratios?year=&period_type=&quarter=`：单期全部比率。
- `GET /api/companies/{id}/ratios/history?period_type=annual`：多期序列（图表用）。

### ADDED-4：前端

- `/analysis` 可选用企业、报告期，展示比率卡片与简单图表。
- 无数据时友好空态。

## 非目标

- 自定义比率编辑器
- 与导入 L0 明细联动
