# Spec 004: CAS-simplified-v2 + 披露明细层

## ADDED

### ADDED-1：COA 版本

- 系统标准科目版本号 `COA_VERSION = "cas-simplified-v2"`。
- v1 字段全部保留；v2 新增字段见 design。

### ADDED-2：L1 扩列

- 资产负债表 / 利润表 / 现金流量表 ORM、Pydantic、前后端元数据同步新增 v2 字段。
- 开发期 `ensure_sqlite_columns` 自动增列。

### ADDED-3：别名与 rollup

- `subject_aliases` 覆盖 v1 权益科目与 v2 新字段。
- `rollup_rules`：显式源标签 → 标准科目；映射报告中 `rule=rollup`。

### ADDED-4：L0 披露明细

- 表 `statement_disclosure_lines` 按企业+报告期+表种存储原文行。
- 导入 commit 同事务写入 L0 + L1；同 period 的 `source=import` 行可被覆盖替换。
- 每行含 `mapped_to` / `map_rule` / `role` / `include_in_aggregate`。

### ADDED-5：locate 续页

- 标题含「续」时延续当前 segment，不重置 `start_page`。

## MODIFIED

- 导入管道输出披露行草稿；commit 双写。
- 测试 PDF 路径对齐 `年报参考/ashare-cas/`。

## 非目标

- 手工录入强制录 L0。
- 比率公式实现。
