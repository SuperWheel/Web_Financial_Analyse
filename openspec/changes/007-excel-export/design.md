# Design 007

## 分层

```
api/export.py → services/export_service.py
  ├─ statement list / compare 科目矩阵逻辑（复用 constants groups）
  └─ ratio_service.compute_period_ratios（每期）
openpyxl 仅在 service 内使用
```

## 期间轴

与 compare 一致：过滤 `period_type` + 可选 `years`，按 `(year, quarter)` 升序。
期间集合 = 三表并集（任一表有该期即出列；该表缺数则单元格空）。

## 比率 sheet

对每个期间调用 `compute_period_ratios`；行序固定为 `RATIO_DEFINITIONS`。
列：分组 | 比率 | 单位说明 | 公式 | 各期值

percent：导出 `value * 100`（与常见 Excel 百分比录入习惯一致，**不**使用 Excel 百分比格式以免双重×100 误解；表头写「%」）。
ratio：原值，表头写「倍」。

## 文件名

`{公司名}_{period_type}_{起年}-{止年}.xlsx`，非法文件名字符替换为 `_`。

## 前端下载

`axios` `responseType: 'blob'` + 解析 `Content-Disposition` 或默认文件名触发 `<a download>`。
