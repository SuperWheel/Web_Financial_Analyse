# Proposal 006: 科目级多期对比

## Why

比率分析（变更包 005）已能看指标趋势与本期/上期，但缺少**三大报表科目金额**的多期对照与同比/结构分析，无法回答「资产/收入/现金流哪些项目在变」。

## What

1. `compare_service`：按企业 + 报表类型 + 报告期类型读取多期 L1 科目，计算环比变动与结构占比（不落库）。
2. REST：`GET .../compare-periods`、`GET .../compare`。
3. 前端 `CompareView`：选企业/报表/期间，科目对照表 + 关键科目趋势图。

## Out of scope

- Excel 导入导出（Phase 5）
- 行业对标、自定义科目树
- 季报与年报混比
- 比率多期（已在 005 history）
