# Proposal 009: 年报 PDF 拉取（URL + 巨潮）

## Why

本地已有 PDF 识别入库；缺「按公司/年份自动获得 PDF」。用户需要合法公开渠道检索下载后接入现有导入流水线。

## What

1. **Phase A**：`pdf_url` 下载 → `create_job_from_upload`。
2. **Phase B**：巨潮 topSearch + hisAnnouncement 按证券代码/年份检索年报候选，选中后下载并建 job。
3. 前端「年报导入」增加「在线拉取」Tab。

## Out of scope

- 港股披露易 / SEC EDGAR
- 绕过验证码、批量打爆官网
- 自动 commit（仍须人审）
