# Spec 007: Excel 导出

## 需求

### R1 导出内容

工作簿至少 5 个 sheet：

| Sheet | 内容 |
|-------|------|
| 说明 | 企业、期间类型、导出时间、口径说明 |
| 资产负债表 | 科目 × 各期金额（升序） |
| 利润表 | 同上 |
| 现金流量表 | 同上 |
| 财务比率 | 比率名称/分组/单位/公式 × 各期数值 |

- 比率：`unit=percent` 在表中写 **百分数数值**（如 12.5 表示 12.5%），表头标注单位；`ratio` 写倍数。
- 缺期/缺科目单元格留空。
- 仅同 `period_type` 内导出；可选 `years` 过滤。

### R2 API

`GET /api/companies/{company_id}/export.xlsx`

- Query：`period_type`（默认 annual）、`years`（可选逗号年份）
- 响应：`Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
- `Content-Disposition: attachment; filename="..."`
- 无任何可用期间：仍返回 200 工作簿，说明页注明无数据；企业不存在 404。

### R3 前端

- 比率分析页、多期对比页工具条「导出 Excel」。
- 使用当前选中的企业与期间类型；对比页若已选年份则一并传入。

## 验收

- [ ] 后端测试：种子两期数据 → xlsx 含比率 sheet 与正确数值
- [ ] 前端可触发下载
- [ ] docs / dev-log 更新
