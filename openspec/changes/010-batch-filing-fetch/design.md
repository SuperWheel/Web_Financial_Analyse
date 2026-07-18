# Design 010

## 模块

复用 009，不新增存储：

```
services/fetching/service.py
  batch_cninfo_download(db, q, years, company_id) → BatchResult dict
api/fetch.py
  POST /imports/fetch/cninfo/batch
schemas/fetch.py
  CninfoBatchRequest / CninfoBatchYearResult / CninfoBatchResponse
```

## 流程

```
resolve 证券一次（search_securities[0]）
for year in sorted(unique years):
  throttle 已在 cninfo/http_util
  candidates = search_annual_reports(code, year)
  if empty → empty
  else pick candidates[0]
       create_job_from_cninfo_candidate(...) → ok | error
```

- **同步**请求：本地工具、批最多 12 年；前端 timeout ≥ 单年 × 年数（建议 180s× 或 600s 上限）。
- **首选候选**：与 UI 单年「列表第一条」一致（全文过滤已在 `cninfo._is_annual_full_report`）。
- **限速**：沿用 `MIN_INTERVAL_SEC=0.4`；批内自然串行。

## 响应形状

```json
{
  "code": "603486",
  "name": "科沃斯",
  "company_id": 1,
  "years_requested": [2022, 2023, 2024],
  "summary": { "ok": 2, "empty": 1, "error": 0 },
  "results": [
    {
      "year": 2022,
      "status": "ok",
      "title": "...",
      "pdf_url": "https://...",
      "job_id": 12,
      "detail": null
    }
  ]
}
```

成功项可不内嵌完整 `ImportJob`（体积大）；前端用 `job_id` 调既有 `GET /api/imports/filings/{id}` 打开核对。

## 前端

- 在线拉取卡：保留单年检索；增加 `yearFrom`/`yearTo` +「批量下载解析」。
- 结果表：年 / 状态 / 标题 / 打开核对。
- 批量进行中禁用重复提交；loading 覆盖。

## 测试

mock `search_cninfo_annual` + `create_job_from_cninfo_candidate`（或更底层 download），覆盖全 ok、混 empty/error、years 校验。
