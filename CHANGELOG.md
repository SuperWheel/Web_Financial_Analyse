# Changelog

## [1.0.0] — 2026-07-16

首个功能完整的本地可用版本（单机 FastAPI + Vue3 + SQLite）。

### 功能

- **企业与三大报表**：年报/季报 CRUD，CAS simplified v2 科目
- **年报导入**：PDF 识别映射 + 人审入库；Excel 模板导入；巨潮按代码/公司名称检索下载
- **比率分析**：13 项常用比率动态计算；角色视图；较上期变动（对齐当前报告期前一年）；趋势图可调 Y 轴
- **多期对比**：科目矩阵、环比/结构、KPI（万/亿）、变动榜、双轴/对数/自定义坐标
- **导出**：Excel（三表 + 财务比率）；HTML 快照 / 打印

### 技术

- 后端：FastAPI · SQLAlchemy · SQLite · pandas · openpyxl · pdfplumber
- 前端：Vue3 · TypeScript · Element Plus · ECharts · Vite
- 分层：`api → services → models`

### 已知限制

- 无多用户认证
- 港股 / EDGAR 与批量任务待增强
- 巨潮拉取请控制频率

