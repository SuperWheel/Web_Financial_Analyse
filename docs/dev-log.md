# 开发日志 (dev-log)

> 每次对话后用 3 分钟整理一份记录（来源：《AI Coding 开发规范》第三金律）。最新在上。

---

## [2026-07-18] Phase B3/B5 + C2/C3 —— 门禁收尾与视图拆分完成

**B3 ESLint**：`eslint.config.js` flat 最小规则；`npm run lint` 0 errors；CI/check 接入。  
**B5 烟测**：`test_e2e_smoke.py` 企业→三表→比率→对比；pytest **61 passed**。  
**C2 Compare**：1283→230；`useStatementCompare` + 4 组件。  
**C3 Analysis**：2393→258；`useRatioAnalysis` + 6 组件；修 PeriodComparePanel 模板 TS。  

**验证**：lint / type-check / vitest 9 / build 全绿；backend 61 passed。  

**下一步**：Phase D（DB 备份 + PDF 黄金样本）。

---

## [2026-07-18] Phase B4 —— 前端关键纯函数单测

**需求简述**：为覆盖率聚合与同比上期定位加 Vitest，防回归。

**实现**：
- 引入 `vitest@2.1.9`；`npm test` / `test:watch`
- `importCoverage.spec.ts`（5）+ `ratioInsights.spec.ts`（4）= **9 passed**
- CI frontend job 与 `scripts/check.sh` 增加 unit tests 步骤

**验证**：`npm test` 9 passed。

**下一步**：B3 ESLint（可选）或 D 黄金样本 / C2 Compare。

---

## [2026-07-18] Phase C1c —— StatementDraftTables + useImportReviewQueue

**需求简述**：收尾 ImportView 拆分：三表 draft 展示 + 核对队列 composable。

**实现**：
- `components/import/StatementDraftTables.vue`
- `composables/useImportReviewQueue.ts`（队列/软保存/单份与批量入库）
- `ImportView.vue` 瘦身为 tab 壳：**~245 行**（原 ~1600）

**验证**：type-check + build 通过。

**下一步**：C1 可宣告完成；可选 B4 单测或 C2 CompareView。

---

## [2026-07-18] Phase C1b —— 抽出 CninfoSearchPanel

**需求简述**：继续拆 ImportView，在线拉取 tab 整段下沉。

**实现**：
- `components/import/CninfoSearchPanel.vue`：巨潮检索/勾选导入/PDF 直链/新建企业
- 与父通信：`v-model:company-id` + `@review-jobs` → `enterReviewQueue`
- `ImportView.vue`：~1086 → ~522 行

**验证**：type-check + build 通过。

**下一步**：可选 StatementDraftTables / useImportReviewQueue；或 B4 单测。

---

## [2026-07-18] Phase C1 —— 拆分 ImportView

**需求简述**：降低 ImportView 体积，抽出边界清晰的展示/子域组件，行为不变。

**实现**：
- `utils/importCoverage.ts`：覆盖率/金额/原因纯函数
- `components/import/MappingQualityPanel.vue`：映射质量 + unmapped
- `components/import/ReviewQueueNav.vue`：多年核对队列导航
- `components/import/ExcelImportPanel.vue`：Excel 模板导入整 tab
- `ImportView.vue`：~1600 → ~1087 行，编排 fetch/PDF 主流程

**验证**：`npm run type-check` / `build` 通过。

**下一步**：可选再抽 CninfoSearchPanel / useImportReviewQueue；或 B3/B4。

---

## [2026-07-18] Phase B2 —— 后端 Ruff 最小门禁

**需求简述**：CI/本地增加后端静态检查，只拦明显错误，不全仓格式化。

**实现**：
- `backend/ruff.toml`：E+F，忽略 E501
- `requirements-dev.txt` 固定 `ruff==0.15.22`
- 修 F401/F841：`ratio_service` 未用模型导入、`http_util` 未用变量
- `scripts/check.sh`：1/4 ruff → pytest → type-check → build
- CI backend job：Install 后 `ruff check app tests` 再 pytest

**验证**：`ruff check app tests` OK；`pytest` 60 passed。

**下一步**：push 确认 Actions 绿；B3 ESLint 或 C1 拆 ImportView。

---

## [2026-07-18] Phase B1 —— GitHub Actions CI

**需求简述**：把本地 `scripts/check.sh` 接到远程自动门禁。

**实现**：
- 新增 `.github/workflows/ci.yml`
- 触发：`push` / `pull_request` → `main`
- 并行 jobs：
  - backend：Python 3.12 + pip cache · `requirements.txt` + `requirements-dev.txt` · `pytest -q`
  - frontend：Node 22 + npm cache · `npm ci` · `type-check` · `build`
- README / AGENTS / 可靠性计划标注 CI 入口

**验证**：workflow YAML 就位；本地命令集此前已由 check.sh 跑绿。push 后看 Actions 是否全绿。

**下一步**：确认 Actions 绿；可选 B2 Ruff / B3 ESLint，或 C1 拆 ImportView。

---

## [2026-07-18] Phase A4 —— 切片提交 post-1.0 工作区

**需求简述**：将 ~2k 行混合未提交改动按可验证切片 commit。

**提交（main ahead 5，未 push）**：
1. `8dec51b` fix(import): prefer cover issuer over related-party names
2. `d5665b4` feat(fetch): CNINFO multi-year batch download and industry prefill
3. `52cc926` feat(import): review queue, mapping quality, and unmapped table
4. `6c9be53` chore: restore frontend build gate and add scripts/check.sh
5. `e198081` docs: archive evaluation, reliability plan, and post-1.0 status

**验证**：提交前 `./scripts/check.sh` 全绿；提交后工作区干净。

**下一步**：Phase B CI；或按需 push。

---

## [2026-07-18] Phase A —— 恢复可靠交付（A1–A3/A5）

**需求简述**：按可靠性计划执行 Phase A：修编译债、恢复门禁、一键检查、文档对齐。

**完成**：
- **A1**：`ImportView` Excel 期间列抽 `formatPeriodLabels`，去掉模板内 TS 注解。
- **A2**：安装 Node 22；清 `vue-tsc -b` 存量错误（excel/export content-type、upload onError、ratioInsights 历史点类型、Analysis/Compare 未用变量与模板类型）。
- **A3**：新增 `scripts/check.sh`（pytest → type-check → build；自动找 venv/node@22）。
- **A5**：`openspec/project.md` / `AGENTS.md` P2 标「进行中」；README 补 Node 要求与 check 入口；计划状态更新。

**验证**：`./scripts/check.sh` → **60 passed** + type-check + build **全绿**。

**未做（A4）**：工作区仍为大批量未切片提交；需用户确认后再按 010 / 公司名 / UX / 文档 分 commit。

**下一步**：A4 切片提交 → Phase B CI。

---

## [2026-07-18] Plan —— Post-1.0 可靠性修改计划

**需求简述**：针对评价文档中的问题，制定可执行修改计划。

**产物**：`docs/plans/2026-07-18-post1.0-reliability-plan.md`

**结构**：
- Phase A（P0）：修模板 TS、恢复 type-check/build、check.sh、按切片提交未提交改动、文档对齐
- Phase B：CI + 最小 Ruff/ESLint + 关键纯函数单测
- Phase C：Import → Compare → Analysis 拆分（行为不变）
- Phase D：DB 备份、PDF 黄金样本、L0 追溯
- Phase E：核对编辑 / 同比边角 → 港股 / EDGAR（延后）

**第一刀**：A1 修 ImportView Excel 期间列注解 → A2 工具链 → A4 拆 commit。

---

## [2026-07-18] Docs —— 审阅并归档项目评价

**需求简述**：分析《项目评价与改进建议》是否有理，加今日日期并归档。

**审阅结论**：总体有道理，可作 post-1.0 工程优先级参考。
- **成立**：闭环/人审/L0L1/分层/60 测/巨型视图行数/缺 CI/ADD COLUMN 迁移/未提交 ~1989 行/`ImportView` 模板 TS 注解/暂缓多用户云行情 等均与仓库一致。
- **限定**：「前端无法编译」→ 交付门禁未闭环（语法债+本机 node 缺失）；P2 核对页 unmapped 当日已部分完成。
- **采纳**：Phase A→D 先稳 CAS 主路径；E 再港股/EDGAR；不并行大拆+扩准则。

**归档**：根目录原稿 → `docs/archive/2026-07-18-项目评价与改进建议.md`（文首归档元数据 + 附录核对意见）。

**下一步（Phase A）**：修 Excel 预览模板类型注解；恢复 type-check/build；按切片提交未提交改动。

---

## [2026-07-18] Docs —— 项目评价与改进建议

**需求简述**：对当前项目进行整体评价，并在项目根目录形成可执行的 Markdown 建议文档。

**模式**：Vibe（仅文档）

**主要内容**：
- 从产品闭环、架构、测试、数据可靠性和可维护性评价当前项目。
- 区分 v1.0.0 基线与当前 post-1.0 在研工作区状态。
- 记录后端 `60 passed` 以及当前前端模板编译错误。
- 给出恢复交付、质量门禁、前端拆分、数据可靠性和产品增强五阶段路线。
- 补充各阶段验收标准、建议指标及暂缓事项。

**变更文件**：`项目评价与改进建议.md`、`docs/dev-log.md`

**验证**：检查 Markdown 标题层级、代码块、表格与任务清单结构。

---

## [2026-07-17] Vibe —— 导入核对页映射质量 / unmapped

**需求简述**：P2 导入体验修补——核对页此前不展示后端已有的 `coverage` / `unmapped` / `issues`，入库前难判断映射质量。

**模式**：Vibe（前端为主，后端字段已齐）

**关键决策**：
- 核对页新增「映射质量」区块：三表核心科目覆盖进度条、总体覆盖%、置信度、问题条数。
- 未映射科目表：原文科目 / 金额 / 页 / 原因（中文）；按报表筛选。
- 状态条带上覆盖率；覆盖 < 50% 时单份/批量入库二次确认。
- API 类型收紧：`CoverageStats` / `UnmappedRow`。

**变更文件**：`frontend/src/api/importFiling.ts`、`frontend/src/views/ImportView.vue`、`docs/dev-log.md`

**验证**：
- 浏览器注入 job `#29`：显示「核心科目覆盖 100%」「未映射科目（200）」「置信度 97%」及原因标签；按表筛选计数一致。
- 覆盖率聚合逻辑单元烟测：hit/total 与 pct 正确。

**下一步**：分析同比边角 / 导入核对可编辑金额；或港股 GAAP（P3）。

---

## [2026-07-16] Fix —— 年报公司名识别成关联方（红旗连锁）

**现象**：巨潮下载永辉（601933）年报后，核对页公司名显示「成都红旗连锁股份有限公司」。

**根因（非下错年报）**：
1. 文件名/代码正确：`601933_*_永辉超市…pdf`，`company_code_hint=601933`。
2. PDF 封面是永辉；释义表有「红旗连锁 指 成都红旗连锁股份有限公司」。
3. `guess_company_name` 在前 25 页全文里按「含股份+最长」排序，关联方全称更长 → 误选。
4. `create_job_from_upload` 合并策略「解析优先」，错误名覆盖了巨潮预填简称。

**修复**：
- `guess_company_name`：优先法定中文名/封面前 800 字最早发行人；跳过「简称 指 全称」释义行；`公司代码` 纳入股票代码正则。
- `build_profile`：公司/代码/年份优先封面+前几页。
- 巨潮/URL 拉取：`company_hint/code/year` **预填优先**于解析结果。

**验证**：✅ 永辉 2024 profile → 永辉超市股份有限公司 / 601933；`pytest` import+fetch **20 passed**。

---


## [2026-07-16] Vibe —— 在线拉取多年预览 + 批量确认入库

**需求简述**：「导入勾选」只下载建 job，未进入核对/入库；需要多年预览左右切换与批量确认入库。

**模式**：Vibe（前端 ImportView）

**关键决策**：
- 下载解析成功后 `enterReviewQueue`：自动跳转「年报 PDF」核对页，绑定可选 `company_id`。
- 多 job 队列：上一份/下一份 + 年份芯片切换；切换前软保存当前 draft。
- 操作：**确认本份入库** / **批量确认入库（N）**；`commit` 时传入关联企业。
- 单份上传 PDF 也走同一队列路径。

**变更文件**：`frontend/src/views/ImportView.vue`、`docs/dev-log.md`

**验证**：`bun run type-check` 通过。

**下一步**：核对页展示 unmapped / 覆盖率；或港股 GAAP。

---


## [2026-07-16] Vibe —— 在线拉取 UX：统一年份 + 勾选导入 + 新建企业

**需求简述**：单年/多年双入口不直观；需统一年份输入、勾选导入；导入页可新建关联企业并自动填代码/行业。

**模式**：Vibe

**关键决策**：
- 年份输入合一：`2024` / `2022-2024` / `2022,2023`；`POST /cninfo/search-years` 多年检索。
- 候选表 checkbox +「导入勾选」：按勾选 PDF **逐份**下载建 job（尊重勾选，非仅按年首选）。
- 新建企业对话框：预填巨潮简称/代码；行业来自东财 `f127`（`fetching/eastmoney.py`，失败可空）。
- 选中证券时按 code/name 自动匹配本地企业；不再默认强绑列表第一家。

**变更文件**：
- 后端：`services/fetching/{service,eastmoney}.py`、`schemas/fetch.py`、`api/fetch.py`、`tests/test_fetch_api.py`
- 前端：`api/fetchFiling.ts`、`views/ImportView.vue`
- 文档：`docs/api.md`、`docs/dev-log.md`

**验证**：✅ `pytest` **58 passed**；`bun run type-check` 通过。

**下一步**：导入核对/unmapped 体验；或港股 GAAP。

---


## [2026-07-16] Spec 010 —— 巨潮批量多年拉取

**需求简述**：同一 A 股证券连续多年年报一次提交：检索 → 下载 → 建 import job；单年失败不中断；不自动入库。

**模式**：Spec（变更包 010）

**关键决策**：
- `POST /api/imports/fetch/cninfo/batch`：`q`/`code` + `years`（1–12，去重升序）+ 可选 `company_id`。
- 服务层 `batch_cninfo_download`：解析证券一次；按年 `search_annual_reports` → 首选候选 → `create_job_from_cninfo_candidate`；`ok|empty|error` 汇总。
- 同步串行 + 009 限速；不引入 batch 任务表 / 异步队列。
- 前端：年份起止 +「批量下载解析」+ 结果表（打开核对 → `GET /imports/filings/{id}`）。

**变更文件**：
- Spec：`openspec/changes/010-batch-filing-fetch/*`
- 后端：`services/fetching/service.py`、`schemas/fetch.py`、`api/fetch.py`、`tests/test_fetch_api.py`
- 前端：`api/fetchFiling.ts`、`views/ImportView.vue`
- 文档：`docs/{api,architecture,dev-log}.md`、`AGENTS.md`、`openspec/project.md`

**验证**：✅ `pytest` **56 passed**（fetch 11，含 batch 4）；`bun run type-check` 通过。

**下一步**：导入/分析体验修补；或港股 GAAP / EDGAR。

---


## [2026-07-16] Docs —— v1.0 对齐 + post-1.0 backlog

**需求简述**：v1.0.0 已发布后统一文档状态，标清已交付范围与下一步 backlog，再开 post-1.0 功能。

**模式**：Vibe（仅文档）

**关键决策**：
- `openspec/project.md`：业务范围改为 v1.0 已覆盖；Excel/导入/巨潮写入已交付；新增 Post-1.0 backlog 表（批量拉取 → 体验修补 → 港股 → EDGAR）。
- `docs/architecture.md`：补能力切片、api/services 对照、L0/L1、变更包 001–009 索引与 post-1.0 边界。
- `AGENTS.md`：当前状态标 v1.0.0；补 Import/fetch/excel 范式与 backlog。
- `openspec/changes/001-init-project/tasks.md`：Phase 1–5 勾选与独立包对齐；港股/批量仍 open。
- `docs/api.md` 页脚指向 project backlog。

**变更文件**：`openspec/project.md`、`docs/architecture.md`、`AGENTS.md`、`openspec/changes/001-init-project/tasks.md`、`docs/api.md`、`docs/dev-log.md`

**验证**：文档交叉引用一致；无代码改动。

**下一步**：按 backlog 默认序做 **批量多年拉取**（Spec 010 候选），或用户指定体验修补 / 港股 / EDGAR。

---


## [2026-07-15] Vibe —— 比率分析页对齐多期对比体验

**需求简述**：按多期对比方式优化比率分析：趋势图可调 Y 轴、布局更紧凑。

**模式**：Vibe

**关键决策**：
- 趋势分析：原始值/走势指数；Y 轴含0/自适应/对数/自定义 min-max；右侧 dataZoom + Shift+滚轮缩放 Y；底栏缩放时间。
- 布局：KPI/摘要 padding 收紧；趋势图固定 360px 宿主避免塌陷。
- 修复编辑过程中 AnalysisView 结构损坏并恢复。

**验证**：`bun run type-check` 通过。

---

## [2026-07-15] Vibe —— 多期对比单位/Y轴/留白

**需求简述**：顶部卡片大金额用万/亿；趋势图加强 Y 轴调节；压缩模块留白。

**模式**：Vibe

**关键决策**：
- KPI：`formatMoneySmart` 自动 元/万元/亿元，环比差额同步缩写。
- 趋势图：Y 轴 dataZoom 滑条 + Shift+滚轮缩放；X 轴底栏缩放保留。
- 布局：缩小 card/padding/gap，KPI 更紧凑。

**验证**：`type-check` 通过。

---

## [2026-07-15] Vibe —— 多期对比看板增强 + 趋势坐标可调

**需求简述**：多期对比信息量不足；科目趋势图需可调坐标轴，便于看小数指标。

**模式**：Vibe（前端）

**关键决策**：
- 看板：重点科目 KPI 卡（最新值+环比）+ 最近一期增长/下降 Top 条形榜 + 对照表默认「金额+环比」。
- 趋势图：数值模式（原始/走势指数首期=100）；坐标模式（自动含0 / 自适应缩放 / 对数 / 自定义 min-max）；双 Y 轴按量级几何中位拆分；dataZoom 缩放时间轴；「按所选填范围」一键写入自定义刻度。
- 表格：科目筛选、隐藏全空行；点击行切换趋势曲线。

**变更文件**：`frontend/src/views/CompareView.vue`、`docs/dev-log.md`

**验证**：`bun run type-check` 通过。

---

## [2026-07-15] Fix —— 较上期对比应对齐当前选中报告期

**需求简述**：比率分析「较上一期变动」总是拿最新两年比（如永远对 2024），应拿**当前年报的前一年**。

**模式**：Vibe

**根因**：`computeYoY` 取 history 有值序列的 `[1]`（全局次新），与当前 `snapshot.period` 无关。

**修复**：
- 传入当前报告期；在 history 中找 `periodRank < 当前` 的最近一期作为上期（年报即前一年；缺数年则再往前）。
- `buildPeriodCompareRows` / KPI / 健康摘要统一用该逻辑；标签显示如「2023 年报 → 2024 年报」。

**验证**：2024→上期 2023；2025→上期 2024。`type-check` 通过。

---

## [2026-07-15] Fix —— 比率分析切换报告期数据不更新

**需求简述**：切换年报年份后界面仍显示最新一期（如 2026/2025）比率。

**模式**：Vibe

**根因**：`periodKey` 绑定了下拉框，但没有 `watch(periodKey)` 去重新 `fetchRatios`；仅 `watch(companyId)` 会加载。

**修复**：
- 增加 `watch(periodKey)` → `loadSnapshotAndHistory`
- `loadPeriods` 不再每次强制重置为最新期（当前 key 仍有效则保留）
- 请求序号防竞态；工具条显示「数据期 YYYY 年报」便于核对

**验证**：科沃斯切换 2025→2024→2023，请求 `year=` 与标签同步正确。

---

## [2026-07-15] Vibe —— 巨潮支持公司名称检索

**需求简述**：在线拉取除证券代码外，支持用公司名称检索年报。

**模式**：Vibe

**关键决策**：
- `search_securities`：名称变体（去「股份有限公司」等后缀 + 逐步缩短）应对巨潮 topSearch 对全称/中间名无结果。
- 新接口 `GET /api/imports/fetch/cninfo/securities?q=`；年报检索参数改为 `q`（兼容 `code`）。
- 前端：输入「代码或名称」→ 证券列表（多命中手选）→ 年报列表。

**验证**：✅ 全称「科沃斯机器人股份有限公司」「贵州茅台酒股份有限公司」可解析；fetch 测试 7 passed；type-check 通过。

---

## [2026-07-15] 009 —— 年报 PDF 在线拉取（URL + 巨潮）

**需求简述**：按公司/年份自动检索下载 A 股年报 PDF，或 PDF 直链下载，接入现有导入人审流水线（A+B）。

**模式**：Spec（变更包 009）

**关键决策**：
- A：`POST /api/imports/fetch/from-url` 下载 PDF → `create_job_from_upload(source_type=pdf_url)`
- B：巨潮 `topSearch` + `hisAnnouncement/query`（category 年报）；标题过滤排除摘要/英文；`static.cninfo.com.cn` 下 PDF
- 礼貌限速 0.4s；校验 `%PDF` 魔数与 40MB 上限
- 不自动 commit；前端「在线拉取」Tab → 下载后跳转 PDF 核对
- 测试 mock httpx；外网 smoke：603486/2024 命中「2024年年度报告」

**变更文件**：
- Spec：`openspec/changes/009-filing-fetch/*`
- 后端：`services/fetching/*`、`api/fetch.py`、`schemas/fetch.py`、`import_service.create_job_from_upload` 扩展、`tests/test_fetch_api.py`
- 前端：`api/fetchFiling.ts`、`views/ImportView.vue`
- 文档：`docs/api.md`、`AGENTS.md`、`docs/dev-log.md`

**验证结果**：✅ `pytest` **50 passed**；`type-check` 通过；巨潮检索 live 200

**下一步**：可选批量多年任务；或港股/EDGAR（解析器需另做）。

---

## [2026-07-15] Phase 5 导入 —— Excel 模板三表入库

**需求简述**：实现 Excel 模板导入，与导出对称；比率不导入。

**模式**：Spec（变更包 008）

**关键决策**：
- 模板：`GET /api/excel/template.xlsx`（说明+三表+比率占位说明）
- 预览/入库：`POST .../excel/preview|import`；忽略「财务比率」与未知 sheet
- 期间列：`YYYY 年报` / `YYYY Qn`；同工作簿不混 period_type
- 覆盖：overwrite 更新科目字段，不改 year/period_type；空期间跳过
- 导出文件可 round-trip 再导入
- 前端「年报导入」页默认 Tab：Excel 模板导入

**变更文件**：
- Spec：`openspec/changes/008-excel-import/*`
- 后端：`services/excel_import_service.py`、`schemas/excel_import.py`、`api/excel_io.py`、`tests/test_excel_import_api.py`
- 前端：`api/excel.ts`、`views/ImportView.vue`
- 文档：`docs/api.md`、`AGENTS.md`、`docs/dev-log.md`

**验证结果**：✅ `pytest` **45 passed**（excel import 6）；`bun run type-check` 通过

**下一步**：PDF 导入边角修补，或对比页同比增强。

---

## [2026-07-15] Phase 5 导出 —— Excel 三表 + 财务比率

**需求简述**：导出 Excel 时必须包含相关财务比率（用户明确要求）。

**模式**：Spec（变更包 007，先做导出切片；导入另开）

**关键决策**：
- `GET /api/companies/{id}/export.xlsx`：openpyxl 生成 5 sheet（说明 / BS / IS / CF / 财务比率）。
- 比率按期调用 `compute_period_ratios`；percent 导出为 ×100 百分数，ratio 为倍数；表头单位列标明。
- 期间轴 = 三表并集，可选 `years`；前端对比页按所选年份、比率页按当前 period_type 全部年份。
- 入口：`CompareView` / `AnalysisView`「导出 Excel」。

**变更文件**：
- Spec：`openspec/changes/007-excel-export/*`
- 后端：`services/export_service.py`、`api/export.py`、`api/__init__.py`、`tests/test_export_api.py`
- 前端：`api/export.ts`、`views/{CompareView,AnalysisView}.vue`
- 文档：`docs/api.md`、`AGENTS.md`、`docs/dev-log.md`

**验证结果**：✅
- `pytest`：**39 passed**（export 4）
- 科沃斯 2024–2025 导出含「财务比率」：流动比率 1.71/1.81、资产负债率 52.1%/48.1%
- `bun run type-check` 通过

**下一步**：Excel 模板导入；或 PDF 导入体验修补。

---

## [2026-07-15] Fix —— 多期对比空白

**需求简述**：科目趋势与科目对照表不显示。

**模式**：Vibe

**根因**：
1. `frontend/src/api/compare.ts` 请求路径写成 `/companies/...`，漏了项目约定的 `/api` 前缀（其它客户端均为 `/api/companies/...`），开发代理未命中 → 404。
2. 运行中的 uvicorn 未加载 006 路由（openapi 无 compare），需重启后端。

**修复**：
- 路径改为 `/api/companies/{id}/compare-periods` 与 `/compare`
- 注册 ECharts `TitleComponent`（空态标题）
- 重启后端

**验证结果**：✅ 科沃斯 4 期 BS 趋势图 canvas 1098×320；对照表 2022–2025 金额可见；代理 `/api/.../compare` 200。

---

## [2026-07-15] Phase 4 —— 科目级多期对比

**需求简述**：三大报表科目金额的多期对照、环比与结构占比，补齐比率页之外的科目级分析。

**模式**：Spec（变更包 006）

**关键决策**：
- API：`GET .../compare-periods`、`GET .../compare`；期间列表复用 `ratio_service.list_ratio_periods`。
- 矩阵：科目 × 期间（时间升序）；`deltas`/`delta_pcts` 为序列相邻期环比；结构 balance÷资产总计、income÷营业收入、cashflow 无结构。
- 同 `period_type` 内对比，不混比年报/季报；结果不落库。
- 前端 `CompareView`：企业/报表/期间多选（默认最近 5 期）、金额|结构%|环比% 切换、科目趋势折线。

**变更文件**：
- Spec：`openspec/changes/006-multi-period-compare/{proposal,spec,design,tasks}.md`
- 后端：`schemas/compare.py`、`services/compare_service.py`、`api/compare.py`、`api/__init__.py`、`tests/test_compare_api.py`
- 前端：`api/compare.ts`、`views/CompareView.vue`、`router/index.ts`、`layouts/DefaultLayout.vue`
- 文档：`docs/{api,architecture,dev-log}.md`、`AGENTS.md`

**验证结果**：✅
- `pytest`：**35 passed**（含 compare 6）
- 前端：`bun run type-check` 通过
- 本地 venv 升级为 Python 3.12（`Mapped[int | None]` 需 3.10+）

**下一步**：Phase 5 Excel 模板导入导出；或导入体验修补。

---

## [2026-07-15] Vibe —— 对比图表空白 + 结构悬停明细

**需求简述**：变动幅度 / 上期对照不显示；结构图偏小；悬停需看到需关注具体项目。

**模式**：Vibe

**关键决策**：
- 根因：`.chart-module { overflow:hidden }` 导致 echarts canvas clientHeight=0。
- 用 `.chart-host` 固定高度容器 + `v-chart` 100% 填满；`key` 随 period/role 强制重绘。
- 结构环图高度 200→280，半径加大；tooltip 列出该扇区全部指标名/变动/水平。

**变更文件**：`frontend/src/views/AnalysisView.vue`、`docs/dev-log.md`

**验证结果**：✅ 科沃斯多期页 canvas 高度正常（结构 280 / 双向条 288 / 对照 320）；悬停「需关注」显示「总资产周转率」。type-check 通过。

---

## [2026-07-15] Vibe —— 对比模块布局：重叠与留白

**需求简述**：变动幅度模块与上方重叠；变动结构/重点变动区域空白过大。

**模式**：Vibe

**关键决策**：
- 顶部改为 `compare-top-grid`（CSS grid），去掉 `el-row` + `min-height:100%` 拉伸溢出。
- 结构区 `structure-body` 纵向 flex，芯片贴底，减少环图下方空洞。
- 重点区两列均分、卡片收紧；空态用虚线框占位。
- 下方 chart-module `clear/overflow` + 双向条高度上限 420，grid `containLabel` 防标签撑破。

**变更文件**：`frontend/src/views/AnalysisView.vue`、`docs/dev-log.md`

**验证结果**：✅ `bun run type-check` 通过。

---

## [2026-07-15] Vibe —— 较上期变动：图表模块化

**需求简述**：对比区不要以纯文字为主，改为图表/模块直观展示。

**模式**：Vibe

**关键决策**：
- **变动结构**：ECharts 环形图 + 改善/需关注/持平计数芯片。
- **重点变动**：哑铃图卡片（上期点→本期点）+ 幅度条，替代文字列表。
- **语义双向条**：改善向右、需关注向左（业务语义轴，非涨跌）。
- **上期 vs 本期**：分组柱对照；悬停看 transition。
- 数值明细表保留但默认折叠；点击图表/卡可高亮 KPI。
- 辅助：`toDisplayValue` / `semanticChangeValue`；注册 `PieChart` + `GraphicComponent`。

**变更文件**：`frontend/src/utils/ratioInsights.ts`、`frontend/src/views/AnalysisView.vue`、`docs/dev-log.md`

**验证结果**：✅ `bun run type-check` 通过。

**下一步**：Phase 4 多期对比，或继续打磨 KPI 迷你 sparkline。

---

## [2026-07-15] Vibe —— 本期 vs 上期对比体验（方案 B）

**需求简述**：比率页「本期 vs 上期」不直观，表格台账感强、与 KPI 重复；按方案 B 做三层叙事。

**模式**：Vibe

**关键决策**：
- 信息架构：健康摘要 → **核心 KPI（含上期→本期）** → **较上期变动** → 雷达/杜邦 → 趋势 → 全表。
- 数据层：`computeYoY` 文案改为 `+2.8pp` / `+0.15×`；补 `meaning`（改善/需关注/持平）、相对变动、`formatTransition`。
- `buildPeriodCompareRows` 产出 counts、`rowsByMagnitude`、`barPct`；`buildCompareNarrative` 生成结论条。
- UI：结论条 + 改善/需关注焦点卡（条形幅度）+ 折叠对照表（上期→本期列序，业务含义与水平分列）。
- 水平状态与变动语义分色；点击焦点卡/行高亮对应 KPI；专业角色默认展开对照表。

**变更文件**：`frontend/src/utils/ratioInsights.ts`、`frontend/src/views/AnalysisView.vue`、`docs/dev-log.md`

**验证结果**：✅ `bun run type-check` 通过；展示文案 smoke：`12%→15% +3.0pp 改善`、`55%→62% +7.0pp 需关注`。

**下一步**：Phase 4 多期对比（科目级），或导入体验修补。

---

## [2026-07-13] Vibe —— 趋势图：双轴 + 可选对比（去指数）

**需求简述**：不要指数模式；采用方案 2 双 Y 轴 + 用户自选对比指标，且不限制勾选数量上限。

**模式**：Vibe

**关键决策**：
- 删除走势指数/原始数值切换。
- Tab 内多选对比指标（checkbox，无上限）；切换 Tab/角色时重置为默认 1～2 项。
- 勾选序列同时含 % 与倍数 → 左 % / 右倍数；否则单轴。
- Tooltip 仅真实单位值。

**变更文件**：`frontend/src/utils/ratioInsights.ts`、`frontend/src/views/AnalysisView.vue`

**验证结果**：✅ `bun run type-check` 通过。

---


## [2026-07-13] Vibe —— 趋势图量纲修复（指数/双轴）

**需求简述**：趋势分析多指标共轴时大数压扁小数，走势不可读。

**模式**：Vibe

**关键决策**：
- 默认 **走势指数**（首个有效值=100），只比相对涨跌。
- **原始数值**模式：% 与倍数混排时左右双 Y 轴；同单位仍单轴。
- Tooltip 在指数模式下同时显示原始值。

**变更文件**：`frontend/src/views/AnalysisView.vue`、`docs/dev-log.md`

**验证结果**：✅ `bun run type-check` 通过。

---


## [2026-07-13] Vibe —— 比率分析补齐 P1：本期 vs 上期

**需求简述**：P1 中「两期对比条 / 变动榜」此前未单独落地（摘要与全表折叠已在 P0）。

**模式**：Vibe

**关键决策**：
- `buildPeriodCompareRows` + `rankMovers`：基于 history 做本期/上期与改善·恶化 Top3。
- 摘要卡下方增加对比卡：空态提示需 ≥2 期；有数据时展示 Top 变动 + 表格（本期/上期/变动/状态）。
- 指标集跟随当前角色 KPI keys。

**变更文件**：`frontend/src/utils/ratioInsights.ts`、`frontend/src/views/AnalysisView.vue`

**验证结果**：✅ `bun run type-check` 通过。

---


## [2026-07-13] Vibe —— 比率分析 P3：角色视图 + 导出

**需求简述**：管理层/投资人/专业全量三视图切换；导出 HTML 快照与打印/PDF。

**模式**：Vibe

**关键决策**：
- `ROLE_PROFILES`：不同 KPI 集、默认趋势 Tab、是否展开全表、是否显示雷达/杜邦。
- 管理层默认偏偿债与现金流、隐藏杜邦；投资人偏 ROE/利润率并显示杜邦；专业默认展开全表。
- 导出独立 HTML（摘要+核心 KPI+全表）；打印用 `@media print` 隐藏工具按钮。

**变更文件**：`frontend/src/utils/ratioInsights.ts`、`frontend/src/views/AnalysisView.vue`

**验证结果**：✅ `bun run type-check` 通过。

**下一步**：Phase 4 多期对比，或导入体验修补。

---


## [2026-07-13] Vibe —— 比率分析 P2：雷达 + 杜邦

**需求简述**：在 P0 快览基础上增加能力雷达与杜邦三因子拆解，便于讲清「哪里强/弱、ROE 从哪来」。

**模式**：Vibe（前端可视化）

**关键决策**：
- `scoreRatio` 将指标映射 0–100 沟通分；四维：偿债/盈利/营运/现金流。
- 杜邦：ROE ≈ 净利率 × 总资产周转率 × 权益乘数（1/权益比率）；展示乘积与偏差提示。
- 布局：核心 KPI 下方左右分栏（雷达 | 杜邦条形）。

**变更文件**：`frontend/src/utils/ratioInsights.ts`、`frontend/src/views/AnalysisView.vue`

**验证结果**：✅ `bun run type-check` 通过。

**下一步**：Phase 4 多期对比；或导出一页财务快照。

---


## [2026-07-13] Vibe —— 比率分析页体验增强（P0）

**需求简述**：比率页偏简陋，按「摘要 + 核心 KPI 红绿灯/同比 + 分主题趋势 + 可展开明细」增强，便于管理者与投资人快读。

**模式**：Vibe（前端体验，不改计算公式）

**关键决策**：
- 新增 `utils/ratioInsights.ts`：阈值信号、YoY、规则化健康摘要。
- 主 KPI 六项：ROE / 净利率 / 毛利率 / 资产负债率 / 流动比率 / 经营现金流÷营收。
- 趋势按盈利 / 偿债 / 营运与现金流分 Tab；时间轴旧→新。
- 全部 13 项收入可折叠表格（状态色 + 公式说明）。
- 阈值仅为沟通用默认，页头声明非投资建议。

**变更文件**：`frontend/src/utils/ratioInsights.ts`、`frontend/src/views/AnalysisView.vue`、`docs/dev-log.md`

**验证结果**：✅ `bun run type-check` 通过。

**下一步**：可选雷达/杜邦（P2）；或 Phase 4 多期对比 API。

---


## [2026-07-13] Phase 3 —— 财务比率分析与可视化

**需求简述**：按企业/报告期动态计算常用财务比率，前端卡片 + 多期趋势图。

**模式**：Spec 实施（变更包 005）

**关键决策**：
- 比率不落库；公式元数据在 `RATIO_DEFINITIONS`，计算在 `ratio_service`。
- 一期 13 项：偿债 6 + 盈利 5 + 营运 1 + 现金流 1。
- ROE 优先 `net_profit_parent / total_equity_parent`，否则回退合并口径。
- 缺字段 / 分母 0 → `value=null` + reason，不编造。
- API：`ratio-periods` / `ratios` / `ratios/history`。

**变更文件**：
- Spec：`openspec/changes/005-ratio-analysis/*`
- 后端：`core/constants.py`、`services/ratio_service.py`、`schemas/ratio.py`、`api/ratios.py`、`tests/test_ratios_api.py`
- 前端：`api/ratio.ts`、`views/AnalysisView.vue`（ECharts）
- 文档：api.md、AGENTS、dev-log

**验证结果**：✅ pytest 全绿（含 4 个比率用例）；`vue-tsc --noEmit` 通过。

**下一步**：Phase 4 多期对比；或导入 unmapped 体验修补。

---


## [2026-07-13] 实施 —— 004 CAS-simplified-v2 + L0 披露层

**需求简述**：按确认的合成版冻结清单实现 v2 标准科目扩列、别名热修、显式 rollup、L0 披露明细双写、locate 续页修复。

**模式**：Spec 实施（变更包 004）

**关键决策**：
- `COA_VERSION=cas-simplified-v2`；L1 三表扩约 21 列（少数股东/使用权资产/归母净利/经营现金流其他收付等）。
- 权益四字段仅补 `subject_aliases`（非加列）。
- `rollup_rules` 精确匹配；mapper 产出 `disclosure_lines`。
- commit 同事务写 L1 + `statement_disclosure_lines`。
- locate：续页不重置 start；合并段忽略后续母公司/未知「资产负债表」截断。

**变更文件（主要）**：
- Spec：`openspec/changes/004-coa-v2-disclosure-layers/*`
- 后端：`core/{constants,subject_aliases,rollup_rules}`、三表 ORM/schemas、`models/disclosure_line`、`services/{disclosure_service,import_service,importing/*}`
- 前端：`constants/statementFields.ts`
- 测试路径对齐 `年报参考/ashare-cas/`

**验证结果**：✅
- pytest **25 passed**
- 科沃斯：权益/库存股/使用权资产/归母净利/经营其他收付等映射成功；disclosure≈193 行
- 迈瑞：locate 自 p208 表头起，`AUTO_COMMIT_CANDIDATE`，BS 46 字段
- 前端 `vue-tsc --noEmit` 通过

**下一步**：Phase 3 比率分析（只读 L1）；可选 ImportView 展示 L0 映射表。

---


## [2026-07-13] 分析 —— ashare-cas 频次与 v2 草案

**需求简述**：对 10 家 A 股 CAS 主集跑导入管道，统计 unmapped，冻结 v2 字段与 L0/L1 结构草案。

**模式**：Plan / 数据驱动设计

**关键发现**：
- 9/10 `AUTO_COMMIT_CANDIDATE`；迈瑞因 locate 落在「（续）」页导致 BS/IS 映射失败（样本仍保留）。
- 权益四科目已在 v1 ORM，但 **aliases 缺失** → 100% 假 unmapped，应先热修别名。
- 高频真缺失：少数股东权益、库存股、BS-OCI、其他流动负债、使用权资产、归母净利/少数股东损益、综合收益、公允价值变动、经营现金流「其他收/付」等。
- 产出：`年报参考/_analysis/`（summary、frequency、classified、**CAS-simplified-v2-proposal.md**）。

**建议 v2**：约 21 个 L1 新列 + L0 `statement_disclosure_lines`；rollup 表承接长尾。

**下一步**：用户确认清单 → openspec 变更包 → 别名热修 + 扩列 + L0。

---


## [2026-07-13] 样本集验收 —— ashare-cas 主集 10/10

**需求简述**：补齐格力、永辉后再次验收。

**模式**：Vibe / 数据验收

**关键结果**：
- `格力电器2025年报`、`永辉超市2025年报` 归位为 `000651_*` / `601933_*`。
- 抽检：简体「合并资产负债表/利润表/现金流量表」+「企业会计准则」，无 IFRS 港式标记，CID=0。
- **主集 10/10 齐套**，可进入 unmapped 频次统计。

**变更文件**：`年报参考/ashare-cas/`、`samples.csv`、`README.md`

**下一步**：管道批量统计 → 冻结 v2 字段清单与表结构。

---


## [2026-07-13] 样本集验收 —— 主集 8/10，2 份 IFRS 误收

**需求简述**：用户集齐年报后验收是否可作为 CAS v2 统计输入。

**模式**：Vibe / 数据验收

**关键发现**：
- 新 PDF 原在 `年报参考/` 根目录且未规范命名 → 已归入 `ashare-cas/` 并重命名。
- **美的、顺丰** 实为 **港式 IFRS 年报**（合併財務狀況表 / 国际财务报告准则），非巨潮 A 股 CAS 合并资产负债表 → 移入 `cross-gaap/`，不参与 v2 加列统计。
- 顺丰部分页 CID；其余 8 家 CAS 均可定位合并三表标题。
- 主集替换：G1 家电改 **格力 000651**，G6 改 **永辉 601933**（待下载）。

**变更文件**：`年报参考/{README,samples.csv}`；PDF 归位/挪目录。

**验证结果**：✅ 抽检 extract_text；主集可用 8/10。

**下一步**：补格力、永辉 CAS 全文后跑 unmapped 频次。

---


## [2026-07-13] 设计 —— CAS v2 样本集分层抽样

**需求简述**：为合成版（标准科目 L1 + 披露明细 L0）冻结 v2 字段，先建多行业年报参考集。

**模式**：Plan / 设计前置（未改业务代码）

**关键决策**：
- 定 v2 **只认** 非金融 A 股 CAS 主集 10 家；港股 GAAP / 难例 / 金融仅对照。
- 升格门槛：出现率 ≥40% 独立列；15%～40% 显式 rollup；&lt;15% 仅 L0。
- 不做巨潮批量爬取；精选手工下载全文 PDF。
- 目录：`ashare-cas/` / `cross-gaap/` / `hard-cases/` / `optional-financial/`。

**变更文件**：
- `年报参考/README.md`、`samples.csv`
- 既有 PDF 归入子目录并规范命名（科沃斯/影石/B站/小米）

**主集名单（10）**：603486 科沃斯、688775 影石、000333 美的、600519 茅台、300760 迈瑞、688111 金山办公、002555 三七互娱、600048 保利发展、002352 顺丰、600309 万华化学。

**验证结果**：✅ 目录与清单落盘；主集 2/10 已到位。

**下一步**：补齐剩余 8 家巨潮年报全文 → 管道跑 unmapped 频次 → 冻结 v2 字段与 L0/L1 表结构。

---


## [2026-07-12] Phase 2 —— 公开年报导入（CAS 主路径落地）

**需求简述**：上传上市公司年报 PDF，自动识别三大报表并映射入库；先做人审确认。

**模式**：Spec 实施（变更包 003）

**关键决策**：
- 七段管道落地：`profile → locate → extract → map → validate → commit`。
- CAS 数字 PDF 用 pdfplumber 表格；附注列过滤；表头年份优先于审计落款。
- 别名词典 + 字段级消歧（营收/净利/权益合计）；资产负债勾稽 gap=0 于科沃斯/影石样本。
- 入库复用 `statement_service`；前端向导 `/import`。

**变更文件（主要）**：
- 后端：`services/importing/*`、`import_service.py`、`api/imports.py`、`models/import_job.py`、`core/subject_aliases.py`、`tests/test_import_pipeline.py`
- 前端：`views/ImportView.vue`、`api/importFiling.ts`、路由/侧栏
- 文档：api.md、AGENTS/CLAUDE、003 tasks

**验证结果**：✅
- pytest **24 passed**
- 科沃斯 PDF smoke：upload → review → commit 三表入库
- 影石/科沃斯管道：`AUTO_COMMIT_CANDIDATE`，核心字段与 BS 勾稽通过
- 前端 `bun run type-check` + build 通过

**下一步**：补强港股/B站别名；比率分析 Phase 3。

---

## [2026-07-12] Spec —— 财报识别与自动填入算法

**需求简述**：设计适用于大部分公开财报的识别与自动填入算法（非实现）。

**模式**：Spec

**关键决策**：
- 七段管道：DocumentProfile → StatementLocate → TableExtract → RowNormalize → SubjectMap → Validate → AutoFill。
- 表格优先、行文本兜底；标题状态机区分合并/母公司；多级别名+区块上下文映射。
- 置信度分层：高置信可预填/候选自动提交，中置信人审，低置信拒绝（CID/扫描）。
- 核心 12 项作为质量闸门；单位统一到元。

**变更文件**：
- `openspec/changes/003-public-filing-import/algorithm.md`
- `design.md` / `tasks.md` 交叉引用
- `docs/dev-log.md`

**验证结果**：✅ 对照科沃斯/影石/B站/小米抽样特征写清规则与验收用例。

---

## [2026-07-12] Spec —— 公开年报导入通用方案（变更包 003）

**需求简述**：基于 `年报参考/` 四份年报，设计自动识别并导入上市公司财报的通用方案，拟纳入下一阶段。

**模式**：Spec（仅设计，未实施）

**样本结论**：
- 科沃斯 / 影石：A 股 CAS 数字 PDF，pdfplumber 表格可用，合并+母公司双表，单位元。
- 哔哩哔哩：US GAAP 繁体，千元+多列年份，表格线弱，需行文本解析。
- 小米：CID 字体乱码，一期应降级而非硬解析。

**关键决策**：管道架构（接入→抽取适配器→映射词典→草稿人审→复用 CRUD 落库）；不做静默全自动入库；导入建议作为 Phase 2，比率顺延。

**变更文件**：
- `openspec/changes/003-public-filing-import/{proposal,spec,design,tasks}.md`
- `docs/dev-log.md`

**验证结果**：✅ 对四份 PDF 做了页定位与表格抽样；方案文档已落盘。

**下一步**：用户确认阶段排序后开工实施。

---

## [2026-07-12] Vibe —— 报表录入界面改为会计表格式

**需求简述**：录入界面不符合会计习惯，参照 `财务报表图片参考/` 调整布局。

**模式**：Vibe（UI 交互）

**关键决策**：
- 资产负债表：左右对照（资产 | 负债及权益），「项目 + 期末数」。
- 利润表 / 现金流量表：竖式「项目 | 金额」，标题/公司/期间/单位元表头。
- 分组标题行、合计行加粗底色；科目缩进；弹窗内滚动纸面样式。
- 字段集合不变（仍对接现有 API），仅改前端元数据角色与渲染。

**变更文件**：
- `frontend/src/constants/statementFields.ts`
- `frontend/src/views/StatementsView.vue`
- `docs/dev-log.md`

**验证结果**：✅ `bun run type-check` + `bun run build` 通过；浏览器截图确认资产负债表左右栏、利润表竖式布局。

---

## [2026-07-12] Phase 1 —— 三大报表录入与存储

**需求简述**：完整 CAS 简化版科目 + 年报/季报 + 三表 CRUD + StatementsView 录入界面。

**模式**：Spec（变更包 002）

**关键决策**：
- 科目口径：完整 CAS 简化版（资产负债 32 / 利润 18 / 现金流 15），用户确认。
- 报告期：`annual` 强制 `quarter=null`；`quarterly` 强制 `1..4`；service 层显式防重（兼容 SQLite UNIQUE+NULL）。
- 三表 CRUD 同构，嵌套路径 `/api/companies/{id}/{balance-sheets|income-statements|cash-flow-statements}`。
- 开发期 `create_all` + `ensure_sqlite_columns` 增列，避免本地库卡在 stub 字段。
- 合计科目由用户录入，不做自动勾稽。
- 前后端各维护一份科目分组常量（`core/constants.py` / `constants/statementFields.ts`）。

**变更文件**：
- Spec：`openspec/changes/002-statements-crud/{proposal,spec,design,tasks}.md`
- 后端：`models/{balance_sheet,income_statement,cash_flow}.py`、`schemas/statement.py`、`services/statement_service.py`、`api/statements.py`、`core/constants.py`、`database.py`、`main.py`、`tests/test_statements_api.py`
- 前端：`api/statement.ts`、`stores/statement.ts`、`constants/statementFields.ts`、`views/StatementsView.vue`
- 文档：`docs/{api,architecture,dev-log}.md`、`AGENTS.md`、`CLAUDE.md`

**验证结果**：✅ 通过
- `pytest`：**20 passed**（企业 9 + 报表 11）
- smoke：创建企业 → 三表录入 → 列表
- 前端：`bun run build`（vue-tsc + vite）通过

**下一步**：Phase 2 —— 财务比率分析与可视化（变更包 003）。

---

## [2026-06-27] Vibe —— 增加一键关闭项

**需求简述**：提供一个可双击的关闭入口，用于停止本地后端与前端开发服务。

**模式**：Vibe（小型开发体验改进）

**关键决策**：
- 新增 `scripts/stop-dev.sh` 作为通用停止脚本，优先使用 `.runtime/*.pid`，再回退检查 `9000/5173` 端口。
- 新增根目录 `关闭财务分析系统.command`，macOS 下可直接双击关闭服务。
- 停止脚本会匹配命令行特征，仅关闭看起来属于本项目的 FastAPI/Vite 进程。

**变更文件**：
- `scripts/stop-dev.sh`
- `关闭财务分析系统.command`
- `README.md`
- `docs/dev-log.md`

**验证结果**：✅ 通过
- `bash -n scripts/stop-dev.sh`
- `bash -n 关闭财务分析系统.command`
- `./scripts/stop-dev.sh --dry-run` 可识别当前项目后端与前端进程，并跳过其他目录下的 Vite 进程。

---

## [2026-06-27] Vibe —— 增加一键启动项

**需求简述**：提供一个可双击的一键启动入口，自动启动本地后端与前端开发服务。

**模式**：Vibe（小型开发体验改进）

**关键决策**：
- 新增 `scripts/start-dev.sh` 作为通用启动脚本，负责检查 Python/Node、补齐依赖、启动 FastAPI 与 Vite。
- 新增根目录 `启动财务分析系统.command`，macOS 下可直接双击启动并打开前端页面。
- 运行时日志与 PID 落到 `.runtime/`，并加入 `.gitignore`。

**变更文件**：
- `scripts/start-dev.sh`
- `启动财务分析系统.command`
- `.gitignore`
- `README.md`
- `docs/dev-log.md`

**验证结果**：✅ 通过
- `bash -n scripts/start-dev.sh`
- `bash -n 启动财务分析系统.command`
- `SKIP_OPEN=1 ./scripts/start-dev.sh` 可识别当前后端 `9000` 与前端 `5173` 已运行，并输出访问地址。

**下一步**：如需要，可再补一个停止脚本。

---

## [2026-06-17] Phase 0 —— 建立项目框架

**需求简述**：从零搭建轻量级企业财务报表分析系统的项目骨架（后端可起服务、前端可渲染、含示例切片与全套文档）。

**模式**：Spec（"从零开始一个项目"）

**关键决策**：
- 技术栈：FastAPI + Vue3 + Element Plus + ECharts + SQLite + pandas，单机本地无认证。
- 后端分层：`api → services → models`，由 Company CRUD 切片确立范式。
- 比率不落库，按公式动态计算；报告期用 `(year, period_type, quarter)` 三元组。
- 前端 `/api` 代理打通开发态。

**变更文件**：
- 新增 Spec 文档：`openspec/project.md`、`openspec/AGENTS.md`、`openspec/changes/001-init-project/{proposal,spec,design,tasks}.md`
- 新增导航文档：`CLAUDE.md`、`README.md`、`.gitignore`、`docs/{architecture,api,dev-log}.md`
- 后端骨架：`backend/requirements.txt`、`backend/app/**`（main/config/database、models、schemas、api、services、core、tests）
- 前端骨架：`frontend/{package.json,vite.config.ts,tsconfig.json,index.html}`、`frontend/src/**`

**验证结果**：✅ 全部通过
- 后端：`pytest` **9 passed**（CRUD + 校验 + 404 + 409 覆盖）。
- 后端：`uvicorn app.main:app` 启动，`GET /api/health` → `{"status":"ok"}`，`/docs` 可达。
- 前端：`npm run build` 通过（vue-tsc 类型检查 + vite 打包，✓ built in 4.19s）。
- 联调：前端 5173 经 Vite `/api` 代理 → 后端 9000；POST 创建 → 201、重复 code → 409、GET 列表正常，端到端打通。

**关键问题与修复（本次验证发现）**：
- **端口冲突**：本机 Windows Hyper-V 保留端口范围 `7985-8084` / `8134-8233` 把常见的 8000/8001/8080 全部排除，uvicorn bind 报 `Errno 13`。
  → **改默认端口为 9000**，同步更新 `backend/app/config.py`(BACKEND_PORT)、`frontend/vite.config.ts`(proxy target)、README/CLAUDE/api.md/architecture.md/design.md，保证全局一致。
- **FastAPI 0.111 对 204 的约束**：`@router.delete(status_code=204)` 触发 `AssertionError: Status code 204 must not have a response body`。
  → delete 端点改用 `response_class=Response` 并显式返回 `Response(status_code=204)`。
- **tsconfig project references**：单一 tsconfig.json 既带 include 又带 references 会报 TS6310。
  → 拆为标准三文件结构：`tsconfig.json`(solution, files:[]) + `tsconfig.app.json`(应用) + `tsconfig.node.json`(构建配置)。

**下一步**：Phase 1 —— 三大报表录入与存储（独立变更包 002），届时决策科目集合口径。
