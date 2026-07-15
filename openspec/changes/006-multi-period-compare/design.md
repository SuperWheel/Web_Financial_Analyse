# Design 006

## 分层

```
api/compare.py → services/compare_service.py → statement list models
schemas/compare.py  边界
core/constants.py   科目分组（复用 BALANCE/INCOME/CASH_FLOW_GROUPS）
```

禁止在 `api/` 写计算；比率逻辑不复用（005 已独立）。

## API

### `GET /api/companies/{company_id}/compare-periods`

与比率期间同源：任意 L1 表存在即列出，附 `has_balance|has_income|has_cashflow`。
实现上可直接委托 `ratio_service.list_ratio_periods`，避免双份排序逻辑。

### `GET /api/companies/{company_id}/compare`

| 参数 | 说明 |
|------|------|
| `statement_type` | `balance` \| `income` \| `cashflow` |
| `period_type` | `annual` \| `quarterly`，默认 `annual` |
| `years` | 可选，`2023,2024,2025`；省略则该类型全部有数据期间 |

**响应摘要**：

```json
{
  "company_id": 1,
  "statement_type": "balance",
  "period_type": "annual",
  "base_field": "total_assets",
  "base_label": "资产总计",
  "periods": [
    {"year": 2023, "period_type": "annual", "quarter": null, "label": "2023 年报", "statement_id": 1}
  ],
  "groups": [
    {
      "key": "current_assets",
      "label": "流动资产",
      "rows": [
        {
          "key": "monetary_funds",
          "label": "货币资金",
          "values": [100.0, 120.0],
          "deltas": [null, 20.0],
          "delta_pcts": [null, 0.2],
          "structure_pcts": [0.05, 0.06]
        }
      ]
    }
  ]
}
```

- `periods` / `values` 等数组**时间升序**（旧→新），便于环比。
- `delta_pcts`：`(curr - prev) / abs(prev)`；`prev` 为 0 或任一侧 null → `null`。
- `structure_pcts`：`value / base`（0–1 比例，与比率 `percent` unit 一致）。

## 计算

1. 拉取对应 model 列表，过滤 `period_type` 与可选 `years`。
2. 去重按 `(year, quarter)` 建 period 轴。
3. 对每个科目 key：`values[i] = getattr(row_i, key)`。
4. 环比、结构在 service 内纯函数完成。

## 前端

- `api/compare.ts`：类型 + `fetchComparePeriods` / `fetchCompare`。
- `views/CompareView.vue`：工具条 + `el-table` 固定首列 + ECharts 折线。
- 金额格式：千分位，亿/万自适应可选（一期用简单 `toLocaleString` + 万元切换可选，默认原值千分位）。
- 复用 `useCompanyStore` 与 `statementFields` 仅作展示对齐；**权威字段序以后端 groups 为准**。

## 风险

- 期数过多表格过宽：前端默认最多勾选 5 期，可全选。
- 季报环比是「上一季」而非「去年同季」：一期明确为**序列相邻期**环比，页面脚注说明。
