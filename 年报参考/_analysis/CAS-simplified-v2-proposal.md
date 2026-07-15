# CAS-simplified-v2 字段清单（基于 ashare-cas 10 家频次）

> 生成自管道批量：`年报参考/ashare-cas/*.pdf` → extract/map。  
> 原始数据：`年报参考/_analysis/`。  
> 统计口径：仅主集 10 家；标签经 `normalize_label`；按公司去重计出现率。

## 1. 管道跑批摘要

| 代码 | 简称 | fill_mode | conf | BS映射 | IS映射 | CF映射 | unmapped条数 |
|------|------|-----------|------|--------|--------|--------|-------------|
| 000651 | 格力电器 | AUTO_COMMIT_CANDIDATE | 0.97 | 31 | 18 | 15 | 200 |
| 002555 | 三七互娱 | AUTO_COMMIT_CANDIDATE | 0.97 | 31 | 18 | 5 | 56 |
| 300760 | 迈瑞医疗 | REJECT_OR_MANUAL | 0.79 | 2 | 2 | 5 | 85 |
| 600048 | 保利发展 | AUTO_COMMIT_CANDIDATE | 0.97 | 30 | 18 | 15 | 200 |
| 600309 | 万华化学 | AUTO_COMMIT_CANDIDATE | 0.97 | 32 | 18 | 7 | 65 |
| 600519 | 贵州茅台 | AUTO_COMMIT_CANDIDATE | 0.97 | 29 | 17 | 10 | 71 |
| 601933 | 永辉超市 | AUTO_COMMIT_CANDIDATE | 0.97 | 31 | 18 | 6 | 73 |
| 603486 | 科沃斯 | AUTO_COMMIT_CANDIDATE | 0.97 | 31 | 18 | 12 | 68 |
| 688111 | 金山办公 | AUTO_COMMIT_CANDIDATE | 0.97 | 30 | 18 | 9 | 61 |
| 688775 | 影石创新 | AUTO_COMMIT_CANDIDATE | 0.97 | 30 | 18 | 9 | 56 |

**异常**：`300760 迈瑞医疗` 定位到「合并××表（续）」页，表头页丢失 → BS/IS 映射极差。属 **locate 缺陷**，不否定样本；v2 统计仍计入 unmapped 标签频次。

**别名词典缺口（非缺列）**：`paid_in_capital` / `capital_reserve` / `surplus_reserve` / `retained_earnings` 已在 v1 ORM，但 `subject_aliases` 未配置 → 映射率 0/10，表现为 unmapped。应 **先补别名**，不要重复加列。

## 2. 决策规则（重申）

| 动作 | 条件 |
|------|------|
| 升格 v2 独立列 | 出现率 ≥40% 或分析口径必需 |
| 显式 rollup | 15%～40% 且语义稳定 |
| 仅 L0 | <15% 或小计/OCI 明细/章节 |
| 不进通用 v2 | 金融专用、母公司表 |

## 3. v1 已有字段：仅补别名（不改表结构）

| statement | field | 建议 aliases |
|-----------|-------|--------------|
| balance | `paid_in_capital` | 实收资本（或股本）, 实收资本(或股本), 股本, 实收资本 |
| balance | `capital_reserve` | 资本公积 |
| balance | `surplus_reserve` | 盈余公积 |
| balance | `retained_earnings` | 未分配利润 |
| balance | `total_assets` | 负债和所有者权益（或股东权益）总计, 负债和所有者权益(或股东权益)总计, 负债及股东权益总计 |
| income | `operating_cost` | 营业总成本 |

## 4. v2 新增标准科目（L1 扩列）— 建议冻结清单

共 **20** 个新字段（+ 建议桶 `other_non_current_liabilities` 若尚未作为 promote 列出则并入）。

### 4.1 资产负债表

| key | 中文 | 出现率 | 级别 | 备注 |
|-----|------|--------|------|------|
| `minority_interest` | 少数股东权益 | 100% | L2 | 合并报表必需；与 total_equity 口径 |
| `total_equity_parent` | 归属于母公司所有者权益合计 | 80% | L2 | 多数公司有；分析归母 ROE |
| `treasury_stock` | 库存股 | 80% | L2 | 权益减项；常见 减：库存股 |
| `other_comprehensive_income_equity` | 其他综合收益（权益） | 100% | L2 | BS 行；与 IS 的 OCI 发生额区分 |
| `other_current_liabilities` | 其他流动负债 | 90% | L2 | 高频桶 |
| `right_of_use_assets` | 使用权资产 | 70% | L2 | 租赁准则 |
| `other_equity_instruments_investment` | 其他权益工具投资 | 70% | L2 | FVOCI 投资 |
| `deferred_income` | 递延收益 | 70% | L2 | 常见负债/非流动 |
| `other_non_current_financial_assets` | 其他非流动金融资产 | 60% | L2 |  |
| `investment_property` | 投资性房地产 | 60% | L2 |  |
| `other_non_current_liabilities` | 其他非流动负债 | 30%+桶 | L2 | 承接预计负债等 rollup；与其他流动负债对称 |

### 4.2 利润表

| key | 中文 | 出现率 | 级别 | 备注 |
|-----|------|--------|------|------|
| `interest_income` | 利息收入 | 80% | L2 | 财务费用附注行；可独立或附属 |
| `net_profit_parent` | 归属于母公司股东的净利润 | 80% | L2 | 归母净利 |
| `net_profit_minority` | 少数股东损益 | 80% | L2 |  |
| `total_comprehensive_income` | 综合收益总额 | 80% | L2 |  |
| `fair_value_change_income` | 公允价值变动收益 | 70% | L2 |  |
| `asset_disposal_income` | 资产处置收益 | 60% | L2 |  |

### 4.3 现金流量表

| key | 中文 | 出现率 | 级别 | 备注 |
|-----|------|--------|------|------|
| `other_cash_received_operating` | 收到其他与经营活动有关的现金 | 70% | L2 |  |
| `other_cash_paid_operating` | 支付其他与经营活动有关的现金 | 70% | L2 |  |
| `tax_refunds_received` | 收到的税费返还 | 60% | L2 |  |
| `cash_from_investment_income` | 取得投资收益收到的现金 | 50% | L2 |  |

### 4.4 口径约定

- `total_equity`：优先映射「所有者权益合计 / 股东权益合计」（含少数股东的合并权益）。
- `total_equity_parent`：归母权益；若年报只有归母合计而无「权益合计」，`total_equity` 可人审或 = 归母 + 少数。
- `net_profit`：合并净利润；`net_profit_parent` / `net_profit_minority` 为拆分。
- `other_comprehensive_income`（IS）：本期 OCI **发生额**；`other_comprehensive_income_equity`（BS）：权益科目 **余额**。
- `treasury_stock`：库存股，通常为权益减项（入库为正数，展示/分析时作减项）。
- 比率默认：ROE 可用归母净利 / 归母权益（若两字段皆有），否则回退 net_profit / total_equity。

## 5. 显式 rollup 规则（不升格或升格前）

| 源标签（示例） | statement | mapped_to | 出现率 | 说明 |
|----------------|-----------|-----------|--------|------|
| 衍生金融资产 | balance | `trading_financial_assets` | 30% | 或 other_current_assets |
| 应收股利 | balance | `other_receivables` | 40% |  |
| 债权投资 | balance | `other_non_current_assets` | 30% | 若未升格 |
| 预计负债 | balance | `other_non_current_liabilities` | 30% | 建议同时新增 other_non_current_liabilities 桶 |
| 其他非流动负债 | balance | `other_non_current_liabilities` | 30% | 升格桶字段 |
| 收到其他与投资活动有关的现金 | cashflow | `cash_from_investments` | 40% | 弱归并；或仅 L0 |
| 支付其他与投资活动有关的现金 | cashflow | `cash_paid_for_investments` | 30% | 弱归并；或仅 L0 |

## 6. 仅 L0 / 不进 L1 聚合（示例）

- 经营活动现金流入小计
- 经营活动现金流出小计
- 投资活动现金流入小计
- 持续经营净利润
- OCI 明细子项
- 母公司报表重复行
- 各类「小计」行、附注编号行、章节标题
- OCI 子项明细（外币折算差额、其他权益工具公允价值变动等）— 合计进 `total_comprehensive_income` / BS OCI 余额即可

## 7. L0 / L1 表结构（合成版）

### 7.1 L1 — 标准科目宽表（扩列后）

沿用现表：

- `balance_sheets` / `income_statements` / `cash_flow_statements`
- 唯一键：`(company_id, year, period_type, quarter)`
- 金额：`Numeric(18,2)`，单位元
- 开发期：`ensure_sqlite_columns` 增列
- 元数据：`core/constants.py` + `frontend/.../statementFields.ts` 同步
- **COA_VERSION** = `cas-simplified-v2`
- v1 字段保留全数；v2 新增约 **21** 列（上表）

### 7.2 L0 — 披露明细表（新建）

```sql
CREATE TABLE statement_disclosure_lines (
  id INTEGER PRIMARY KEY,
  company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
  statement_kind VARCHAR(20) NOT NULL,  -- balance|income|cashflow
  year INTEGER NOT NULL,
  period_type VARCHAR(20) NOT NULL,
  quarter INTEGER,
  source VARCHAR(20) NOT NULL,       -- import|manual
  import_job_id INTEGER,
  line_no INTEGER,
  label_raw VARCHAR(512) NOT NULL,
  label_norm VARCHAR(512),
  amount NUMERIC(18,2),
  unit_scale_applied FLOAT DEFAULT 1,
  role VARCHAR(20),                  -- detail|subtotal|total|header|unknown
  page_no INTEGER,
  section_hint VARCHAR(64),
  mapped_to VARCHAR(64),             -- 标准科目 key 或 NULL
  map_rule VARCHAR(20),               -- alias|rollup|manual|none
  map_confidence FLOAT,
  include_in_aggregate BOOLEAN DEFAULT 1,
  created_at DATETIME,
  updated_at DATETIME
);
CREATE INDEX ix_disclosure_period ON statement_disclosure_lines(
  company_id, statement_kind, year, period_type, quarter);
```

### 7.3 聚合与 commit

```text
L0 detail 且 include_in_aggregate 且 mapped_to 非空
  → sum → L1[field]
L0 total 行命中合计字段 → 直接写入 L1 合计（优先于明细加总）
commit 同事务写 L0 + L1
```

## 8. 实施分期建议

1. **别名热修**：权益四字段 + 负债和权益总计（立刻提升映射，无需迁移）
2. **v2 扩列**：ORM/constants/前端 + ensure_sqlite_columns
3. **rollup_rules + aliases** 覆盖新字段
4. **L0 表 + 导入双写 + 人审映射**
5. **locate 修复**：迈瑞类「（续）」页向前扩展到表头
6. 比率 Phase 3 只读 L1

## 9. 冻结状态

- [x] 样本 10/10
- [x] 频次统计
- [x] 本清单草案
- [ ] 用户确认后写入 openspec 变更包并动代码
