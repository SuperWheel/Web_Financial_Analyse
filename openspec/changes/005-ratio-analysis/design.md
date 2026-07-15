# Design 005

## 比率清单（一期）

| key | 名称 | 公式 | 组 |
|-----|------|------|-----|
| current_ratio | 流动比率 | 流动资产合计 / 流动负债合计 | 偿债 |
| quick_ratio | 速动比率 | (流动资产合计−存货) / 流动负债合计 | 偿债 |
| cash_ratio | 现金比率 | 货币资金 / 流动负债合计 | 偿债 |
| debt_to_asset | 资产负债率 | 负债合计 / 资产总计 | 偿债 |
| equity_ratio | 权益比率 | 所有者权益合计 / 资产总计 | 偿债 |
| debt_to_equity | 产权比率 | 负债合计 / 所有者权益合计 | 偿债 |
| gross_margin | 毛利率 | (营业收入−营业成本) / 营业收入 | 盈利 |
| operating_margin | 营业利润率 | 营业利润 / 营业收入 | 盈利 |
| net_margin | 净利率 | 净利润 / 营业收入 | 盈利 |
| roe | 净资产收益率 | 归母净利/归母权益 或 净利/权益 | 盈利 |
| roa | 总资产收益率 | 净利润 / 资产总计 | 盈利 |
| asset_turnover | 总资产周转率 | 营业收入 / 资产总计 | 营运 |
| ocfr | 经营现金流/营收 | 经营现金流净额 / 营业收入 | 现金流 |

展示：比率类 ×100 加 `%` 的在 schema 用 `unit: "ratio"|"percent"` 区分；前端格式化。

## 分层

`api/ratios.py` → `services/ratio_service.py` → 读 statement models；公式在 `core`。

## 期间对齐

以资产负债表期间为主键；利润表/现金流按同 `(year, period_type, quarter)` 左连。缺表时仍算能算的比率。
