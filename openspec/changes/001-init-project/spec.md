# Spec 001: 初始化项目框架

> 使用 OpenSpec 的 ADDED 风格描述本变更新增的需求。本规格仅约束"项目框架建立"这一变更包；业务功能由后续 Phase 的独立 spec 描述。

## ADDED 需求

### ADDED-1：项目目录结构

- **要求**：仓库根下包含 `backend/`、`frontend/`、`openspec/`、`docs/`、`data/` 五个顶层目录，结构遵循 design.md 的目录树。
- **验收**：目录存在，各占位文件齐全。

### ADDED-2：后端最小可启动服务

- **要求**：`backend/app/main.py` 定义 FastAPI 应用，挂载 `/api/health` 健康检查端点，返回 JSON 含 `status: "ok"`。
- **要求**：`uvicorn app.main:app --reload`（在 `backend/` 下）能正常启动，无导入错误。
- **验收**：`GET /api/health` 返回 HTTP 200，body 为 `{"status": "ok"}`。

### ADDED-3：企业（Company）端到端切片

- **要求**：实现 `/api/companies` 资源的列表（GET）与创建（POST），遵循 api→services→models 分层。
- **数据模型**：`Company` 含 `id`、`name`、`code`（可空）、`industry`（可空）、`created_at`。
- **校验**：`name` 必填且非空；`code` 唯一（若提供）。
- **验收**：
  - `POST /api/companies` 创建成功，返回 201 与企业对象。
  - `GET /api/companies` 返回已创建的企业列表。
  - 重复 `code` 返回 409。

### ADDED-4：三大报表数据模型占位

- **要求**：`models/` 下提供 `balance_sheet.py` / `income_statement.py` / `cash_flow.py` 三个 stub 模型文件，定义表结构与 `(company_id, year, period_type, quarter)` 唯一约束，**但暂不暴露 API**。
- **验收**：表能随 `Base.metadata.create_all` 创建；不要求有路由。

### ADDED-5：前端最小可启动应用

- **要求**：`frontend/` 为 Vite + Vue3 + TS 工程，`npm install && npm run dev` 可启动。
- **要求**：默认布局含侧边栏导航（仪表盘 / 三大报表 / 比率分析）与主区域。
- **要求**：Dashboard 页通过 `/api` 代理调用后端 `GET /api/companies` 并渲染列表。

### ADDED-6：开发代理打通

- **要求**：`vite.config.ts` 配置 `/api` 代理到 `http://127.0.0.1:8000`，前端零跨域调用后端。
- **验收**：前端开发态下，Dashboard 能读到后端真实企业数据。

### ADDED-7：导航与文档

- **要求**：根目录提供 `CLAUDE.md`（地图式导航）、`README.md`（启动指南）、`.gitignore`。
- **要求**：`docs/` 提供 `dev-log.md`、`architecture.md`、`api.md` 占位。
- **验收**：文档齐全，CLAUDE.md 行数 ≤ 500，仅作导航不含全部细节。

## 非本变更范围（明确不做）

- 三大报表的录入 UI 与 API（Phase 1）。
- 财务比率计算与可视化（Phase 2）。
- 多期对比与趋势分析（Phase 3）。
- Excel 导入/导出（Phase 4）。
- 用户认证、权限、多租户。
