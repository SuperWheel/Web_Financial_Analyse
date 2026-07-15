# 公开财报识别与自动填入算法

> 目标：对**大部分**中国上市公司公开年报/中报（PDF 为主），自动识别三大报表并映射到本系统字段，经校验后写入。  
> 原则：**规则优先、词典可演进、置信度驱动、低置信不盲写**。

---

## 0. 问题定义

**输入**：一份公开财报文件 \(F\)（PDF/Excel）  
**输出**：结构化草稿

```text
Draft = {
  company: {name, code?},
  period: {year, period_type, quarter?},
  unit_scale: 1|1000|1e6,
  scope: consolidated|parent,
  standard: CAS|US_GAAP|IFRS|unknown,
  statements: {
    balance:  {field -> amount},
    income:   {field -> amount},
    cashflow: {field -> amount}
  },
  unmapped: [{statement, label, amount, reason}],
  confidence: 0..1,
  issues: [勾稽/冲突提示]
}
```

**成功标准（「大部分」）**：

| 档位 | 样本类型 | 自动填入目标 |
|------|----------|--------------|
| A | A 股 CAS 数字 PDF（科沃斯/影石同类） | 系统字段覆盖率 ≥ 85%，核心 12 项 100% |
| B | 港股/美股 GAAP 繁体数字 PDF（B 站同类） | 覆盖率 ≥ 60%，核心 8 项 ≥ 80% |
| C | CID/扫描/纯图片（小米同类） | 拒绝自动填入，引导替代源；不写脏数 |

核心 12 项（填入质量闸门）：

```
货币资金/现金, 应收, 存货, 流动资产合计, 资产总计,
流动负债合计, 负债合计, 所有者权益合计,
营业收入, 营业成本, 净利润,
经营活动现金流量净额
```

---

## 1. 总流程（七段管道）

```
F
│
├─① DocumentProfile   文档画像（可抽取性/语言/准则线索）
├─② StatementLocate   报表定位（页区间 + 表种 + 合并/母公司）
├─③ TableExtract      表抽取（表格 or 行文本 or 网格重建）
├─④ RowNormalize      行规范化（标签清洗 + 金额解析 + 列选择）
├─⑤ SubjectMap        科目映射（多级匹配 + 冲突消解）
├─⑥ Validate          校验（勾稽/覆盖率/置信度）
└─⑦ AutoFill          自动填入策略（直接写 / 待审 / 拒绝）
```

每一段输出带 `confidence` 与 `diagnostics`，下游可短路失败。

---

## 2. 段① DocumentProfile（文档画像）

### 2.1 可抽取性评分 \(Q \in [0,1]\)

对前 \(N=20\) 页（及全文抽样）：

```
text_chars     = 可提取字符数
cjk_ratio      = CJK字符 / max(text_chars,1)
cid_ratio      = 含 "(cid:" 或大量控制符 的比例
digit_ratio    = 数字字符比例
table_hit      = pdfplumber.extract_tables 非空页占比
```

启发式：

```
if cid_ratio > 0.02 or cjk_ratio < 0.15 and text_chars > 500:
    Q = 0.1   # 小米类 → 走拒绝/OCR 通道
elif table_hit > 0.05 and cjk_ratio > 0.3:
    Q = 0.9   # 科沃斯/影石类
elif cjk_ratio > 0.3 and digit_ratio > 0.05:
    Q = 0.65  # B 站类：有文本但表线弱
else:
    Q = 0.35
```

\(Q < 0.25\) → **终止自动填入**，返回 `needs_structured_source`。

### 2.2 准则/市场线索

| 信号 | 推断 |
|------|------|
| 「合并资产负债表」「单位：元 币种：人民币」「√适用 □不适用」 | CAS + A 股 |
| 「合併資產負債表」「美國公認會計準則」「美元」附註折算 | US_GAAP / 港股年报 |
| 「國際財務報告準則」「IFRS」 | IFRS |
| 文件名含 港交所/NASDAQ 代号 | 港美股权重+ |

`standard = argmax score`；置信不足则 `unknown`，后续用通用词典。

### 2.3 公司名线索

优先级：

1. 首页/页眉：`XXXX股份有限公司` / `XXXX有限公司` 最长匹配  
2. 「编制单位：」后文本  
3. 文件名去「20xx年报/年度报告」  

代码：正则 `港交所代號|股票代码|证券代码|股份代號[:：\s]*([0-9A-Z.]+)`。

---

## 3. 段② StatementLocate（报表定位）——关键算法

财报 PDF 很长（100~400 页），不能全页当表解析。用**标题状态机**切区间。

### 3.1 标题模式库（简繁等价）

```
BALANCE_TITLE = {
  strong: [合并资产负债表, 合併資產負債表, 合并财务状况表],
  weak:   [资产负债表, 資產負債表],
  parent: [母公司资产负债表, 母公司資產負債表],
  stop:   [合并利润表, 合併利潤表, 合并现金流量表, 财务报表附注, 合併財務報表附註, 母公司]
}

INCOME_TITLE = {
  strong: [合并利润表, 合併利潤表, 合并利润表及收益表,
           合併經營狀況及全面收益表, 合併經營狀況及全面（虧損）╱收益表,
           综合收益表, 合併損益表],
  weak:   [利润表, 利潤表],
  parent: [母公司利润表],
}

CASH_TITLE = {
  strong: [合并现金流量表, 合併現金流量表],
  weak:   [现金流量表, 現金流量表],
  parent: [母公司现金流量表],
}
```

匹配前：`normalize_title(s) = 繁转简 + 去空格 + 小写英文 + 压掉全角符号`。

### 3.2 扫描算法

```
state = NONE
segments = []  # {kind, scope, start_page, end_page, title_score}

for page in pages:
    titles = find_title_lines(page.text)  # 字号大/居中/或短行+关键字

    for t in titles:
        kind, scope, score = classify_title(t)
        if kind is None: continue

        # 关闭上一段
        close_open_segment(page_index - 1)

        # 母公司：仅当尚无 consolidated 时记录，否则 skip
        if scope == parent and has_consolidated(kind):
            continue

        open_segment(kind, scope, page_index, score)

    # 附注开始 → 关闭所有主表段
    if matches(page, 财务报表附注|合併財務報表附註|重要会计政策):
        close_all(page_index - 1)
```

同 kind 多段时：

```
prefer consolidated over parent
prefer higher title_score
prefer 更靠后、靠近审计报告之后的「正式报表」区
  （A股常见：第八节 财务报告 之后）
```

输出：`segments = {balance, income, cashflow}` 各至多 1 个**合并**区间。

### 3.3 「大部分适用」的关键技巧

- A 股模板高度同构：强标题命中率极高（样本已验证）。  
- 港股：标题在页眉重复 → 用**首次出现页**作 start，直到下一强标题。  
- 若只找到 weak 标题且无「合并」：仍可用，但 `scope_confidence` 降低。

---

## 4. 段③ TableExtract（双通道抽取）

### 通道 A：网格表（CAS 主路径）

对 segment 内每页：

```
tables = pdfplumber.extract_tables(page)
keep tables where:
  - 列数 >= 3
  - 首行或次行含 项目/附注/年|月|日|年度
  - 数据行中金额单元格占比 > 0.3
```

跨页拼接：

```
if page_i table 无表头 and 列数 == prev列数 and prev.kind 未结束:
    append rows to prev
```

### 通道 B：行文本（GAAP/表线失败）

对 segment 文本行：

```
line' = 合并多空格
if is_section_header(line'):  # 以冒号结尾或「一、」「流动资产：」
    emit section row
elif match amount_line(line'):
    label, nums[] = split_label_and_numbers(line')
    emit data row
```

金额 token 正则：

```
[（(]?\s*-?\d{1,3}(?:,\d{3})*(?:\.\d+)?\s*[)）]? | —
| -
```

### 通道选择

```
if channelA.rows >= 15 and channelA.amount_parse_rate > 0.5:
    use A
elif channelB.rows >= 15:
    use B
else:
    merge(A,B) by label union, prefer A amounts
```

---

## 5. 段④ RowNormalize（行规范化）

### 5.1 列角色识别

对表头行打分：

| 角色 | 特征 |
|------|------|
| label | 「项目」「項 目」或首列大量 CJK |
| note | 「附注」「附註」「Notes」 |
| current | 最大年份 / 「期末」「本年」「本期」「2025年12月31日」「2025年度」 |
| prior | 次大年份 / 「期初」「上年」「上期」 |
| fx | 「美元」「港元」「USD」→ **默认丢弃** |

无表头时：`col0=label`，`col_last_numeric_non_fx=current`。

### 5.2 标签清洗 \(\mathrm{norm}(label)\)

有序变换：

```
1. 繁体 → 简体（OpenCC t2s）
2. 去换行/零宽字符/全角空格
3. 统一括号：（）→()
4. 去掉行号前缀：^\d+\.|^[一二三四五六七八九十]+、
5. 去掉尾注：\(净额\)|（淨額）|（亏损以.*）|以“-”号填列
6. 压缩空白
7. 可选：去掉「其中：」前缀生成 secondary_key（用于优先级）
```

### 5.3 金额解析

```
parse_amount(s):
  if s in {None,'','—','–','-'}: return None
  neg = 有会计括号 (1,234.56) 或 前导 -
  去千分位逗号、货币符号、空格
  float → 若 neg: -abs
```

### 5.4 单位

页眉/表题扫描：

```
if 千元|以千元为单位|金额以千元: scale=1000
elif 百万元|百萬元: scale=1_000_000
elif 单位：元|單位：元: scale=1
else: scale=1  # 并降低 confidence
amount_yuan = amount * scale
```

### 5.5 规范化行结构

```
NormRow = {
  raw_label, norm_label,
  amount_yuan,          # 选用 current 列
  prior_yuan?,
  is_section: bool,     # 无金额且以：结尾 或 匹配「流动资产：」「一、经营活动」
  is_total: bool,       # 含 合计/总计/净额/總額
  line_no?
}
```

过滤：`is_section and amount is None` 保留作结构上下文，不参与金额映射。

---

## 6. 段⑤ SubjectMap（科目映射）——核心算法

### 6.1 词典结构

```yaml
# core/subject_aliases.yaml
balance:
  monetary_funds:
    aliases: [货币资金, 现金及现金等价物, 现金及现金等价物净额?]
    # 注意：B站「现金及现金等价物」→ monetary_funds（系统无独立 cash_equiv）
    priority: 100
    tags: [core]
  accounts_receivable:
    aliases: [应收账款, 应收账款(净额), 应收帐款]
    priority: 100
  total_assets:
    aliases: [资产总计, 资产合计, 资产总额, 总资产]
    priority: 100
    tags: [core, total]
income:
  operating_revenue:
    aliases: [营业收入, 营业总收入, 净营业额, 主营业务收入]
    # 冲突规则见 6.3
    priority: 90
  net_profit:
    aliases: [净利润, 净收益, 净(亏损)/收益, 本期净利润]
cashflow:
  net_cash_flow_operating:
    aliases: [经营活动产生的现金流量净额, 经营活动产生的现金流量净额(净额)]
```

每个系统字段：`aliases[]`、`priority`、`statement`、`tags`。

### 6.2 多级匹配打分

对每个 `NormRow`（非 section）对每个候选字段 \(f\)：

```
score(row, f) =
  1.00  if norm_label == alias_norm          # 精确
  0.92  if norm_label == alias_norm 去「合计/总计」对称
  0.85  if alias_norm 是 norm_label 的前缀/去括号后相等
  0.75  if alias_norm in norm_label and len(alias)>=4
  0.60  if token_set_f1(norm_label, alias) >= 0.8
  0.00  else

# 惩罚
- 0.25  if row.is_total XOR f.tags.contains(total)   # 合计行对非合计字段
- 0.15  if 行处于错误大类上下文
        （如在「流动负债」section 下却匹配资产字段——见 6.4）
- 0.10  if 仅模糊命中且金额为空
```

取 `score >= 0.75` 的最佳字段；若 top1 - top2 < 0.05 → **歧义**，进 unmapped 或人工。

### 6.3 冲突消解规则（CAS 高频）

| 现象 | 规则 |
|------|------|
| 同时有「营业总收入」与「其中：营业收入」 | 映射 `operating_revenue` ← **其中：营业收入**；总收入作 fallback |
| 「四、净利润」与「归属于母公司所有者的净利润」 | 系统仅一字段：优先 **净利润（合计）**；若只有归母则用归母并标记 `approx` |
| 「资产总计」与「负债和所有者权益总计」 | 都可作 total_assets 校验；写入字段用「资产总计」 |
| 「现金及现金等价物」vs「货币资金」 | 有「货币资金」用它；否则现金及等价物 → monetary_funds |
| 金融模板空行（结算备付金等） | 无金额则忽略；有金额但无系统字段 → unmapped |
| 一行多义（预付款项及其他流动资产） | 不自动拆分；整行 unmapped 或映射到 `other_current_assets`（低置信） |

### 6.4 结构上下文（section stack）

扫描顺序维护栈：

```
遇到 section「流动资产：」→ context=asset.current
「非流动资产：」→ asset.noncurrent
「流动负债：」→ liability.current
「所有者权益：」→ equity
「一、经营活动」→ cash.operating
...
```

字段元数据带 `allowed_context`；不匹配则降权。  
这使「其他」类科目在正确区块内更准。

### 6.5 一对多与多对一

- **多源行 → 一字段**：取 score 最高且金额非空；记录 `sources[]`。  
- **一行 → 多字段**：禁止自动拆分（避免幻觉）。  
- 已占用字段：后行若 score 更高可覆盖，并记 `overwritten_by`。

### 6.6 映射输出

```
MappedField = {
  field, amount, confidence,
  source_label, source_page,
  rule: exact|alias|fuzzy|context
}
coverage = mapped_core / core_total
```

---

## 7. 段⑥ Validate（校验）

### 7.1 硬门槛（不通过则不自动入库）

```
H1: 至少一个 statement 的 mapped 字段数 >= 5
H2: 核心字段命中数 >= 6（档位 A 要求 10）
H3: unit_scale 已识别或用户确认
H4: year 在 [1990,2100] 且 period 合法
H5: Q >= 0.25
```

### 7.2 软勾稽（警告不阻断）

```
BS1: |total_assets - (total_liabilities + total_equity)| 
     <= max(1.0, 0.005 * |total_assets|)
IS1: 若有 operating_revenue 与 net_profit：|net_profit| <= 5 * |operating_revenue|
     （极端异常提示 OCR/列错）
CF1: 若三项净额齐全：
     |op+inv+fin - net_increase| 相对误差（可选，缺汇率项时常失败）
```

### 7.3 综合置信度

```
C = 0.25*Q
  + 0.25*locate_score
  + 0.30*mean(mapped.confidence)
  + 0.20*coverage
  - 0.10*num_hard_warnings_normalized
```

---

## 8. 段⑦ AutoFill（自动填入策略）

```
if C >= 0.80 and hard_pass and soft_bs_ok:
    mode = AUTO_COMMIT_CANDIDATE
    # 仍建议 UI 一键确认；API 可提供 auto_commit=true
elif C >= 0.55 and hard_pass:
    mode = REVIEW_REQUIRED   # 预填表单，用户点保存
else:
    mode = REJECT_OR_MANUAL
```

### 8.1 写入步骤（确认后）

```
1. upsert Company(name, code)
2. for kind in balance, income, cashflow:
     payload = {year, period_type, quarter, **mapped_fields}
     if exists(same period):
        if policy == overwrite: update
        else: skip
     else: create via statement_service
3. 记录 ImportJob.committed_ids, status=committed
```

### 8.2 预填 UI

直接填充现有会计表格式编辑器（StatementsView 同源组件）：  
已映射字段写入 `amounts[field]`；未映射列表侧栏展示，支持拖拽绑定字段。

---

## 9. 伪代码（端到端）

```python
def import_filing(path: Path) -> Draft:
    doc = open_document(path)
    profile = build_profile(doc)
    if profile.extractability < 0.25:
        return Draft.fail("PDF 文本不可靠，请上传巨潮 Excel/XBRL 或使用 OCR")

    segments = locate_statements(doc, profile)
    if not segments:
        return Draft.fail("未定位到三大报表标题")

    raw = {}
    for kind, seg in segments.items():
        rows_a = extract_grid(doc, seg)
        rows_b = extract_lines(doc, seg)
        raw[kind] = choose_channel(rows_a, rows_b)

    norm = {k: normalize_rows(v, profile) for k, v in raw.items()}
    mapped, unmapped = map_subjects(norm, load_alias_dict())
    draft = assemble_draft(profile, mapped, unmapped)
    draft = validate(draft)
    draft.fill_mode = decide_fill_mode(draft)
    return draft
```

---

## 10. 为何能覆盖「大部分」财报

| 覆盖层 | 手段 | 解决的对象 |
|--------|------|------------|
| 模板层 | A 股强标题 + 标准 4 列表格 | 约 80%+ A 股数字年报 |
| 文本层 | 行解析 + 繁简 | 港股/部分美股中文年报 |
| 语义层 | 同义词词典 + section 上下文 | 科目别名、合计行 |
| 单位层 | 元/千元/百万显式识别 | 披露口径差异 |
| 质量层 | 置信度 + 勾稽 + 人审闸门 | 长尾脏数据 |
| 降级层 | 拒绝 CID/扫描 | 避免错误自动填入 |

**不声称 100%**。长尾靠：词典增补、用户一次纠正回写别名（可选学习）、Excel/XBRL 旁路。

---

## 11. 词典冷启动清单（实施时必须内置）

至少为系统全部 ~65 个金额字段各配置 ≥1 个别名；核心字段 ≥3 个（简体标准名 + 合计变体 + 繁体/GAAP 变体）。

建议维护方式：

- `subject_aliases.yaml` 版本化进仓库  
- 单测：用科沃斯/影石/B 站三份 fixture 断言核心字段金额（允许单位换算后比较）  
- 每多支持一家「失败年报」→ 只加别名/规则，不改管道骨架  

---

## 12. 与实现模块的映射

| 算法段 | 建议代码 |
|--------|----------|
| ① Profile | `services/importing/profile.py` |
| ② Locate | `services/importing/locate.py` |
| ③ Extract | `services/importing/extractors/cas_ashare.py`, `gaap_hk.py` |
| ④ Normalize | `services/importing/normalize.py` |
| ⑤ Map | `services/importing/mapper.py` + `core/subject_aliases.yaml` |
| ⑥ Validate | `services/importing/validate.py` |
| ⑦ Fill | `services/importing/pipeline.py` → `statement_service` |

---

## 13. 验收用例（算法级）

1. **科沃斯 PDF** → locate 三表；`货币资金/资产总计/营业收入/净利润/经营现金流净额` 与年报一致（元）。  
2. **影石 PDF** → 不取母公司表；合并净利润正确。  
3. **B 站 PDF** → scale=1000；`淨營業額→operating_revenue`；`現金及現金等價物→monetary_funds`。  
4. **小米 PDF** → `fill_mode=REJECT`，无 business 表写入。  
5. **故意缺页/截断 PDF** → hard fail，不半写入。

---

## 14. 一句话总结

> **用标题状态机定位报表，用「表格优先、行文本兜底」抽数，用「清洗 + 多级别名 + 区块上下文」映射到系统科目，用置信度与会计勾稽决定能否自动填入。**  

这套算法不依赖单一版式，通过分层覆盖 A 股主体与港美股中文年报长尾，并在不可靠输入上安全失败。
