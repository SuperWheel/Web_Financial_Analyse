# Design 008

## 分层

```
api/excel_io.py → services/excel_import_service.py
  ├─ openpyxl 读模板/上传
  └─ statement_service create/update + _find_by_period
schemas/excel_import.py  预览/结果
```

与 PDF `imports/filings` 分离：Excel 为**已绑定企业**的结构化回填，无 OCR。

## 期间列解析

| 表头 | 结果 |
|------|------|
| `2024 年报` / `2024年报` | annual, year=2024, quarter=null |
| `2024 Q1` / `2024Q1` | quarterly, year=2024, quarter=1 |

同一工作簿内 period_type 须一致（以列头推断；混用则 422）。

## 行解析

- `科目代码` 非空且 ∈ 该表合法字段 → 取值。
- 分组行（代码空）跳过。
- 未知代码 → warning，不中断。
- 单元格：空/空白 → null；数字或可 float 字符串。

## 入库

对每个 (statement_type, period)：
1. 若全部字段 null → skip
2. find 同报告期 → update 或 create
3. 返回 summary counts

## 前端

在「年报导入」页增加 Tab：**Excel 模板**；或独立区块：选企业 → 下模板 → 上传 → 预览表 → 确认。
优先改 `ImportView` 增加 Excel 区，避免新路由。
