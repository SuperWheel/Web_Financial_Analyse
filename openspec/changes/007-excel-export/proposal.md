# Proposal 007: Excel 导出（三表 + 财务比率）

## Why

多期对比与比率分析已可用，但结果只能在线查看；需要一键导出工作簿，便于线下复核与汇报。用户明确要求导出中包含**财务比率**。

## What

1. `export_service` 用 openpyxl 生成 `.xlsx`：资产负债表 / 利润表 / 现金流量表 / 财务比率（+ 说明页）。
2. REST：`GET /api/companies/{id}/export.xlsx`（流式下载）。
3. 前端：对比页、比率页提供「导出 Excel」入口。

## Out of scope

- Excel **导入**（另开变更包）
- 自定义科目列 / 模板上传
- 图表嵌入 Excel
