# Tasks 001: 初始化项目框架（含后续 Phase 规划）

> 复选框状态约定：`[x]` 已完成；`[ ]` 未完成。本变更包（001）只完成 Phase 0；Phase 1~4 为后续独立变更包，列于此供规划。

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

- [ ] 详见 `openspec/changes/003-public-filing-import/tasks.md`
- [ ] CAS 数字 PDF 主路径 + 人审入库
- [ ] 港股/US GAAP 适配 + 难解析降级

## Phase 3：财务比率分析与可视化（原 Phase 2）

- [ ] core/constants.py 定义比率公式清单
- [ ] services/ratio_service.py（pandas 计算）
- [ ] api/ratios.py：按企业/报告期返回比率
- [ ] 前端 AnalysisView：ECharts 图表 + 比率卡片
- [ ] 测试

## Phase 4：多期对比与趋势分析

- [ ] 查询接口支持多期数据组装（同比/环比）
- [ ] 趋势折线图、变动额/变动率计算
- [ ] 前端对比视图
- [ ] 测试

## Phase 5：Excel 模板导入导出与报表打印

- [ ] 与 003 的 Excel 适配器对齐
- [ ] 导出/打印
- [ ] 前端上传/下载 UI
- [ ] 测试
