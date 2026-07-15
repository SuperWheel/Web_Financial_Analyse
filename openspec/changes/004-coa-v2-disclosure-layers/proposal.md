# Proposal 004: CAS-simplified-v2 + 披露明细层

## Why

公开年报科目远多于 Phase 1 的 CAS 简化列。导入后大量行进 unmapped，且部分 v1 字段因别名缺失映射失败。需要有界扩列 + 原文行留存，支撑后续比率分析。

## What

1. **CAS-simplified-v2**：L1 三表扩约 21 个高频标准科目。
2. **别名热修**：补齐实收资本/资本公积/盈余公积/未分配利润等 v1 别名。
3. **L0 披露明细表**：`statement_disclosure_lines` 全量保留导入行与映射关系。
4. **受控映射**：alias + 显式 rollup；禁止模糊静默匹配。
5. **locate 修复**：「（续）」页不覆盖表头页。

## Out of scope

- 比率计算 UI（Phase 3）
- 金融专用模板
- OCR / 巨潮批量爬取
