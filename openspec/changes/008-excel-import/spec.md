# Spec 008: Excel 模板导入

## 需求

### R1 模板

- `GET /api/excel/template.xlsx?period_type=annual&years=2024,2025`
- Sheet：说明、资产负债表、利润表、现金流量表（可无「财务比率」或仅提示只读）。
- 列：`科目代码 | 科目 | {期间标签…}`；期间标签 `YYYY 年报` 或 `YYYY Qn`。

### R2 预览

- `POST /api/companies/{id}/excel/preview` multipart `file`
- 解析三表；忽略未知 sheet / 财务比率。
- 返回：将创建/覆盖的期间列表、每表非空科目数、警告（未知科目代码、无法解析的列头）。

### R3 入库

- `POST /api/companies/{id}/excel/import` multipart `file` + `overwrite`（默认 true）
- 同报告期已存在：`overwrite=true` 更新字段；`false` 跳过并记入 skipped。
- 全空期间（该表该期所有科目空）跳过。
- 事务：单企业导入尽量原子（一期一表失败则整体回滚）。

## 验收

- [ ] 模板可下载
- [ ] 导出文件可再导入（round-trip 金额一致）
- [ ] 测试覆盖 create / overwrite / 忽略比率 sheet
- [ ] 前端可下载模板并上传入库
