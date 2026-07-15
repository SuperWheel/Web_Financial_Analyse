# Spec 009

## R1 URL 下载

`POST /api/imports/fetch/from-url`  
Body: `{ "url": "...", "company_id"?: int, "filename"?: str }`  
→ 下载 PDF（≤40MB）→ 创建 import job（`source_type=pdf_url`）。

## R2 巨潮检索

`GET /api/imports/fetch/cninfo/search?code=603486&year=2024`  
→ 候选列表：title、date、pdf_url、announcement_id、org_id、code、name。  
过滤：类别年报；标题含「年度报告」，排除「摘要」「英文」「取消」等。

## R3 巨潮下载入库

`POST /api/imports/fetch/cninfo/download`  
Body: `{ "pdf_url", "code"?, "title"?, "year"?, "company_id"? }`  
→ 下载 → job（`source_type=pdf_cninfo`）。

## R4 约束

- 仅 http(s)；超时与 UA 固定；失败返回可读错误。
- 不自动 commit。
- 测试 mock httpx，不依赖外网。
