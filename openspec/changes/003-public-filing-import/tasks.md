# Tasks 003: 公开财报导入

## 0. 对齐

- [x] 确认阶段：导入作为 Phase 2，比率顺延 Phase 3
- [x] 确认一期范围：上传 PDF + CAS 主路径 + 人审；B 站适配；小米降级
- [x] 通用识别/填入算法文档 `algorithm.md`

## 1. 后端基础

- [x] `models/import_job.py` + create_all
- [x] `data/imports/` 落地与 gitignore
- [x] `services/importing/` 管道（profile/locate/extract/mapper/validate/pipeline）
- [x] 依赖：`pdfplumber`、`opencc-python-reimplemented`

## 2. CAS 抽取主路径

- [x] CAS A 股 PDF 网格抽取（科沃斯/影石）
- [x] 合并 vs 母公司标题切割
- [x] 单位/期间解析

## 3. 映射

- [x] `core/subject_aliases.py` 别名词典
- [x] mapper：规范化 + 匹配 + coverage
- [x] 勾稽软校验

## 4. API

- [x] upload / get / patch / commit / delete
- [x] 复用 statement_service 入库
- [x] 测试：pytest + 科沃斯 smoke commit

## 5. 前端

- [x] 导入向导页 `ImportView.vue`
- [x] 侧栏「年报导入」+ 三大报表入口按钮

## 6. 扩展适配

- [ ] `GaapHkPdfExtractor`（哔哩哔哩）— 管道已兼容行文本，词典需继续补强
- [x] 难解析降级文案（小米类 extractability 拒绝）
- [ ] Excel 适配器（后续）

## 7. 文档

- [x] api.md / AGENTS / CLAUDE / dev-log
