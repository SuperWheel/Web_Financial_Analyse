# Proposal 005: 财务比率分析与可视化

## Why

三大报表与年报导入已可用，系统尚未提供比率计算与分析页，核心「辅助决策」价值未闭环。

## What

1. 在 `core` 定义一组常用财务比率公式（不落库）。
2. `ratio_service` 按企业 + 报告期读取 L1 三表动态计算。
3. REST：`GET .../ratios`、`.../ratio-periods`、`.../ratios/history`。
4. 前端 `AnalysisView`：选企业/期间、比率卡片、ECharts 柱状/折线。

## Out of scope

- 多期同比环比完整对比页（Phase 4）
- 行业对标、自定义公式 UI
- 比率结果落库
