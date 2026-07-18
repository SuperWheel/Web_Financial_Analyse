# Proposal 010: 巨潮年报批量多年拉取

## Why

009 已支持单年检索 + 单份下载建 job。分析常用「同一公司连续多年年报」，逐次检索下载摩擦大。需要在现有 fetch 管道上做**多年份一次提交**，仍走人审入库。

## What

1. 后端：`POST /api/imports/fetch/cninfo/batch` —— 指定证券（代码/名称）+ 年份列表，按年检索全文年报 → 下载 → `create_job_from_upload`（`source_type=pdf_cninfo`）。
2. 单年失败不中断整批；响应按年汇总 `ok | empty | error` 与 `job_id`。
3. 沿用 009 限速与 PDF 校验；**不**自动 commit。
4. 前端「在线拉取」增加年份区间 / 多选年 +「批量下载解析」与结果表。

## Out of scope

- 多证券并行批处理 / 后台队列 / 持久化 batch 任务表
- 港股 / EDGAR
- 自动 commit 或跳过人审
- 打爆官网的无上限年份（本包限制最多 12 年）
