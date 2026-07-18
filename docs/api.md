# API 文档

> 后端启动后，FastAPI 自动生成交互式文档：
> - Swagger UI：http://127.0.0.1:9000/docs
> - ReDoc：http://127.0.0.1:9000/redoc
>
> 本文档为人工维护的接口摘要，便于快速查阅。以 `/docs` 为准。

## 通用约定

- 所有路径以 `/api` 为前缀。
- 时间字段统一 ISO 8601。
- 错误响应：`{"detail": "..."}`，HTTP 状态码表达语义（4xx 客户端错误，5xx 服务端错误）。
- 报告期：`period_type` 为 `annual` | `quarterly`；年报 `quarter` 必须为 `null`，季报为 `1|2|3|4`。

## 健康检查

### `GET /api/health`

健康检查。

**响应 200**：
```json
{ "status": "ok" }
```

## 企业（Company）

### `GET /api/companies`

获取企业列表。

**响应 200**：`Company[]`

### `POST /api/companies`

创建企业。

**请求体**：
```json
{ "name": "示例科技", "code": "EX001", "industry": "信息技术" }
```
- `name`：必填，非空。
- `code`：选填，唯一。
- `industry`：选填。

**响应 201**：`Company`

**错误**：
- `409`：`code` 与已有企业冲突。

### `GET /api/companies/{company_id}`

获取单个企业。不存在 → `404`。

### `PATCH /api/companies/{company_id}`

部分更新企业。

### `DELETE /api/companies/{company_id}`

删除企业（级联删除关联报表）。**响应 204**。

## 三大报表

三表路径同构，嵌套在企业资源下：

| 资源 | 路径段 |
|------|--------|
| 资产负债表 | `balance-sheets` |
| 利润表 | `income-statements` |
| 现金流量表 | `cash-flow-statements` |

下列以资产负债表为例，另两表替换路径段即可。科目字段见 `openspec/changes/004-coa-v2-disclosure-layers/design.md`（**CAS-simplified-v2**）。

### `GET /api/companies/{company_id}/balance-sheets`

列表。可选查询：`year`、`period_type`。

**响应 200**：`BalanceSheet[]`

**错误**：企业不存在 → `404`

### `POST /api/companies/{company_id}/balance-sheets`

创建报告期。

**请求体**（示例）：
```json
{
  "year": 2024,
  "period_type": "annual",
  "quarter": null,
  "monetary_funds": 1000.50,
  "total_assets": 5000,
  "total_liabilities": 2000,
  "total_equity": 3000
}
```

科目金额均可选（可空，支持分步录入）。

**响应 201**：完整报表对象（含 `id`、`company_id`）。

**错误**：
- `404` 企业不存在
- `409` 同企业同报告期已存在
- `422` 报告期规则或字段校验失败

### `GET /api/companies/{company_id}/balance-sheets/{statement_id}`

详情。不存在或不属于该企业 → `404`。

### `PATCH /api/companies/{company_id}/balance-sheets/{statement_id}`

部分更新（报告期与科目均可选）。

### `DELETE /api/companies/{company_id}/balance-sheets/{statement_id}`

删除。**响应 204**。

### 利润表 / 现金流量表

- `.../income-statements`：科目含 `operating_revenue`、`net_profit` 等
- `.../cash-flow-statements`：科目含 `net_cash_flow_operating`、`net_increase_in_cash` 等

## 年报导入（公开财报）

### `POST /api/imports/filings`

上传 PDF，创建导入任务并解析。

- `multipart/form-data` 字段名：`file`
- 响应 201：`ImportJob`（含 `status`、`draft.statements`、`draft.disclosure_lines`、`coverage`、`unmapped`、`fill_mode`、`confidence`、`coa_version`）

`status`：`review` | `failed` | `committed` 等。  
`fill_mode`：`AUTO_COMMIT_CANDIDATE` | `REVIEW_REQUIRED` | `REJECT_OR_MANUAL`。

### `GET /api/imports/filings`

任务列表。

### `GET /api/imports/filings/{id}`

任务详情与映射草稿。

### `PATCH /api/imports/filings/{id}`

修正公司名/年份/报告期/科目金额草稿。

### `POST /api/imports/filings/{id}/commit`

确认入库（创建/覆盖企业三表 **L1**，并写入 `statement_disclosure_lines` **L0** 披露明细）。请求体可选：`{ "company_id": 1, "overwrite": true }`。`commit_result` 含 `statement_ids`、`disclosure_lines_written`。

### `DELETE /api/imports/filings/{id}`

删除任务与上传文件。**204**。

## 财务比率（Phase 3）

比率**不落库**，按 L1 三表科目动态计算。公式与字段见 `openspec/changes/005-ratio-analysis/design.md`。

### `GET /api/companies/{company_id}/ratio-periods`

有报表数据的报告期列表（含 `has_balance` / `has_income` / `has_cashflow`）。

### `GET /api/companies/{company_id}/ratios`

查询参数：`year`（必填）、`period_type`（默认 annual）、`quarter`（季报必填）。

响应：`ratios[]`（key/name/group/unit/value/missing/reason）、`summary`、`sources`。

- 缺字段 → `value=null`，`reason=missing_fields`
- 分母 0 → `reason=zero_denominator`
- ROE 优先归母净利/归母权益

### `GET /api/companies/{company_id}/ratios/history`

查询参数：`period_type`、`keys`（逗号分隔，可选）。多期序列供图表。


## 多期科目对比（Phase 4）

科目金额矩阵**不落库**，按 L1 三表动态组装环比与结构占比。详见 `openspec/changes/006-multi-period-compare/design.md`。

### `GET /api/companies/{company_id}/compare-periods`

有报表数据的报告期列表（字段同 `ratio-periods`：`has_balance` / `has_income` / `has_cashflow`）。

### `GET /api/companies/{company_id}/compare`

查询参数：
- `statement_type`（必填）：`balance` | `income` | `cashflow`
- `period_type`（默认 `annual`）
- `years`（可选，逗号分隔年份过滤）

响应：`periods[]`（时间升序）、`groups[].rows[]`：
- `values`：各期金额
- `deltas` / `delta_pcts`：相对**序列上一期**的变动额 / 变动率（首期为 `null`；上期为 0 时 `delta_pct` 为 `null`）
- `structure_pcts`：结构占比（balance÷`total_assets`，income÷`operating_revenue`，cashflow 全 `null`）

**错误**：
- `404`：企业不存在
- `422`：非法 `statement_type` / `period_type` / `years`


## Excel 导出（Phase 5 导出切片）

工作簿含：**说明**、**资产负债表**、**利润表**、**现金流量表**、**财务比率**。比率动态计算写入，不落库。

### `GET /api/companies/{company_id}/export.xlsx`

查询参数：
- `period_type`（默认 `annual`）
- `years`（可选，逗号分隔年份）

响应：`application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` 附件。

- 财务比率 sheet：`unit=%` 的值已 ×100 写出（如 12.5 表示 12.5%）；`倍` 为倍数原值。
- 企业不存在 → `404`；无期间时仍返回空结构工作簿。


## Excel 模板导入（Phase 5 导入切片）

与导出列结构对称；**不导入**财务比率（入库后动态计算）。

### `GET /api/excel/template.xlsx`

空三表模板。Query：`period_type`、`years`（逗号年份，默认近三年）。

### `POST /api/companies/{company_id}/excel/preview`

multipart `file`。解析预览：将新建/更新/跳过的期间、警告。不入库。

### `POST /api/companies/{company_id}/excel/import`

multipart `file` + form `overwrite`（默认 true）。写入 L1 三表；同报告期可覆盖。


## 年报在线拉取（变更包 009）

下载 PDF 后走现有导入任务（**不自动 commit**）。请控制频率，遵守巨潮等站点使用条款。

### `GET /api/imports/fetch/cninfo/securities`

Query：`q`（证券代码或公司名称；全称会回退简称）。返回证券列表（含 `industry`，东财 best-effort，可能为空）。

### `GET /api/imports/fetch/cninfo/search`

Query：`year`，以及 `q` 或兼容参数 `code`（代码/名称）。  
返回年报全文候选（排除摘要/英文等），含 `pdf_url`。

### `POST /api/imports/fetch/cninfo/search-years`

Body：`q`/`code` + `years`（1–12 个）。  
统一多年检索：1 个年份=单年，多个=多年拼接候选列表（**不下载**）。供前端勾选后导入。

### `POST /api/imports/fetch/cninfo/download`

Body：`pdf_url`、可选 `code`/`title`/`year`/`name`/`company_id`。  
下载 PDF → 创建 import job（`source_type=pdf_cninfo`）。

### `POST /api/imports/fetch/cninfo/batch`

Body：
```json
{
  "q": "603486",
  "years": [2022, 2023, 2024],
  "company_id": 1
}
```
- `q` 或兼容 `code`：证券代码 / 公司名称（必填其一）。
- `years`：1–12 个年份（1990–2100）；服务端去重升序。
- 串行检索全文年报 → 下载首选候选 → 建 import job；**不自动 commit**。
- 单年 `empty`/`error` 不中断整批。

响应 200：`code`/`name`/`years_requested`/`summary{ok,empty,error}`/`results[]`  
（`status`=`ok|empty|error`；成功含 `job_id`，可用 `GET /api/imports/filings/{id}` 打开核对）。

- 缺 `q`/`code` 或 `years` 非法 → `422`
- 证券未找到 / 年份超限（业务层）→ `400`

### `POST /api/imports/fetch/from-url`

Body：`url`、可选 `company_id`/`filename`。  
任意 http(s) PDF 直链 → job（`source_type=pdf_url`）。

---

> **Post-1.0 其余项**：港股/美股拉取解析等见 `openspec/project.md` backlog；当前主路径为 A 股 CAS。批量多年已由变更包 **010** 交付。
