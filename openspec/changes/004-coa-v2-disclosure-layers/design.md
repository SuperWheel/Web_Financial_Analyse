# Design 004

依据 `年报参考/_analysis/CAS-simplified-v2-proposal.md`（10 家 A 股 CAS 频次）。

## 1. L1 新增字段

### balance

| key | 中文 |
|-----|------|
| right_of_use_assets | 使用权资产 |
| investment_property | 投资性房地产 |
| other_equity_instruments_investment | 其他权益工具投资 |
| other_non_current_financial_assets | 其他非流动金融资产 |
| other_current_liabilities | 其他流动负债 |
| deferred_income | 递延收益 |
| other_non_current_liabilities | 其他非流动负债 |
| treasury_stock | 库存股 |
| other_comprehensive_income_equity | 其他综合收益（权益） |
| minority_interest | 少数股东权益 |
| total_equity_parent | 归属于母公司所有者权益合计 |

### income

| key | 中文 |
|-----|------|
| fair_value_change_income | 公允价值变动收益 |
| asset_disposal_income | 资产处置收益 |
| interest_income | 利息收入 |
| net_profit_parent | 归属于母公司股东的净利润 |
| net_profit_minority | 少数股东损益 |
| total_comprehensive_income | 综合收益总额 |

### cashflow

| key | 中文 |
|-----|------|
| other_cash_received_operating | 收到其他与经营活动有关的现金 |
| other_cash_paid_operating | 支付其他与经营活动有关的现金 |
| tax_refunds_received | 收到的税费返还 |
| cash_from_investment_income | 取得投资收益收到的现金 |

## 2. L0 表

见 proposal 实现：`statement_disclosure_lines`。

## 3. 映射优先级

manual > alias ≥0.75 无歧义 > rollup 显式规则 > none（仅 L0）

## 4. 口径

- `total_equity` = 合并权益合计（含少数）
- `total_equity_parent` = 归母权益
- IS `other_comprehensive_income` = 本期发生额；BS `other_comprehensive_income_equity` = 余额
- `treasury_stock` 存绝对值，分析作权益减项

## 5. 分层

api → services → models；rollup/aliases 在 core。
