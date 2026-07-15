# Change Proposal 001: 初始化项目框架

> 本变更包对应《AI Coding 开发规范》中"从零开始一个项目"场景，走 Spec 模式。

## Why（为什么做）

当前仓库只有一个开发规范文档，没有任何代码骨架。为了让后续所有功能开发有一个**清晰、可启动、范式明确**的起点，需要先搭建项目框架：

- 统一的目录结构与分层约定，避免后续返工。
- 一条端到端"示例切片"（企业 CRUD），确立前后端编码范式。
- 可启动的最小骨架：后端起服务、前端渲染页面、代理打通。
- 完整的 Spec/导航文档，让 AI 和人都能快速定位项目。

## What I Want（要什么）

1. **完整目录骨架**：backend / frontend / openspec / docs / data 各就各位。
2. **后端骨架**：FastAPI + SQLAlchemy + SQLite，含 Company 端到端切片（CRUD），三大报表为 stub。
3. **前端骨架**：Vue3 + Element Plus + ECharts + Vite，含 Dashboard 切片渲染企业列表，报表/分析页占位。
4. **导航文档**：CLAUDE.md（地图）+ README + .gitignore + docs（dev-log/architecture/api）。
5. **Spec 文档**：本 proposal + spec + design + tasks（含后续 Phase 1~4 全量规划）。

## What I Know（已知）

- 技术栈：FastAPI / Vue3 / Element Plus / ECharts / SQLite / pandas。
- 形态：单机本地，无认证。
- 业务场景：企业财务报表分析。

## What I Don't Know（待定，后续 Phase 决策）

- 三大报表的具体科目集合（中文会计准则口径）——Phase 1 决策。
- 财务比率清单与口径——Phase 2 决策。
- Excel 导入的模板格式——Phase 4 决策。

这些不影响"建框架"本身，留到对应 Phase 时再细化。
