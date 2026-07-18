# Tasks 001: 初始化项目框架（含后续 Phase 规划）

> 复选框状态约定：`[x]` 已完成；`[ ]` 未完成。本变更包（001）只交付 Phase 0 代码；下方 Phase 1–5 为历史规划索引，**v1.0.0 时均已由独立变更包完成**（港股/EDGAR/批量任务属 post-1.0）。

---

## Phase 0：建立项目框架（本变更包 001）

### 0.1 目录结构
- [x] 创建 backend/frontend/openspec/docs/data 完整目录树
- [x] 各占位文件齐全

### 0.2 Spec 与导航文档
- [x] openspec/project.md、openspec/AGENTS.md
- [x] openspec/changes/001-init-project/{proposal,spec,design,tasks}.md
- [x] CLAUDE.md（地图式导航）
- [x] README.md、.gitignore
- [x] docs/{dev-log,architecture,api}.md

### 0.3 后端骨架
- [x] backend/requirements.txt
- [x] app/main.py（FastAPI 入口 + /api/health + CORS）
- [x] app/config.py、app/database.py
- [x] models/base.py、company.py、三表 stub
- [x] schemas/company.py、common.py
- [x] api/deps.py、companies.py、__init__.py
- [x] services/company_service.py
- [x] core/constants.py（占位）
- [x] tests/test_companies_api.py

### 0.4 前端骨架
- [x] package.json、vite.config.ts、tsconfig.json、index.html
- [x] src/main.ts、App.vue
- [x] router/index.ts
- [x] layouts/DefaultLayout.vue
- [x] api/http.ts、company.ts
- [x] stores/company.ts
- [x] views/Dashboard.vue（切片）
- [x] views/StatementsView.vue、AnalysisView.vue（占位）

### 0.5 验证
- [x] 后端 `uvicorn app.main:app` 启动，`GET /api/health` → 200（默认端口 9000）
- [x] 前端 `npm run dev` 启动，Dashboard 经代理读到后端数据（POST/GET/409 全通）
- [x] 示例切片测试通过（pytest **9 passed**）

---

## Phase 1：三大报表录入与存储（变更包 002）

- [x] 完成（见 `openspec/changes/002-statements-crud/tasks.md`）

## Phase 2：公开年报导入（变更包 003，优先）

- [x] 详见 `openspec/changes/003-public-filing-import/tasks.md`（CAS 数字 PDF 主路径 + 人审入库已通）
- [x] CAS 数字 PDF 主路径 + 人审入库
- [ ] 港股/US GAAP 适配 + 难解析降级 → **post-1.0**（003 内部分任务仍 open）

## Phase 3：财务比率分析与可视化（变更包 005）

- [x] 完成（见 `openspec/changes/005-ratio-analysis/tasks.md`）

## Phase 4：多期对比与趋势分析（变更包 006）

- [x] 完成（见 `openspec/changes/006-multi-period-compare/tasks.md`）

## Phase 5：Excel 模板导入导出（变更包 007/008）+ 在线拉取（009）

- [x] Excel 导出含比率（007）
- [x] Excel 模板导入（008）
- [x] 年报在线拉取 URL+巨潮（009）
- [ ] 批量多年任务、港股/EDGAR → **post-1.0**（见 `openspec/project.md`）
