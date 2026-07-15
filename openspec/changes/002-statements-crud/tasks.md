# Tasks 002: 三大报表录入与存储

> `[x]` 完成 / `[ ]` 未完成。本包仅 Phase 1。

## 1. Spec

- [x] proposal / spec / design / tasks
- [x] 科目集合与 API 契约写入 design

## 2. 后端

- [x] 扩展三表 ORM 字段
- [x] `core/constants.py` 科目元数据 + 报告期常量
- [x] `schemas/statement.py` 校验（报告期规则）
- [x] `services/statement_service.py` CRUD + 防重
- [x] `api/statements.py` 挂载三表路由
- [x] SQLite 缺列补齐（ensure_sqlite_columns）
- [x] `tests/test_statements_api.py`

## 3. 前端

- [x] `api/statement.ts` 类型与请求
- [x] `constants/statementFields.ts` 分组科目
- [x] `stores/statement.ts`
- [x] `StatementsView.vue` 列表 + 分组表单

## 4. 验证与文档

- [x] pytest 全绿（20 passed）
- [x] smoke：创建企业 → 录入三表 → 列表
- [x] 更新 `docs/api.md`、`AGENTS.md` / `CLAUDE.md` 状态
- [x] 追加 `docs/dev-log.md`
