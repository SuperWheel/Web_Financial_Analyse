# AGENTS.md —— AI 协作约定

本文件定义 AI（及人类协作者）在本仓库工作的统一约定。所有改动都应遵循。

## 协作流程（来自《AI Coding 开发规范》三金律）

1. **先对齐再动手**：开始任何非平凡改动前，先用自然语言复述理解的需求，确认后再执行。
2. **小步快跑，步步验证**：分阶段推进，每阶段完成验证再继续；不一次性生成全部代码。
3. **文档即副产品**：每次对话结束后，把变更追加到 `docs/dev-log.md`。

## 分层架构（铁律）

后端严格分层，不可越层：

```
api/        → 路由层：只做请求/响应转换、依赖注入，不写业务逻辑
   ↓
services/   → 业务层：业务规则与编排，调用 models
   ↓
models/     → 数据层：SQLAlchemy ORM
schemas/    → 边界校验：Pydantic，请求/响应与内部模型隔离
core/       → 常量、公式、配置等横切关注点
```

- ❌ 不要在 `api/` 里直接写 SQL 或业务判断。
- ❌ 不要在 `models/` 里写业务逻辑。
- ✅ 新增功能请遵守该分层，参照 `companies` 切片范式。

## 命名约定

- 后端文件/模块：`snake_case`（如 `company_service.py`）。
- 前端文件/组件：组件 `PascalCase`（`Dashboard.vue`），其余 `camelCase`。
- 数据库表名：`snake_case` 复数（`balance_sheets`）。
- API 路径：统一 `/api` 前缀，资源复数（`/api/companies`）。

## 改动前自检清单

- [ ] 这属于哪个模式？Vibe（小改）/ Plan（功能）/ Spec（模块/架构）。
- [ ] 是否新增依赖？如新增，需在对应 `requirements.txt` / `package.json` 登记，并在 design.md 记录理由。
- [ ] 是否触碰不该改的文件？（Spec 文档 / 已稳定的模块）
- [ ] 是否更新了 `docs/dev-log.md`？

## 不要做

- 不要把详细编码规范塞进 `CLAUDE.md`（那只是地图）。通用约定放本文件。
- 不要在单次任务里跨多个 Phase 推进。
- 不要跳过验证步骤直接交付。
