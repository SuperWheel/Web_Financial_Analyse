# Design 003: 公开财报导入通用方案

## 1. 问题本质

公开年报**不是一种格式**，而是「披露载体 × 会计准则 × 版式 × 抽取质量」的组合：

```
载体：PDF 数字版 | PDF 扫描/CID 字体 | Excel | XBRL
准则：CAS（A股） | IFRS（港股常见） | US GAAP（中概/美股）
版式：合并表 vs 母公司表 | 单位元/千元/百万元 | 简繁体 | 多期并列
```

因此**不存在「一个正则吃天下」**；通用方案必须是**管道 + 适配器 + 人审**。

**识别与自动填入的详细算法**见同目录 [`algorithm.md`](./algorithm.md)（七段管道：画像→定位→抽取→规范化→映射→校验→填入）。

## 2. 总体架构

```
┌──────────────┐   ┌─────────────────┐   ┌──────────────────┐
│ 接入层        │→ │ 抽取层            │→ │ 标准化层           │
│ 本地上传 PDF  │   │ 版式检测          │   │ 简繁转换          │
│ (后续:巨潮/   │   │ 表定位            │   │ 单位换算→元       │
│  东财 Excel)  │   │ 表格/行解析适配器  │   │ 科目同义词映射     │
└──────────────┘   └─────────────────┘   └────────┬─────────┘
                                                   ↓
┌──────────────┐   ┌─────────────────┐   ┌──────────────────┐
│ 落库层        │← │ 人审确认 UI       │← │ 草稿层             │
│ Company+三表  │   │ 映射修正/忽略     │   │ ImportJob+预览JSON │
│ CRUD 复用     │   │ 勾稽提示          │   │ 覆盖率/未映射清单  │
└──────────────┘   └─────────────────┘   └──────────────────┘
```

分层仍遵守：`api → services → models`；解析逻辑放 `services/importing/`，不进路由。

## 3. 核心抽象

### 3.1 ImportJob（导入任务）

| 字段 | 说明 |
|------|------|
| id | PK |
| source_type | `pdf_upload` / `excel_upload` / `xbrl`（预留） |
| file_path | 本地存储路径（`data/imports/`） |
| status | `uploaded` → `parsing` → `mapped` → `review` → `committed` / `failed` |
| company_hint | 从文件名/页眉解析的公司名 |
| report_year / period_type / quarter | 报告期推断 |
| accounting_standard | `CAS` / `US_GAAP` / `IFRS` / `unknown` |
| unit_scale | `1` / `1000` / `1000000` |
| scope | `consolidated` / `parent`（合并优先） |
| raw_extract | JSON：原始表行 |
| mapped_draft | JSON：映射到系统字段的草稿 |
| coverage | 映射覆盖率统计 |
| error_message | 失败原因 |

### 3.2 解析适配器（Strategy）

```python
class StatementExtractor(Protocol):
    def detect(self, doc: Document) -> float: ...   # 置信度 0~1
    def extract(self, doc: Document) -> ExtractResult: ...
```

一期实现：

| 适配器 | 适用 | 方法 |
|--------|------|------|
| `CasAsharePdfExtractor` | A 股 CAS 数字 PDF | pdfplumber 表格；标题锚定「合并资产负债表/合并利润表/合并现金流量表」；取合并表，跳过母公司表 |
| `GaapHkPdfExtractor` | 港股/美股繁体 PDF | 行文本解析（表格线常失败）；标题「合併資產負債表/合併經營狀況/合併現金流量表」；取人民币列、最近年度 |
| `ExcelTemplateExtractor` | 系统导出模板 / 东财导出 | openpyxl 按固定 sheet |
| `OcrPdfExtractor`（二期） | CID/扫描件（小米类） | 可选：pdf2image + OCR；或提示用户改用巨潮 XBRL/Excel |

路由：`max(detect)` 且 ≥ 阈值，否则 `unknown` 进入人工选择。

### 3.3 科目映射词典（核心资产）

`core/subject_aliases.yaml`（或 JSON）：

```yaml
balance_sheet:
  monetary_funds:
    - 货币资金
    - 現金及現金等價物      # B站把现金等价物并在此，需规则：可映射到 monetary_funds
    - 现金及现金等价物
  accounts_receivable:
    - 应收账款
    - 應收賬款
    - 應收賬款（淨額）
  total_assets:
    - 资产总计
    - 资产合计
    - 資產總額
    - 總資產
  # ...
income_statement:
  operating_revenue:
    - 营业收入
    - 其中：营业收入
    - 营业总收入          # 规则：若同时有「其中：营业收入」优先子项
    - 淨營業額
    - 净营业额
  net_profit:
    - 净利润
    - 四、净利润
    - 淨（虧損）╱收益
    - 净收益
```

映射算法：

1. 行标签规范化：去空格/换行/全半角、简繁转换、去「（净额）」「其中：」可选前缀。
2. 精确匹配 → 包含匹配 → 编辑距离模糊（阈值）。
3. 输出：`{system_field, source_label, amount, confidence, rule}`。
4. 未映射行进入 `unmapped[]`，UI 可手工指定或忽略。

### 3.4 单位与期间

- 从页眉/表头识别：`单位：元` / `金额以千元为单位` / `百万元` → `unit_scale`。
- 入库前：`amount * unit_scale`，系统统一存**元**。
- 期间：优先表头「2025年12月31日」「2025年度」；年报默认 `period_type=annual, quarter=null`。
- 多列年份：默认取**最近报告期列**；UI 可切换「同时导入上年比较数」。

### 3.5 合并 vs 母公司

A 股年报常连续出现「合并资产负债表」与「母公司资产负债表」。

规则：**默认只取标题含「合并」的表**；若只有一套则取之。UI 显示 scope，允许用户改选。

## 4. 抽取流程（CasAshare 主路径）

```
1. pdfplumber 打开 PDF
2. 扫页文本，记录标题页码：
   - 合并资产负债表 / 合并利润表 / 合并现金流量表
   - 遇到「母公司资产负债表」则停止当前合并表区间
3. 对每个表区间：
   a. extract_tables()；若空则按文本行 split 数字
   b. 识别表头列：项目、附注、期末/本年、期初/上年
   c. 输出 rows: [{label, note, current, prior}]
4. 汇总 ExtractResult
```

B 站路径差异：

- 表格线不可靠 → 用正则：`^(.+?)\s+([\d(),.-]+)\s+([\d(),.-]+)`
- 货币列：跳过美元列，取人民币最近年度
- 标签简繁转换后进同一映射词典

小米路径：

- `detect` 若乱码率高（CJK 比例低 / cid 特征）→ 标记 `needs_ocr_or_structured_source`
- 一期 UI 提示：「该 PDF 无法可靠抽取，请上传巨潮/交易所 Excel，或使用 OCR（二期）」

## 5. API 设计

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/imports/filings` | multipart 上传 PDF/Excel，创建 ImportJob，异步或同步解析 |
| GET | `/api/imports/filings/{id}` | 任务状态 + 草稿 + 未映射清单 |
| PATCH | `/api/imports/filings/{id}/mapping` | 用户修正字段映射/报告期/企业 |
| POST | `/api/imports/filings/{id}/commit` | 确认入库（调现有 statement_service） |
| DELETE | `/api/imports/filings/{id}` | 放弃任务 |

Commit 行为：

1. 若 `company_id` 空：按名称/代码查找或创建 Company。
2. 对三表分别 `create` 或「已存在则更新」（UI 勾选策略：`skip` / `overwrite`）。
3. 返回写入的 statement ids。

## 6. 前端交互

入口：三大报表页增加「从年报导入」按钮；或独立「导入」页。

步骤条：

1. **上传**（拖拽 PDF）
2. **识别结果**：准则/单位/公司/年份/合并范围/三表命中情况
3. **映射预览**：会计表格式展示（复用 StatementsView 纸面样式），未映射高亮
4. **确认入库**

覆盖率提示示例：`资产负债表 28/32 已映射 · 利润表 15/18 · 现金流量表 12/15`

## 7. 依赖

| 库 | 用途 | 阶段 |
|----|------|------|
| pdfplumber | 数字 PDF 文本/表 | 一期必选 |
| openpyxl | Excel | 一期可复用（已在 requirements） |
| opencc-python-reimplemented | 繁简转换 | 一期推荐 |
| pypdf | 页级辅助 | 可选 |
| pdf2image + 本地 OCR | CID/扫描 | **二期**，不默认强依赖系统 poppler |

**不引入**重型 LLM 作为主路径；可选后续「映射失败时 LLM 建议」，但词典优先（可测、可复现）。

## 8. 验收样本与成功标准

| 样本 | 一期目标 |
|------|----------|
| 科沃斯 PDF | 自动识别三表；核心科目（货币资金/应收/存货/资产总计/营收/净利/经营现金流净额等）映射正确；单位元；合并表 |
| 影石创新 PDF | 同上；不误导入母公司表 |
| 哔哩哔哩 PDF | 识别 US GAAP 繁体；千元→元；至少核心科目映射；允许部分未映射 |
| 小米 PDF | 明确失败/降级提示，不产生错误入库 |

数值校验（软提示，不阻断）：

- 资产负债表：`total_assets ≈ total_liabilities + total_equity`（容差 1 元或 0.5%）
- 若系统有合计字段且勾稽失败 → review 页黄灯

## 9. 风险与权衡

| 风险 | 应对 |
|------|------|
| 版式多变 | 适配器 + 置信度 + 人审，不做静默入库 |
| 科目口径不一致（淨營業額 vs 营业收入） | 同义词词典 + 规则优先级 + 未映射暴露 |
| 合并/母公司误取 | 标题区间切割 + UI 明示 scope |
| CID/扫描 PDF | 一期拒绝并引导结构化源；二期 OCR |
| 法律/版权 | 仅处理用户主动上传的公开文件；不做站点批量爬取 |
| 复杂度膨胀 | 一期只做「上传 PDF + CAS 主路径 + 人审 commit」 |

## 10. 与现有系统衔接

- 落库复用 `statement_service.create_*`，不另写 SQL。
- 科目集合以 Phase 1 CAS 简化版为准；年报多出的行（结算备付金、一般风险准备等）→ unmapped，不阻塞。
- 比率分析（原 Phase 2）在导入可用后更有价值 → 建议顺延为 Phase 3。

## 11. 实施切片（建议任务序）

1. ImportJob 模型 + 文件落地 `data/imports/`
2. `CasAsharePdfExtractor` + 单测（以科沃斯/影石 PDF fixture）
3. 映射词典 + 单位/期间规范化
4. API：upload / get / commit
5. 前端向导 UI
6. `GaapHkPdfExtractor`（B站）
7. 小米降级提示 + Excel 适配器
8. （可选二期）OCR / 巨潮结构化拉取
