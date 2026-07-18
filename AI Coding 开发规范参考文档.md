---
title: "AI Coding 开发规范（参考文档）"
type: synthesis
tags: [开发规范, 模板, AI编程, 综合]
created: 2026-06-17
updated: 2026-07-18
sources:
  - ~ai-coding~/wiki/concepts/Vibe Coding.md
  - ~ai-coding~/wiki/concepts/Spec 驱动开发.md
  - ~ai-coding~/wiki/concepts/Vibe Plan Spec 三种模式.md
  - ~ai-coding~/wiki/concepts/Harness Engineering.md
  - ~ai-coding~/wiki/concepts/文档驱动开发 DADD.md
  - ~ai-coding~/wiki/concepts/企业级 AI Coding 风险评估.md
---

# AI Coding 开发规范（参考文档）

> 综合 [[~ai-coding~/wiki/concepts/Vibe Coding.md|Vibe Coding 的灵活性]] 与 [[~ai-coding~/wiki/concepts/Spec 驱动开发.md|Spec 驱动的严谨性]]，结合 [[~ai-coding~/wiki/concepts/Harness Engineering.md|Harness Engineering 工程化实践]]，设计此开发规范参考文档。适用于**个人到小团队**的 AI 辅助编程场景。

---

## 一、核心理念

```
Vibe Coding 的灵魂：轻松对话、快速尝试、享受创造
       +
Spec 驱动的骨架：需求澄清、文档记录、分步执行
       ↓
  「自由的表达，严谨的落地」——Flexible Intent, Rigorous Execution
```

**三条金律**：

| # | 金律 | 来源 |
|---|------|------|
| 1 | **先对齐再动手** —— 让 AI 先用你的话复述一遍它理解的需求，确认后再执行 | Spec 驱动 + Vibe 实战技巧 |
| 2 | **小步快跑，步步验证** —— 分阶段推进，每阶段完成后验证再继续 | Vibe 实战技巧 + Harness 迭代自愈 |
| 3 | **文档即副产品** —— 每次对话结束后，用 3 分钟整理一份开发日志 | Harness + DADD |

---

## 二、场景分级选择

根据任务复杂度选择对应的规范力度：

```
复杂度 →
  Vibe 模式        Plan 模式        Spec 模式
  (轻规范)         (中规范)         (重规范)
  ─────────       ─────────       ─────────
  改个文案         日常功能          新模块
  修个小bug        中等重构          架构变更
  快速原型         交互逻辑          API 设计
  个人工具         多人协作          核心系统
```

### 判断清单

在做任何 AI 编程任务前，先回答三个问题：

1. **这是新功能还是修改？**
   - 新功能 / 架构调整 / 接口变更 → 至少用 Plan 模式
   - 小修小改 / UI 微调 → Vibe 模式即可

2. **这个改动会影响其他模块吗？**
   - 是 → 上 Spec 模式
   - 否 → Plan 或 Vibe 模式

3. **一个月后我自己还能看懂这段代码吗？**
   - 不确定 → 需要文档记录（至少 Plan 级别）

---

## 三、分级规范模板

### 级别 1：Vibe 规范（适用于简单任务）

**适用场景**：bug 修复、文案修改、样式微调、单文件改动

**沟通模板**：
```
"我有一个 [问题/需求]。

当前情况：[简要描述现状]

想要的效果：[预期效果]

如果有不确定的地方可以问我，完成后告诉我改了什么。"
```

**规范要求**：
- [ ] 描述清楚问题和预期
- [ ] 让 AI 完成后**自述改了哪里**
- [ ] 快速验证

**示例**：
```
"登录按钮在手机上点不到，太小了。
把按钮宽度改成屏幕宽度的 80%，高度改成 48px。
完成后告诉我改了哪个文件。"
```

---

### 级别 2：Plan 规范（适用于日常功能开发）

**适用场景**：新功能、中等重构、含交互逻辑的改动

**沟通模板**：

```
📋 需求概述：
[用大白话说清楚想做什么]

🎯 功能要点：
1. [核心功能]
2. [次要功能]
3. [边界条件]

🎨 页面/设计：
- [页面结构]
- [交互行为]
- [状态变化（加载中/空/错误）]

⚠️ 约束：
- 技术栈：[React/Vue/...]
- 不要改：[已有模块/文件]
- 复用：[已有的组件/方法]

📝 请先整理我的需求，列出你理解的开发计划。
有不确定的地方问我，确认后再开始执行。
```

**规范要求**：
- [ ] 需求已用大白话写清
- [ ] AI 已整理并确认理解
- [ ] 开发分步计划已审阅
- [ ] 每步完成后验证
- [ ] 记录开发日志

**开发日志模板**（`docs/dev-log.md`）：
```markdown
## [2026-06-17] 功能名称

**需求简述**：一句话描述
**模式**：Plan
**关键决策**：
- 用了 XX 方案而非 YY，因为...
**变更文件**：
- `src/xxx.ts` — 新增 XXX 组件
- `src/yyy.ts` — 修改 YYY 逻辑
**验证结果**：✅ 通过 / ⚠️ 已知问题：...
**下一步**：...
```

---

### 级别 3：Spec 规范（适用于重要功能/架构变更）

**适用场景**：新模块、架构调整、API 设计、影响多个模块的变更

**沟通模板**（参考 OpenSpec 格式）：

```
/openspec:proposal

## Why
[1-2 句话解释为什么要做这个]

## What I Want
[用大白话描述想要的功能，越详细越好]

## What I Know
- 技术栈：[...]
- 已有相关模块：[...]
- 特殊约束：[...]

## What I Don't Know
[列出你不确定的技术细节，让 AI 帮你决策]
- 比如：用什么库？怎么设计 API？
```

**规范要求**：
- [ ] proposal.md 已审阅确认
- [ ] spec.md 中的 ADDED/MODIFIED/REMOVED 已逐条确认
- [ ] tasks.md 已审阅（粒度合理、顺序合理）
- [ ] design.md 已创建（如果跨模块或有新技术决策）
- [ ] 按 tasks 逐项执行，完成一项 check 一项
- [ ] 完成后 archive，更新开发日志

---

## 四、CLAUDE.md / AGENTS.md 编写规范

根据 [[~ai-coding~/wiki/concepts/Harness Engineering.md|Harness Engineering]] 的地图式导航原则：

### 结构

```markdown
# 项目名称

## 一句话简介
[这个项目是做什么的]

## 技术栈
- 前端：React 18 + TypeScript
- 后端：Node.js + Express
- 数据库：PostgreSQL

## 目录结构
- `src/components/` — UI 组件
- `src/pages/` — 页面
- `src/services/` — API 调用
- `docs/` — 开发文档

## 开发规范
- 所有新组件必须写 TypeScript 类型
- API 调用统一走 `src/services/` 下的封装
- 样式使用 Tailwind CSS

## 当前状态
[简要说明当前开发到什么阶段]

## 关键参考
- 架构设计：[[docs/architecture.md]]
- API 文档：[[docs/api.md]]
```

**🚫 不要做**：
- 把所有编码规范全部塞进去（>500 行 → 模型注意力稀释）
- 把具体实现细节写进去（那应该是 Spec 文档的事）

**✅ 要做**：
- 作为导航地图，指向更详细的文档
- 只写当前项目特有的约定（通用规范放在 Skill 里）
- 不超过 300-500 行

---

## 五、对话规范

### 每次对话的基本流程

```
1. 说清楚你要什么            ← Vibe 的灵活表达
2. 等 AI 复述确认            ← Spec 的需求澄清
3. 审阅 AI 的计划/方案        ← Plan/Spec 的刹车点
4. 确认 → 执行               ← 人决定，AI 干活
5. 验证结果                  ← Harness 的机械验证
6. 记入开发日志              ← DADD 的文档沉淀
```

### 高效沟通技巧

| 技巧 | 示例 | 来源 |
|------|------|------|
| **截图代替长描述** | 截图 + "这个窗口太小了，调大" | Vibe 实战 |
| **给 AI 选择题** | "A 方案还是 B 方案？你觉得呢？" | Plan Mode |
| **脱钩文案** | "我暂时就这些想法了，你先整理，有不确定的问我" | Spec 驱动 |
| **每步验证** | "第一阶段完成了告诉我，我验证后再继续" | Vibe 实战 |
| **让 AI 自述** | "完成后列出你改了哪些文件，为什么这么改" | Harness |

### 不该做的事

| 反模式 | 为什么不好 | 正确做法 |
|--------|-----------|---------|
| "帮我做一个电商系统" | 太宽泛，AI 猜测不可控 | 用 Spec 模式，先澄清需求 |
| 不看 AI 的计划就直接执行 | 相当于闭着眼开车 | Plan/Spec 模式必须先审阅 |
| 一次性让 AI 生成全部代码 | 上下文爆炸 + 雪崩式 bug | 分阶段推进 |
| AI 报错后自己改代码 | 破坏 AI 对项目的认知 | 把报错喂给 AI，让它自愈 |
| 不写开发日志 | 明天就忘了今天做了什么 | 每次对话后 3 分钟记录 |
| 只跑 `type-check` 就宣称可交付 | `vue-tsc --noEmit` 与 `vue-tsc -b`（build）规则集不同，门禁假绿 | 本地/CI 必须 type-check **且** production build |
| 巨型 Vue 单文件上继续堆功能 | 模板类型注解、状态竞态、局部修改牵连全页 | 先拆展示组件/composable，再加功能 |
| 把 ESLint/Ruff 一次开到最严 | 全仓 format 爆炸，掩盖真正缺陷 | 先 E/F 或 essential，显式忽略行宽等风格债 |
| 工作区攒 2000 行再一次提交 | 无法回退、无法评审、无法定位回归 | 按可验证切片 commit（功能/修复/门禁/文档分开） |

---

## 六、测试规范

根据 [[~ai-coding~/wiki/concepts/文档驱动开发 DADD.md|DADD 原则]]：

> 开发效率来自于自动测试，不是来自于 AI 生成速度。

### 测试要求分级

| 场景 | 测试要求 |
|------|---------|
| Vibe（小改） | 人工验证即可 |
| Plan（日常功能） | AI 生成测试用例 + 人工验证核心路径 |
| Spec（重要功能） | TDD：先写测试规格 → AI 生成测试代码 → AI 生成实现代码 → 自动跑测试 |
| 企业级 | 多 AI 竞争评审 + 自动化测试 + 人工抽查 |
| **交付门禁（任何准备合并的改动）** | 见下文「机械门禁」：lint + 类型检查 + 单测 + 构建 +（后端）pytest；**人记不得跑的检查不算门禁** |

### 机械门禁（推荐默认）

把「能合并」定义成**一条命令**或 CI 同构步骤，而不是口头约定：

```bash
# 示例：仓库根 scripts/check.sh（与 CI 命令集对齐）
backend:  ruff check → pytest
frontend: eslint → type-check → unit test → production build
```

| 层级 | 拦什么 | 注意 |
|------|--------|------|
| Lint（Ruff / ESLint） | 未用变量、明显错误 | **渐进开启**；先不强制全仓 format |
| 类型检查 | 接口漂移、错误调用 | Vue 项目见「type-check ≠ build」 |
| 单元测试 | 纯函数与边界（同比上期、覆盖率聚合等） | 优先测**已抽离的 utils/composable**，不要先测巨型 SFC |
| 构建 | 打包期才暴露的模板/TS 问题 | 必须进 CI |
| API 烟测 | 主链路：建档 → 写数 → 读分析 | 可不依赖 PDF/外网 fixture，保证 CI 稳态 |
| 黄金样本（解析类） | 改映射规则不伤旧公司 | PDF 大文件可用 LFS/本地 fixture；黄金 JSON 进库 |

**原则**：CI 红必须能挡住「类型挂了 / 主路径断了 / 构建不过」；风格债用 ignore 显式挂账，而不是假装不存在。

### TDD 对话模板（Spec 级别）

```
"这次的需求是 [xxx]。

请按以下步骤执行：
1. 先根据 spec.md 生成测试用例
2. 让我确认测试用例是否覆盖全面
3. 确认后再写实现代码
4. 写完代码后自动运行测试
5. 如果测试不通过，自动修复直到全部通过（最多尝试 3 次）"
```

### 纯函数优先可测

UI 巨型页难测时，先把**可判定逻辑**抽到 `utils/` / `composables/`，再写单测：

| 适合单测 | 示例 |
|----------|------|
| 聚合与阈值 | 覆盖率 hit/total、标签颜色分档 |
| 时间序列定位 | 同比「上期」= 当前选中期之前最近有值一期（勿用全局次新） |
| 解析/格式化 | 金额、期间标签、原因码中文映射 |

对话提示词可写：

```
"先把 XX 逻辑抽成纯函数（不碰 UI），补 3～8 个边界用例（缺期/未来期干扰/零分母），
再改页面引用。单测必须在 CI 里跑。"
```

---

## 七、项目文件结构建议

```
my-project/
├── CLAUDE.md / AGENTS.md      # AI 自我说明书（地图式导航）
├── openspec/                  # OpenSpec（Spec 模式）
│   ├── project.md             # 范围、非目标、backlog 状态
│   ├── AGENTS.md
│   └── changes/               # 进行中 + 已归档变更包
├── docs/
│   ├── dev-log.md             # 开发日志（每次对话后更新）
│   ├── architecture.md
│   ├── api.md
│   ├── plans/                 # 可执行修改计划（多阶段路线）
│   └── archive/               # 评价/纪要归档（带日期）
├── scripts/
│   ├── check.sh               # 与 CI 同构的一键门禁
│   └── start-dev.sh / …
├── .github/workflows/ci.yml   # push/PR 自动门禁
├── tests/ 或 backend/tests/   # 含 e2e smoke / 黄金样本
├── src/ 或 frontend/ + backend/
└── README.md                  # 环境要求写清（如 Node 必须有，仅 Bun 不够）
```

---

## 八、快速参考卡

### 我要做什么？ → 用什么模式？ → 做什么文档？

| 我要... | 用... | 文档产出 |
|---------|-------|---------|
| 修个 bug | Vibe | 无（AI 自述改动即可） |
| 加个小功能 | Vibe / Plan | dev-log 记录 |
| 加个页面 | Plan | dev-log + plan 文档 |
| 重构一个模块 | Plan | dev-log + plan 文档 |
| 新建一个模块 | Spec | proposal + spec + tasks + dev-log |
| 改 API 接口 | Spec | proposal + spec + tasks + migration 说明 |
| 从零开始一个项目 | Spec | proposal + spec + tasks + design + CLAUDE.md |
| 恢复交付/加 CI/拆巨页 | Plan（可附 `docs/plans/`） | plan + dev-log；门禁命令写进 README |

### AI 说了什么？ → 我要做什么？

| AI 的行为 | 我的应对 |
|-----------|---------|
| AI 直接开始写代码 | "等一下，先整理需求，确认后再写。" |
| AI 问了我不懂的问题 | "我是小白，你给我几个选项让我选。" |
| AI 生成的代码跑不通 | 把报错截图/复制给 AI，让它自愈 |
| AI 一次性想做完所有功能 | "分阶段来，先做核心功能。" |
| AI 用了新的技术/库 | "为什么选这个？有其他方案吗？" |
| AI 修改了不该改的代码 | 明确指出："不要改 xxx 文件，只改 yyy" |
| AI 说 type-check 过了 | "再跑 production build 和 CI 同构的 check.sh。" |
| AI 要一次 format 全仓 | "否。Lint 只开低争议规则，风格债显式 ignore。" |

---

## 九、工程实践备忘（来自真实项目踩坑）

> 归纳自 Web_Financial_Analyse post-1.0 可靠性治理（2026-07）：门禁假绿、巨型 Vue 拆分、切片提交、解析回归。可直接当对话约束贴给 AI。

### 9.1 Vue / TypeScript 门禁

1. **模板里不要写 TypeScript 类型注解**  
   - 错误：`@click="(p: { name?: string }) => …"`、`row.periods.map((p: { label: string }) => …)`  
   - 正确：在 `<script setup>` 里声明具名函数，模板只写 `@click="onFoo"` / `{{ formatLabels(row.periods) }}`  
   - 原因：`vue-tsc --noEmit` 有时能过，**`vue-tsc -b`（build）会挂**，造成「本地 type-check 绿、CI build 红」。

2. **type-check ≠ build，两条都要跑**  
   - 交付定义必须包含 production build，不能只跑 IDE/type-check。  
   - `package.json` 的 `build` 若含 `vue-tsc -b`，CI 必须执行完整 `build`。

3. **运行时与工具链要分开满足**  
   - 仅安装 Bun、系统没有 `node` 时，`node_modules/.bin/vue-tsc` 的 shebang 会直接失败。  
   - README / AGENTS 写明：**Node.js 18+ 必装**（包管理可用 npm/bun/pnpm）。  
   - `scripts/check.sh` 应自动探测常见 Node 路径并给出可执行的安装提示。

### 9.2 静态检查要「能拦错」而不是「先开战」

| 做法 | 说明 |
|------|------|
| Ruff 先开 `E`+`F`，**忽略 E501** | 行宽债一次清会淹没 diff；未用 import/变量优先清 |
| ESLint flat + vue essential + TS recommended | 先 `no-unused-vars`、`vue/no-mutating-props`；关掉 multi-word / explicit-any 等噪音 |
| 0 errors 再进 CI | 允许 warnings 渐进，但 **error 必须为 0 才能合并** |
| 与 check.sh / CI 同构 | 禁止「文档写了 lint、流水线没跑」 |

### 9.3 巨型前端页拆分纪律

当单文件 > ~800～1000 行（尤其 Import / Analysis / Compare）：

1. **先止血门禁，再拆分**；拆分 PR **禁止夹带产品功能**。  
2. 顺序：**纯展示组件（props in / emit out）→ composable 收状态 → 容器只编排**。  
3. 优先切**天然边界**：Tab 面板、映射质量区、图表+坐标控件、队列导航。  
4. 跨子域通信用 `v-model:xxx` + 事件（如 `@review-jobs`），避免深层 props 钻透。  
5. ECharts：固定高度 `.chart-host`；切换 period/role 用 **remount key**，父级避免 `overflow: hidden` 导致塌陷。  
6. 目标：容器页大约 **200～400 行**可读；逻辑在 composable，展示在 `components/<domain>/`。

**对话约束示例**：

```
"只做拆分，不改交互。先抽 MappingQuality / ExcelPanel，每步 type-check+build 绿再下一步。
禁止顺手加功能。完成后报各文件行数。"
```

### 9.4 Git 与协作

1. **大工作区必须切片提交**  
   建议序：修复 → 功能后端 → 功能前端 → 门禁/工具链 → 文档。  
   禁止一个 commit 同时塞「批量拉取 + 公司名识别 + unmapped UX + 文档」。

2. **GitHub Actions 工作流文件需要 `workflow` scope**  
   - 新建/修改 `.github/workflows/*` 时，若 token 只有 `repo`，push 会被拒。  
   - 处理：`gh auth refresh -h github.com -s workflow -s repo`，确认 `gh auth status` 含 `workflow` 后再 push。  
   - 设备码授权必须在 **命令等待期间** 于浏览器完成，过期需重来。

3. **评价/计划要归档**  
   - 外部评价进 `docs/archive/YYYY-MM-DD-….md`，并附「仓库核对」附录。  
   - 可执行路线进 `docs/plans/`，状态与 `openspec/project.md` backlog 对齐。

### 9.5 数据与解析类项目的额外约束

| 点 | 建议 |
|----|------|
| 财务数字 | **禁止自动无人确认入库**；review → 人审 commit |
| 映射质量 | 后端已有 coverage/unmapped 必须在核对 UI 展示；低覆盖二次确认 |
| 公司名识别 | 封面/发行人优先，跳过「简称 指 全称」释义；拉取预填可覆盖误解析 |
| 解析回归 | 固定 PDF + 黄金 JSON（公司/年/单位/核心科目/关键金额容差） |
| SQLite 演进 | 启动期 `ADD COLUMN` 只适合早期；真实数据多了要备份脚本，再考虑正式迁移 |

### 9.6 给 AI 的一段「总约束」（可复制）

```
约束：
1. 先对齐再改；改完跑与 CI 同构的 check（含 build，不只 type-check）。
2. Vue 模板禁止 TS 类型注解；抽 script 函数。
3. 巨页先拆再加功能；拆分 PR 行为不变。
4. Lint 渐进，禁止全仓 format 大爆炸。
5. 大改动按可验证切片 commit；workflow 文件注意 gh workflow scope。
6. 可测逻辑进 utils/composable 并补边界单测；主链路保留 API 烟测。
7. 结束后更新 docs/dev-log.md，需要时更新 plans/project backlog。
```


