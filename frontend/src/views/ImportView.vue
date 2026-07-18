<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Document, UploadFilled } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox, type TableInstance, type UploadRequestOptions } from 'element-plus'
import { storeToRefs } from 'pinia'
import {
  type ImportJob,
  type UnmappedRow,
  commitImportJob,
  fetchImportJob,
  updateImportJob,
  uploadFiling,
} from '@/api/importFiling'
import {
  commitExcelImport,
  downloadExcelTemplate,
  previewExcelImport,
  type ExcelImportPreview,
  type ExcelImportResult,
} from '@/api/excel'
import {
  downloadCninfoFiling,
  fetchFromUrl,
  searchCninfoAnnualYears,
  searchCninfoSecurities,
  type CninfoBatchYearResult,
  type FilingCandidate,
  type StockSecurity,
} from '@/api/fetchFiling'
import { STATEMENT_META, type StatementKind } from '@/constants/statementFields'
import { useCompanyStore } from '@/stores/company'
import type { PeriodType } from '@/api/compare'

const router = useRouter()
const companyStore = useCompanyStore()
const { companies } = storeToRefs(companyStore)

const mainTab = ref<'fetch' | 'pdf' | 'excel'>('fetch')

// ---- PDF 年报 ----
const step = ref(0)
const loading = ref(false)
const committing = ref(false)
const batchCommitting = ref(false)
const job = ref<ImportJob | null>(null)
/** 在线拉取/多份 PDF：可左右切换的核对队列 */
const reviewJobs = ref<ImportJob[]>([])
const reviewIndex = ref(0)

const kinds: StatementKind[] = ['balance', 'income', 'cashflow']
const kindLabel: Record<StatementKind, string> = {
  balance: '资产负债表',
  income: '利润表',
  cashflow: '现金流量表',
}

const statements = computed(() => job.value?.draft?.statements || {})
const fillModeText = computed(() => {
  const m = job.value?.fill_mode
  if (m === 'AUTO_COMMIT_CANDIDATE') return '高置信，可确认入库'
  if (m === 'REVIEW_REQUIRED') return '需人工核对后入库'
  return '置信不足，请检查后决定'
})

const reviewTotal = computed(() => reviewJobs.value.length)
const isMultiReview = computed(() => reviewTotal.value > 1)
const reviewCommittedCount = computed(
  () => reviewJobs.value.filter((j) => j.status === 'committed').length
)
const reviewPendingCount = computed(
  () =>
    reviewJobs.value.filter(
      (j) => j.status !== 'committed' && j.status !== 'failed'
    ).length
)

const UNMAPPED_REASON_LABEL: Record<string, string> = {
  no_alias_match: '无别名匹配',
  low_score: '匹配分过低',
  ambiguous: '多科目歧义',
  skip_total_cost: '跳过营业总成本',
}

type CoverageRow = {
  kind: StatementKind
  label: string
  coreHit: number
  coreTotal: number
  mappedFields: number
  /** 0–100 */
  pct: number
}

const coverageRows = computed((): CoverageRow[] => {
  const cov = job.value?.coverage || {}
  return kinds.map((kind) => {
    const c = cov[kind] || {}
    const coreTotal = Number(c.core_total ?? 0)
    const coreHit = Number(c.core_hit ?? 0)
    const mappedFields = Number(c.mapped_fields ?? 0)
    const rate = typeof c.coverage === 'number' ? c.coverage : coreTotal ? coreHit / coreTotal : 0
    return {
      kind,
      label: kindLabel[kind],
      coreHit,
      coreTotal,
      mappedFields,
      pct: Math.round(Math.max(0, Math.min(1, rate)) * 100),
    }
  })
})

const overallCoveragePct = computed(() => {
  const rows = coverageRows.value
  const total = rows.reduce((s, r) => s + r.coreTotal, 0)
  if (!total) return null
  const hit = rows.reduce((s, r) => s + r.coreHit, 0)
  return Math.round((hit / total) * 100)
})

const issueList = computed(() => {
  const list = job.value?.issues
  return Array.isArray(list) ? list.map(String).filter(Boolean) : []
})

const unmappedRows = computed((): UnmappedRow[] => {
  const list = job.value?.unmapped
  return Array.isArray(list) ? list : []
})

const unmappedFilterKind = ref<'all' | StatementKind>('all')

const filteredUnmapped = computed(() => {
  const rows = unmappedRows.value
  if (unmappedFilterKind.value === 'all') return rows
  return rows.filter((r) => r.statement === unmappedFilterKind.value)
})

const unmappedCountByKind = computed(() => {
  const counts: Record<string, number> = { all: unmappedRows.value.length }
  for (const k of kinds) counts[k] = 0
  for (const r of unmappedRows.value) {
    const s = r.statement || ''
    if (s in counts) counts[s] += 1
  }
  return counts
})

function coverageTagType(pct: number): 'success' | 'warning' | 'danger' | 'info' {
  if (pct >= 80) return 'success'
  if (pct >= 50) return 'warning'
  if (pct > 0) return 'danger'
  return 'info'
}

function reasonLabel(reason?: string): string {
  if (!reason) return '—'
  return UNMAPPED_REASON_LABEL[reason] || reason
}

function statementLabel(kind?: string): string {
  if (!kind) return '—'
  if (kind in kindLabel) return kindLabel[kind as StatementKind]
  return kind
}

function formatMoney(v: unknown): string {
  if (v === null || v === undefined || v === '') return '—'
  const n = Number(v)
  if (Number.isNaN(n)) return '—'
  return n.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

/** Excel 预览：期间标签列表（避免模板内 TS 注解） */
function formatPeriodLabels(periods: { label?: string }[] | null | undefined): string {
  if (!periods?.length) return '—'
  return periods.map((p) => p.label || '—').join('、')
}

function fieldLabel(kind: StatementKind, key: string): string {
  for (const g of STATEMENT_META[kind].groups) {
    const f = g.fields.find((x) => x.key === key)
    if (f) return f.label
  }
  return key
}

async function customUpload(opt: UploadRequestOptions) {
  loading.value = true
  try {
    const file = opt.file as File
    const uploaded = await uploadFiling(file)
    await enterReviewQueue([uploaded])
    opt.onSuccess?.(uploaded)
  } catch (e) {
    opt.onError?.(e as Parameters<NonNullable<UploadRequestOptions['onError']>>[0])
  } finally {
    loading.value = false
  }
}

async function saveMeta(opts?: { silent?: boolean }) {
  if (!job.value) return
  loading.value = true
  try {
    job.value = await updateImportJob(job.value.id, {
      company_id: fetchCompanyId.value ?? job.value.company_id,
      company_hint: job.value.company_hint,
      report_year: job.value.report_year,
      period_type: job.value.period_type || 'annual',
      quarter: job.value.quarter,
      statements: statements.value as Record<string, Record<string, number | null>>,
    })
    syncCurrentIntoQueue()
    if (!opts?.silent) ElMessage.success('已更新')
  } finally {
    loading.value = false
  }
}

function syncCurrentIntoQueue() {
  if (!job.value || !reviewJobs.value.length) return
  const i = reviewJobs.value.findIndex((j) => j.id === job.value!.id)
  if (i >= 0) reviewJobs.value[i] = job.value
}

async function handleCommit() {
  if (!job.value) return
  if (!job.value.report_year) {
    ElMessage.warning('请先填写报告年份')
    return
  }
  if (overallCoveragePct.value !== null && overallCoveragePct.value < 50) {
    try {
      await ElMessageBox.confirm(
        `核心科目覆盖仅 ${overallCoveragePct.value}%，仍可能有重要科目未识别。确认入库？`,
        '覆盖率偏低',
        { type: 'warning', confirmButtonText: '仍要入库', cancelButtonText: '再核对' }
      )
    } catch {
      return
    }
  }
  committing.value = true
  try {
    await saveMeta({ silent: true })
    job.value = await commitImportJob(job.value.id, {
      company_id: fetchCompanyId.value ?? job.value.company_id,
      overwrite: true,
    })
    syncCurrentIntoQueue()
    ElMessage.success(
      `已入库${job.value.report_year ? ` · ${job.value.report_year} 年报` : ''}`
    )
    if (!isMultiReview.value) step.value = 2
  } finally {
    committing.value = false
  }
}

async function handleBatchCommit() {
  if (!reviewJobs.value.length) {
    await handleCommit()
    return
  }
  const pending = reviewJobs.value.filter(
    (j) => j.status !== 'committed' && j.status !== 'failed'
  )
  if (!pending.length) {
    ElMessage.info('队列中没有待入库任务')
    return
  }
  const missingYear = pending.find((j) => !j.report_year)
  if (missingYear) {
    ElMessage.warning(`任务 #${missingYear.id} 缺少报告年份，请先补全`)
    const idx = reviewJobs.value.findIndex((j) => j.id === missingYear.id)
    if (idx >= 0) await selectReviewIndex(idx)
    return
  }
  const lowCov = pending.filter((j) => {
    const cov = j.coverage || {}
    let hit = 0
    let total = 0
    for (const k of kinds) {
      const c = cov[k]
      if (!c) continue
      hit += Number(c.core_hit ?? 0)
      total += Number(c.core_total ?? 0)
    }
    if (!total) return false
    return hit / total < 0.5
  })
  if (lowCov.length) {
    const years = lowCov
      .map((j) => j.report_year || `#${j.id}`)
      .join('、')
    try {
      await ElMessageBox.confirm(
        `${lowCov.length} 份任务核心科目覆盖 < 50%（${years}）。仍批量入库？`,
        '部分覆盖率偏低',
        { type: 'warning', confirmButtonText: '仍要入库', cancelButtonText: '再核对' }
      )
    } catch {
      return
    }
  }
  batchCommitting.value = true
  let ok = 0
  let err = 0
  try {
    // 先保存当前页编辑
    if (job.value && job.value.status !== 'committed') {
      try {
        await saveMeta({ silent: true })
      } catch {
        /* continue others */
      }
    }
    for (let i = 0; i < reviewJobs.value.length; i++) {
      const j = reviewJobs.value[i]
      if (j.status === 'committed' || j.status === 'failed') continue
      try {
        // 切换到该 job 以带上其 draft（已在队列中）
        const saved = await updateImportJob(j.id, {
          company_id: fetchCompanyId.value ?? j.company_id,
          company_hint: j.company_hint,
          report_year: j.report_year,
          period_type: j.period_type || 'annual',
          quarter: j.quarter,
          statements: (j.draft?.statements || {}) as Record<
            string,
            Record<string, number | null>
          >,
        })
        const committed = await commitImportJob(saved.id, {
          company_id: fetchCompanyId.value ?? saved.company_id,
          overwrite: true,
        })
        reviewJobs.value[i] = committed
        if (job.value?.id === committed.id) job.value = committed
        ok += 1
      } catch {
        err += 1
      }
    }
    ElMessage.success(`批量入库完成：成功 ${ok} · 失败 ${err}`)
    if (ok > 0 && reviewPendingCount.value === 0) step.value = 2
  } finally {
    batchCommitting.value = false
  }
}

function goStatements() {
  router.push('/statements')
}

// ---- Excel 模板 ----
const excelCompanyId = ref<number | null>(null)
const excelPeriodType = ref<PeriodType>('annual')
const templateYears = ref<string>(`${new Date().getFullYear() - 2},${new Date().getFullYear() - 1},${new Date().getFullYear()}`)
const excelFile = ref<File | null>(null)
const excelPreview = ref<ExcelImportPreview | null>(null)
const excelResult = ref<ExcelImportResult | null>(null)
const excelLoading = ref(false)
const excelOverwrite = ref(true)

async function onDownloadTemplate() {
  excelLoading.value = true
  try {
    const years = templateYears.value
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean)
      .map((s) => Number(s))
      .filter((n) => !Number.isNaN(n))
    await downloadExcelTemplate({
      period_type: excelPeriodType.value,
      years: years.length ? years : undefined,
    })
    ElMessage.success('模板已下载')
  } catch {
    // interceptor
  } finally {
    excelLoading.value = false
  }
}

async function onExcelFile(opt: UploadRequestOptions) {
  if (excelCompanyId.value == null) {
    ElMessage.warning('请先选择企业')
    opt.onError?.(new Error('no company') as never)
    return
  }
  excelLoading.value = true
  excelResult.value = null
  try {
    const file = opt.file as File
    excelFile.value = file
    excelPreview.value = await previewExcelImport(excelCompanyId.value, file)
    ElMessage.success('解析完成，请确认预览后入库')
    opt.onSuccess?.(excelPreview.value)
  } catch (e) {
    excelPreview.value = null
    excelFile.value = null
    opt.onError?.(e as Parameters<NonNullable<UploadRequestOptions['onError']>>[0])
  } finally {
    excelLoading.value = false
  }
}

async function onExcelCommit() {
  if (excelCompanyId.value == null || !excelFile.value) {
    ElMessage.warning('请先选择企业并上传文件')
    return
  }
  excelLoading.value = true
  try {
    excelResult.value = await commitExcelImport(
      excelCompanyId.value,
      excelFile.value,
      excelOverwrite.value
    )
    ElMessage.success(
      `入库完成：新建 ${excelResult.value.created.length}，更新 ${excelResult.value.updated.length}`
    )
  } catch {
    // interceptor
  } finally {
    excelLoading.value = false
  }
}

// ---- 在线拉取（URL + 巨潮）----
const fetchCompanyId = ref<number | null>(null)
const fetchQuery = ref('')
/** 统一年份输入：`2024` 或 `2022-2024` / `2022,2023,2024` */
const fetchYearsText = ref(String(new Date().getFullYear() - 1))
const fetchUrl = ref('')
const fetchSecurities = ref<StockSecurity[]>([])
const fetchSelected = ref<StockSecurity | null>(null)
const fetchCandidates = ref<FilingCandidate[]>([])
const selectedCandidateKeys = ref<string[]>([])
const fetchLoading = ref(false)
const fetchDownloading = ref(false)
const batchResults = ref<CninfoBatchYearResult[]>([])
const batchSummary = ref<{ ok: number; empty: number; error: number } | null>(null)
const candidateTableRef = ref<TableInstance>()

const createCompanyVisible = ref(false)
const creatingCompany = ref(false)
const createCompanyForm = ref({ name: '', code: '', industry: '' })

function candidateKey(row: FilingCandidate): string {
  return `${row.year}|${row.announcement_id || ''}|${row.pdf_url}`
}

function parseYearsInput(raw: string): number[] {
  const s = (raw || '').trim()
  if (!s) return []
  const years: number[] = []
  const seen = new Set<number>()
  const push = (n: number) => {
    if (n < 1990 || n > 2100 || seen.has(n)) return
    seen.add(n)
    years.push(n)
  }
  for (const part of s.split(/[,，\s]+/).filter(Boolean)) {
    const range = part.match(/^(\d{4})\s*[-~～至]\s*(\d{4})$/)
    if (range) {
      let a = Number(range[1])
      let b = Number(range[2])
      if (a > b) [a, b] = [b, a]
      for (let y = a; y <= b; y++) push(y)
      continue
    }
    if (/^\d{4}$/.test(part)) push(Number(part))
  }
  years.sort((a, b) => a - b)
  return years
}

const parsedYears = computed(() => parseYearsInput(fetchYearsText.value))

const selectedCandidates = computed(() => {
  const set = new Set(selectedCandidateKeys.value)
  return fetchCandidates.value.filter((c) => set.has(candidateKey(c)))
})
async function enterReviewQueue(jobs: ImportJob[], opts?: { message?: string }) {
  const list = jobs.filter(Boolean)
  if (!list.length) {
    ElMessage.warning('没有可核对的导入任务')
    return
  }
  // 绑定关联企业（若已选）
  const bound: ImportJob[] = []
  for (const j of list) {
    if (fetchCompanyId.value && j.company_id !== fetchCompanyId.value && j.status !== 'committed') {
      try {
        bound.push(
          await updateImportJob(j.id, { company_id: fetchCompanyId.value })
        )
        continue
      } catch {
        /* use original */
      }
    }
    bound.push(j)
  }
  reviewJobs.value = bound
  reviewIndex.value = 0
  job.value = bound[0]
  step.value = 1
  mainTab.value = 'pdf'
  const failed = bound.filter((j) => j.status === 'failed').length
  if (opts?.message) {
    ElMessage.success(opts.message)
  } else if (bound.length === 1) {
    if (bound[0].status === 'failed') {
      ElMessage.warning(bound[0].error_message || '解析失败，请检查 PDF')
    } else {
      ElMessage.success('已解析，请核对后确认入库')
    }
  } else {
    ElMessage.success(
      `已解析 ${bound.length} 份年报${failed ? `（失败 ${failed}）` : ''}，可用左右切换预览，再批量确认入库`
    )
  }
}

function openJobForReview(j: ImportJob) {
  void enterReviewQueue([j])
}

async function selectReviewIndex(i: number) {
  if (i < 0 || i >= reviewJobs.value.length) return
  // 软保存当前页（不阻断切换）
  if (job.value && job.value.status !== 'committed' && job.value.status !== 'failed') {
    try {
      await saveMeta({ silent: true })
    } catch {
      /* keep going */
    }
  }
  reviewIndex.value = i
  job.value = reviewJobs.value[i]
  unmappedFilterKind.value = 'all'
}

async function goPrevReview() {
  if (reviewIndex.value <= 0) return
  await selectReviewIndex(reviewIndex.value - 1)
}

async function goNextReview() {
  if (reviewIndex.value >= reviewJobs.value.length - 1) return
  await selectReviewIndex(reviewIndex.value + 1)
}

function matchLocalCompany(stock: StockSecurity) {
  const byCode = companies.value.find((c) => c.code && c.code === stock.code)
  if (byCode) {
    fetchCompanyId.value = byCode.id
    return
  }
  if (stock.name) {
    const byName = companies.value.find((c) => c.name === stock.name)
    if (byName) fetchCompanyId.value = byName.id
  }
}

async function loadAnnualForCode(code: string) {
  const years = parsedYears.value
  if (!years.length) {
    ElMessage.warning('请填写年份，如 2024 或 2022-2024')
    return
  }
  if (years.length > 12) {
    ElMessage.warning('单次最多 12 个年份')
    return
  }
  let rows = await searchCninfoAnnualYears(code, years)
  // 仅查 1 年且无结果时，自动试上一年
  if (!rows.length && years.length === 1 && years[0] > 1990) {
    const prev = years[0] - 1
    rows = await searchCninfoAnnualYears(code, [prev])
    if (rows.length) {
      fetchYearsText.value = String(prev)
      ElMessage.info(`已自动改用 ${prev} 年（${years[0]} 年无全文年报）`)
    }
  }
  fetchCandidates.value = rows
  batchResults.value = []
  batchSummary.value = null
  await nextTick()
  selectedCandidateKeys.value = rows.map(candidateKey)
  const table = candidateTableRef.value
  if (table) {
    table.clearSelection()
    for (const row of rows) table.toggleRowSelection(row, true)
  }
  if (!rows.length) {
    ElMessage.warning(
      `未找到 ${code} 在 ${years.join(',')} 的「年度报告」全文。请确认 A 股代码或调整年份。`
    )
  } else {
    const ys = [...new Set(rows.map((r) => r.year))].sort()
    ElMessage.success(`找到 ${rows.length} 份候选（覆盖 ${ys.join('、')} 年），已默认全选`)
  }
}

async function onSearchCninfo() {
  const q = fetchQuery.value.trim()
  if (!q) {
    ElMessage.warning('请填写证券代码或公司名称')
    return
  }
  if (!parsedYears.value.length) {
    ElMessage.warning('请填写年份，如 2024 或 2022-2024')
    return
  }
  fetchLoading.value = true
  fetchSecurities.value = []
  fetchCandidates.value = []
  selectedCandidateKeys.value = []
  fetchSelected.value = null
  try {
    fetchSecurities.value = await searchCninfoSecurities(q)
    if (!fetchSecurities.value.length) {
      ElMessage.warning(`未找到证券：${q}（可试简称，如「科沃斯」「贵州茅台」）`)
      return
    }
    let pick = fetchSecurities.value[0]
    if (/^\d{6}$/.test(q)) {
      pick =
        fetchSecurities.value.find((s) => s.code === q) || fetchSecurities.value[0]
    }
    if (fetchSecurities.value.length === 1 || /^\d{6}$/.test(q)) {
      await onPickSecurity(pick)
    } else {
      ElMessage.success(
        `找到 ${fetchSecurities.value.length} 只证券，请点击「选此公司」查看年报`
      )
    }
  } catch {
    /* http 拦截器已提示 */
  } finally {
    fetchLoading.value = false
  }
}

async function onPickSecurity(row: StockSecurity) {
  fetchSelected.value = row
  fetchQuery.value = row.code
  matchLocalCompany(row)
  fetchLoading.value = true
  fetchCandidates.value = []
  selectedCandidateKeys.value = []
  try {
    await loadAnnualForCode(row.code)
  } catch {
    /* interceptor */
  } finally {
    fetchLoading.value = false
  }
}

function openCreateCompanyDialog() {
  const s = fetchSelected.value
  createCompanyForm.value = {
    name: s?.name || fetchQuery.value.trim() || '',
    code: s?.code || (/^\d{6}$/.test(fetchQuery.value.trim()) ? fetchQuery.value.trim() : ''),
    industry: s?.industry || '',
  }
  createCompanyVisible.value = true
}

async function submitCreateCompany() {
  const name = createCompanyForm.value.name.trim()
  if (!name) {
    ElMessage.warning('请填写企业名称')
    return
  }
  creatingCompany.value = true
  try {
    const created = await companyStore.add({
      name,
      code: createCompanyForm.value.code.trim() || null,
      industry: createCompanyForm.value.industry.trim() || null,
    })
    fetchCompanyId.value = created.id
    createCompanyVisible.value = false
    ElMessage.success(
      `已创建并关联：${created.name}${created.code ? ' · ' + created.code : ''}${
        created.industry ? ' · ' + created.industry : ''
      }`
    )
  } catch {
    /* interceptor / store */
  } finally {
    creatingCompany.value = false
  }
}

async function onImportSelected() {
  const rows = selectedCandidates.value
  if (!rows.length) {
    ElMessage.warning('请先勾选要导入的年报')
    return
  }
  fetchDownloading.value = true
  batchResults.value = []
  batchSummary.value = null
  const results: CninfoBatchYearResult[] = []
  let ok = 0
  let err = 0
  try {
    for (const row of rows) {
      try {
        const j = await downloadCninfoFiling({
          pdf_url: row.pdf_url,
          code: row.code,
          title: row.title,
          year: row.year,
          name: row.name,
          company_id: fetchCompanyId.value,
        })
        results.push({
          year: row.year,
          status: 'ok',
          title: row.title,
          pdf_url: row.pdf_url,
          job_id: j.id,
          detail: null,
        })
        ok += 1
      } catch (e: unknown) {
        const detail =
          e && typeof e === 'object' && 'message' in e
            ? String((e as { message?: string }).message)
            : '下载失败'
        results.push({
          year: row.year,
          status: 'error',
          title: row.title,
          pdf_url: row.pdf_url,
          job_id: null,
          detail,
        })
        err += 1
      }
    }
    batchResults.value = results
    batchSummary.value = { ok, empty: 0, error: err }
    ElMessage.success(`下载解析完成：成功 ${ok} · 失败 ${err}`)
    if (ok > 0) {
      const jobs: ImportJob[] = []
      for (const r of results) {
        if (r.status === 'ok' && r.job_id != null) {
          try {
            jobs.push(await fetchImportJob(r.job_id))
          } catch {
            /* skip */
          }
        }
      }
      // 按年份排序便于左右切换
      jobs.sort((a, b) => (a.report_year || 0) - (b.report_year || 0))
      await enterReviewQueue(jobs)
    }
  } finally {
    fetchDownloading.value = false
  }
}

async function onFetchUrl() {
  if (!fetchUrl.value.trim()) {
    ElMessage.warning('请填写 PDF URL')
    return
  }
  fetchDownloading.value = true
  try {
    const j = await fetchFromUrl({
      url: fetchUrl.value.trim(),
      company_id: fetchCompanyId.value,
    })
    openJobForReview(j)
  } catch {
    /* interceptor */
  } finally {
    fetchDownloading.value = false
  }
}

async function openBatchJob(jobId: number) {
  try {
    const j = await fetchImportJob(jobId)
    openJobForReview(j)
  } catch {
    /* interceptor */
  }
}

function companyOptionLabel(c: { name: string; code: string | null; industry: string | null }) {
  const parts = [c.name]
  if (c.code) parts.push(c.code)
  if (c.industry) parts.push(c.industry)
  return parts.join(' · ')
}

function onCandidateSelectionChange(rows: FilingCandidate[]) {
  selectedCandidateKeys.value = rows.map(candidateKey)
}

function selectAllCandidates() {
  const table = candidateTableRef.value
  if (!table) {
    selectedCandidateKeys.value = fetchCandidates.value.map(candidateKey)
    return
  }
  for (const row of fetchCandidates.value) table.toggleRowSelection(row, true)
}

function clearCandidateSelection() {
  candidateTableRef.value?.clearSelection()
  selectedCandidateKeys.value = []
}


onMounted(async () => {
  await companyStore.load()
  // 不默认强绑第一家企业，避免误导入；用户可新建或选择
})
</script>

<template>
  <div class="import-page">
    <el-tabs v-model="mainTab">
      <el-tab-pane label="在线拉取" name="fetch">
        <div class="panel" v-loading="fetchLoading || fetchDownloading">
          <el-alert
            type="info"
            :closable="false"
            show-icon
            style="margin-bottom: 16px"
            title="年份填一个=单年，填 2022-2024 或 2022,2023,2024=多年。检索后勾选年报再导入；可新建关联企业（自动带代码/行业）。不自动入库。"
          />

          <el-form label-width="100px" class="excel-form">
            <el-form-item label="关联企业">
              <div class="fetch-row">
                <el-select
                  v-model="fetchCompanyId"
                  clearable
                  filterable
                  placeholder="可选，入库时绑定"
                  style="width: 320px"
                >
                  <el-option
                    v-for="c in companies"
                    :key="c.id"
                    :label="companyOptionLabel(c)"
                    :value="c.id"
                  />
                </el-select>
                <el-button type="primary" plain @click="openCreateCompanyDialog">
                  新建企业
                </el-button>
                <span v-if="fetchSelected" class="sub">
                  当前证券：{{ fetchSelected.code }}
                  {{ fetchSelected.name || '' }}
                  <template v-if="fetchSelected.industry">
                    · {{ fetchSelected.industry }}
                  </template>
                </span>
              </div>
            </el-form-item>
          </el-form>

          <el-card shadow="never" class="fetch-card">
            <template #header><strong>巨潮 · 检索年报</strong></template>
            <div class="fetch-row">
              <el-input
                v-model="fetchQuery"
                placeholder="代码或名称，如 603486 / 科沃斯"
                clearable
                style="min-width: 240px; flex: 1"
                @keyup.enter="onSearchCninfo"
              />
              <el-input
                v-model="fetchYearsText"
                placeholder="年份：2024 或 2022-2024"
                clearable
                style="width: 200px"
                @keyup.enter="onSearchCninfo"
              />
              <el-button type="primary" :loading="fetchLoading" @click="onSearchCninfo">
                检索
              </el-button>
            </div>
            <p class="sub" style="margin-top: 8px">
              解析年份：
              <template v-if="parsedYears.length">{{ parsedYears.join('、') }}</template>
              <template v-else>—</template>
              （最多 12 年）
            </p>

            <el-table
              v-if="fetchSecurities.length"
              :data="fetchSecurities"
              size="small"
              border
              highlight-current-row
              style="margin-top: 12px"
              @row-click="onPickSecurity"
            >
              <el-table-column prop="code" label="代码" width="90" />
              <el-table-column prop="name" label="简称" width="120" />
              <el-table-column prop="industry" label="行业" min-width="100" show-overflow-tooltip />
              <el-table-column prop="category" label="类型" width="90" />
              <el-table-column label="操作" width="120" fixed="right">
                <template #default="{ row }">
                  <el-button type="primary" link @click.stop="onPickSecurity(row)">
                    {{ fetchSelected?.code === row.code ? '已选·查年报' : '选此公司' }}
                  </el-button>
                </template>
              </el-table-column>
            </el-table>

            <div v-if="fetchCandidates.length" class="candidate-block">
              <div class="fetch-row" style="margin-bottom: 8px">
                <el-button
                  type="success"
                  :loading="fetchDownloading"
                  :disabled="!selectedCandidateKeys.length"
                  @click="onImportSelected"
                >
                  导入勾选（{{ selectedCandidateKeys.length }}）
                </el-button>
                <el-button link type="primary" @click="selectAllCandidates">全选</el-button>
                <el-button link @click="clearCandidateSelection">清空</el-button>
              </div>
              <el-table
                ref="candidateTableRef"
                :data="fetchCandidates"
                size="small"
                border
                row-key="pdf_url"
                @selection-change="onCandidateSelectionChange"
              >
                <el-table-column type="selection" width="48" />
                <el-table-column prop="year" label="年份" width="80" />
                <el-table-column prop="code" label="代码" width="90" />
                <el-table-column prop="name" label="简称" width="100" />
                <el-table-column prop="title" label="标题" min-width="220" show-overflow-tooltip />
                <el-table-column prop="announce_date" label="公告日" width="120" />
              </el-table>
            </div>
            <p v-else class="sub" style="margin-top: 12px">
              输入代码/名称与年份后点「检索」；多命中时先选证券，再勾选年报导入。
            </p>

            <div v-if="batchResults.length" class="batch-results">
              <div class="batch-summary" v-if="batchSummary">
                导入结果：成功
                <strong>{{ batchSummary.ok }}</strong>
                · 无全文
                <strong>{{ batchSummary.empty }}</strong>
                · 失败
                <strong>{{ batchSummary.error }}</strong>
              </div>
              <el-table :data="batchResults" size="small" border style="margin-top: 8px">
                <el-table-column prop="year" label="年份" width="80" />
                <el-table-column label="状态" width="90">
                  <template #default="{ row }">
                    <el-tag
                      size="small"
                      :type="
                        row.status === 'ok'
                          ? 'success'
                          : row.status === 'empty'
                            ? 'info'
                            : 'danger'
                      "
                    >
                      {{
                        row.status === 'ok'
                          ? '成功'
                          : row.status === 'empty'
                            ? '无全文'
                            : '失败'
                      }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="title" label="标题" min-width="200" show-overflow-tooltip />
                <el-table-column prop="detail" label="说明" min-width="140" show-overflow-tooltip />
                <el-table-column label="操作" width="110" fixed="right">
                  <template #default="{ row }">
                    <el-button
                      v-if="row.status === 'ok' && row.job_id != null"
                      type="primary"
                      link
                      @click="openBatchJob(row.job_id)"
                    >
                      打开核对
                    </el-button>
                    <span v-else class="sub">—</span>
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </el-card>

          <el-card shadow="never" class="fetch-card" style="margin-top: 16px">
            <template #header><strong>PDF 直链</strong></template>
            <div class="fetch-row">
              <el-input v-model="fetchUrl" placeholder="https://.../*.pdf" clearable />
              <el-button type="primary" plain :loading="fetchDownloading" @click="onFetchUrl">
                下载并解析
              </el-button>
            </div>
          </el-card>

          <el-dialog
            v-model="createCompanyVisible"
            title="新建关联企业"
            width="420px"
            destroy-on-close
          >
            <el-form label-width="80px">
              <el-form-item label="名称" required>
                <el-input v-model="createCompanyForm.name" placeholder="企业名称" />
              </el-form-item>
              <el-form-item label="代码">
                <el-input v-model="createCompanyForm.code" placeholder="股票代码" />
              </el-form-item>
              <el-form-item label="行业">
                <el-input
                  v-model="createCompanyForm.industry"
                  placeholder="所属行业（检索证券后自动填充）"
                />
              </el-form-item>
            </el-form>
            <template #footer>
              <el-button @click="createCompanyVisible = false">取消</el-button>
              <el-button type="primary" :loading="creatingCompany" @click="submitCreateCompany">
                创建并关联
              </el-button>
            </template>
          </el-dialog>
        </div>
      </el-tab-pane>
      <el-tab-pane label="Excel 模板导入" name="excel">
        <div class="panel" v-loading="excelLoading">
          <el-alert
            type="info"
            :closable="false"
            show-icon
            title="下载模板 → 填写三表金额 → 上传预览 → 确认入库。财务比率 sheet 会被忽略（入库后动态计算）。"
            style="margin-bottom: 16px"
          />

          <el-form label-width="100px" class="excel-form">
            <el-form-item label="目标企业">
              <el-select
                v-model="excelCompanyId"
                filterable
                placeholder="选择企业"
                style="width: 280px"
              >
                <el-option
                  v-for="c in companies"
                  :key="c.id"
                  :label="c.name"
                  :value="c.id"
                />
              </el-select>
            </el-form-item>
            <el-form-item label="模板期间">
              <el-radio-group v-model="excelPeriodType">
                <el-radio-button value="annual">年报</el-radio-button>
                <el-radio-button value="quarterly">季报</el-radio-button>
              </el-radio-group>
              <el-input
                v-model="templateYears"
                placeholder="年份，逗号分隔"
                style="width: 220px; margin-left: 12px"
              />
              <el-button
                type="primary"
                plain
                style="margin-left: 12px"
                @click="onDownloadTemplate"
              >
                下载空模板
              </el-button>
            </el-form-item>
            <el-form-item label="覆盖已有">
              <el-switch v-model="excelOverwrite" active-text="是" inactive-text="否" />
            </el-form-item>
          </el-form>

          <el-upload
            drag
            :http-request="onExcelFile"
            :show-file-list="false"
            accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
          >
            <div class="upload-inner">
              <el-icon :size="48" color="#409eff"><UploadFilled /></el-icon>
              <div class="tip">拖拽或点击上传已填好的 .xlsx</div>
              <div class="sub">也可上传本系统「导出 Excel」生成的文件（比率 sheet 自动忽略）</div>
            </div>
          </el-upload>

          <div v-if="excelPreview" class="preview-block">
            <h3>预览</h3>
            <p>
              期间类型：{{ excelPreview.period_type || '—' }} · 将新建
              {{ excelPreview.will_create.length }} · 将更新
              {{ excelPreview.will_update.length }} · 空表跳过
              {{ excelPreview.will_skip_empty.length }}
            </p>
            <el-table :data="excelPreview.sheets" size="small" border style="margin-bottom: 12px">
              <el-table-column prop="label" label="报表" width="140" />
              <el-table-column prop="rows_with_code" label="科目行" width="90" />
              <el-table-column prop="non_null_fields" label="非空单元格" width="110" />
              <el-table-column label="期间">
                <template #default="{ row }">
                  {{ formatPeriodLabels(row.periods) }}
                </template>
              </el-table-column>
            </el-table>

            <el-collapse v-if="excelPreview.will_create.length || excelPreview.will_update.length">
              <el-collapse-item title="将写入的期间明细" name="1">
                <p v-if="excelPreview.will_create.length">
                  <strong>新建：</strong>{{ excelPreview.will_create.join('；') }}
                </p>
                <p v-if="excelPreview.will_update.length">
                  <strong>更新：</strong>{{ excelPreview.will_update.join('；') }}
                </p>
              </el-collapse-item>
            </el-collapse>

            <el-alert
              v-for="(w, i) in excelPreview.warnings.slice(0, 8)"
              :key="i"
              type="warning"
              :title="w"
              :closable="false"
              show-icon
              style="margin-top: 6px"
            />
            <p v-if="excelPreview.warnings.length > 8" class="sub">
              另有 {{ excelPreview.warnings.length - 8 }} 条警告…
            </p>

            <div class="actions">
              <el-button type="primary" :disabled="!excelFile" @click="onExcelCommit">
                确认入库
              </el-button>
              <el-button @click="goStatements">查看三大报表</el-button>
            </div>
          </div>

          <div v-if="excelResult" class="preview-block">
            <h3>入库结果</h3>
            <el-descriptions :column="1" border size="small">
              <el-descriptions-item label="新建">
                {{ excelResult.created.length }}：{{ excelResult.created.join('；') || '—' }}
              </el-descriptions-item>
              <el-descriptions-item label="更新">
                {{ excelResult.updated.length }}：{{ excelResult.updated.join('；') || '—' }}
              </el-descriptions-item>
              <el-descriptions-item label="跳过">
                {{ excelResult.skipped.length }}：{{ excelResult.skipped.join('；') || '—' }}
              </el-descriptions-item>
            </el-descriptions>
          </div>
        </div>
      </el-tab-pane>

      <el-tab-pane label="年报 PDF 导入" name="pdf">
        <el-steps :active="step" align-center finish-status="success" style="margin-bottom: 20px">
          <el-step title="上传 / 在线拉取" />
          <el-step title="识别与核对" />
          <el-step title="入库完成" />
        </el-steps>

        <div v-if="step === 0" class="panel">
          <el-upload
            drag
            :http-request="customUpload"
            :show-file-list="false"
            accept=".pdf,application/pdf"
          >
            <div class="upload-inner" v-loading="loading">
              <el-icon :size="48" color="#409eff"><Document /></el-icon>
              <div class="tip">拖拽或点击上传 A 股年报 PDF</div>
              <div class="sub">也可在「在线拉取」勾选下载后自动进入本页核对</div>
            </div>
          </el-upload>
        </div>

        <div v-else-if="step >= 1 && job" class="panel" v-loading="loading || batchCommitting">
          <div v-if="reviewJobs.length" class="review-nav">
            <el-button :disabled="reviewIndex <= 0" @click="goPrevReview">上一份</el-button>
            <div class="review-nav-center">
              <strong>
                {{ reviewIndex + 1 }} / {{ reviewTotal }}
                <template v-if="job.report_year"> · {{ job.report_year }} 年报</template>
              </strong>
              <div class="sub">
                已入库 {{ reviewCommittedCount }} · 待确认 {{ reviewPendingCount }}
                <template v-if="job.original_filename"> · {{ job.original_filename }}</template>
              </div>
              <div class="review-chips">
                <el-check-tag
                  v-for="(rj, i) in reviewJobs"
                  :key="rj.id"
                  :checked="i === reviewIndex"
                  class="review-chip"
                  @change="selectReviewIndex(i)"
                >
                  {{ rj.report_year || `#${rj.id}` }}
                  <span v-if="rj.status === 'committed'">✓</span>
                  <span v-else-if="rj.status === 'failed'">!</span>
                </el-check-tag>
              </div>
            </div>
            <el-button
              :disabled="reviewIndex >= reviewJobs.length - 1"
              @click="goNextReview"
            >
              下一份
            </el-button>
          </div>
          <el-alert
            :title="`状态：${job.status} · ${fillModeText}${
              overallCoveragePct !== null ? ` · 覆盖 ${overallCoveragePct}%` : ''
            }`"
            :type="
              job.status === 'failed'
                ? 'error'
                : job.status === 'committed'
                  ? 'success'
                  : overallCoveragePct !== null && overallCoveragePct < 50
                    ? 'warning'
                    : 'info'
            "
            :description="job.error_message || undefined"
            show-icon
            :closable="false"
            style="margin-bottom: 12px"
          />
          <el-form label-width="100px" class="meta-form" :inline="true">
            <el-form-item label="公司名">
              <el-input
                v-model="job.company_hint"
                style="width: 220px"
                :disabled="job.status === 'committed'"
              />
            </el-form-item>
            <el-form-item label="年份">
              <el-input-number
                v-model="job.report_year"
                :min="1990"
                :max="2100"
                :disabled="job.status === 'committed'"
              />
            </el-form-item>
            <el-form-item label="期间">
              <el-select
                v-model="job.period_type"
                style="width: 120px"
                :disabled="job.status === 'committed'"
              >
                <el-option label="年报" value="annual" />
                <el-option label="季报" value="quarterly" />
              </el-select>
            </el-form-item>
            <el-form-item v-if="job.period_type === 'quarterly'" label="季度">
              <el-input-number
                v-model="job.quarter"
                :min="1"
                :max="4"
                :disabled="job.status === 'committed'"
              />
            </el-form-item>
          </el-form>

          <div class="review-quality">
            <div class="review-quality-head">
              <h4>映射质量</h4>
              <el-tag
                v-if="overallCoveragePct !== null"
                :type="coverageTagType(overallCoveragePct)"
                effect="dark"
              >
                核心科目覆盖 {{ overallCoveragePct }}%
              </el-tag>
              <el-tag v-if="job.confidence != null" type="info" effect="plain">
                置信度 {{ (Number(job.confidence) * 100).toFixed(0) }}%
              </el-tag>
              <el-tag v-if="unmappedRows.length" type="warning" effect="plain">
                未映射 {{ unmappedRows.length }}
              </el-tag>
              <el-tag v-if="issueList.length" type="danger" effect="plain">
                问题 {{ issueList.length }}
              </el-tag>
            </div>

            <el-table :data="coverageRows" size="small" border class="coverage-table">
              <el-table-column prop="label" label="报表" min-width="120" />
              <el-table-column label="核心科目" width="110" align="center">
                <template #default="{ row }">
                  {{ row.coreHit }} / {{ row.coreTotal || '—' }}
                </template>
              </el-table-column>
              <el-table-column label="已映射字段" prop="mappedFields" width="100" align="center" />
              <el-table-column label="覆盖率" min-width="180">
                <template #default="{ row }">
                  <div class="cov-bar-wrap">
                    <el-progress
                      :percentage="row.pct"
                      :stroke-width="12"
                      :status="
                        row.pct >= 80 ? 'success' : row.pct >= 50 ? 'warning' : row.coreTotal ? 'exception' : undefined
                      "
                      :text-inside="true"
                    />
                  </div>
                </template>
              </el-table-column>
            </el-table>

            <el-alert
              v-for="(iss, i) in issueList.slice(0, 12)"
              :key="'iss-' + i"
              type="warning"
              :title="iss"
              show-icon
              :closable="false"
              class="issue-alert"
            />
            <p v-if="issueList.length > 12" class="sub">另有 {{ issueList.length - 12 }} 条问题…</p>

            <div v-if="unmappedRows.length" class="unmapped-block">
              <div class="unmapped-head">
                <h4>未映射科目（{{ unmappedRows.length }}）</h4>
                <el-radio-group v-model="unmappedFilterKind" size="small">
                  <el-radio-button value="all">
                    全部 {{ unmappedCountByKind.all }}
                  </el-radio-button>
                  <el-radio-button
                    v-for="k in kinds"
                    :key="k"
                    :value="k"
                    :disabled="!unmappedCountByKind[k]"
                  >
                    {{ kindLabel[k] }} {{ unmappedCountByKind[k] || 0 }}
                  </el-radio-button>
                </el-radio-group>
              </div>
              <p class="sub unmapped-hint">
                未映射行不会写入标准科目；可核对金额是否已由其他科目覆盖，或入库后在报表页手工补录。
              </p>
              <el-table
                :data="filteredUnmapped"
                size="small"
                border
                max-height="280"
                empty-text="该表无未映射行"
              >
                <el-table-column label="报表" width="110">
                  <template #default="{ row }">{{ statementLabel(row.statement) }}</template>
                </el-table-column>
                <el-table-column prop="label" label="原文科目" min-width="180" show-overflow-tooltip />
                <el-table-column label="金额" width="140" align="right">
                  <template #default="{ row }">{{ formatMoney(row.amount) }}</template>
                </el-table-column>
                <el-table-column label="页" prop="page" width="64" align="center" />
                <el-table-column label="原因" width="120">
                  <template #default="{ row }">
                    <el-tag size="small" type="info" effect="plain">{{ reasonLabel(row.reason) }}</el-tag>
                  </template>
                </el-table-column>
              </el-table>
            </div>
            <el-empty
              v-else-if="job.status !== 'failed'"
              description="无未映射科目"
              :image-size="56"
              class="unmapped-empty"
            />
          </div>

          <div v-for="k in kinds" :key="k" class="issues">
            <h4>{{ kindLabel[k] }}</h4>
            <el-table
              :data="Object.entries(statements[k] || {}).map(([key, val]) => ({ key, val }))"
              size="small"
              max-height="220"
              border
            >
              <el-table-column label="科目" min-width="160">
                <template #default="{ row }">{{ fieldLabel(k, row.key) }}</template>
              </el-table-column>
              <el-table-column label="代码" prop="key" width="180" />
              <el-table-column label="金额" width="140" align="right">
                <template #default="{ row }">{{ formatMoney(row.val) }}</template>
              </el-table-column>
            </el-table>
          </div>

          <div class="actions">
            <el-button
              @click="saveMeta()"
              :loading="loading"
              :disabled="job.status === 'committed'"
            >
              保存修改
            </el-button>
            <el-button
              type="primary"
              :loading="committing"
              :disabled="job.status === 'committed' || job.status === 'failed'"
              @click="handleCommit"
            >
              确认本份入库
            </el-button>
            <el-button
              v-if="reviewJobs.length"
              type="success"
              :loading="batchCommitting"
              :disabled="reviewPendingCount === 0"
              @click="handleBatchCommit"
            >
              批量确认入库（{{ reviewPendingCount }}）
            </el-button>
            <el-button
              v-if="job.status === 'committed' || reviewCommittedCount > 0"
              type="success"
              plain
              @click="goStatements"
            >
              查看三大报表
            </el-button>
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<style scoped>
.import-page {
  background: #fff;
  padding: 16px;
  border-radius: 6px;
}
.panel {
  max-width: 1100px;
  margin: 0 auto;
}
.upload-inner {
  padding: 40px 16px;
  color: #606266;
}
.tip {
  margin-top: 12px;
  font-size: 16px;
}
.sub {
  margin-top: 8px;
  font-size: 12px;
  color: #909399;
}
.meta-form {
  margin-bottom: 8px;
}
.excel-form {
  margin-bottom: 8px;
}
.issues {
  margin-bottom: 12px;
}
.preview-block {
  margin-top: 20px;
}
.preview-block h3 {
  margin: 0 0 8px;
  font-size: 16px;
}
.review-nav {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  padding: 12px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  background: #fafcff;
}
.review-nav-center {
  flex: 1;
  text-align: center;
}
.review-chips {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 6px;
  margin-top: 8px;
}
.review-chip {
  cursor: pointer;
}
.review-quality {
  margin: 8px 0 16px;
  padding: 12px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  background: var(--el-fill-color-blank);
}
.review-quality-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}
.review-quality-head h4 {
  margin: 0;
  font-size: 14px;
  margin-right: 4px;
}
.coverage-table {
  margin-bottom: 10px;
}
.cov-bar-wrap {
  padding-right: 4px;
}
.issue-alert {
  margin-bottom: 6px;
}
.unmapped-block {
  margin-top: 10px;
}
.unmapped-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 4px;
}
.unmapped-head h4 {
  margin: 0;
  font-size: 14px;
}
.unmapped-hint {
  margin: 0 0 8px;
}
.unmapped-empty {
  padding: 8px 0 0;
}
.actions {
  margin-top: 16px;
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}
.fetch-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
}
.fetch-card {
  border-radius: 8px;
}
.candidate-block {
  margin-top: 16px;
}
.batch-label {
  color: var(--el-text-color-regular);
  font-size: 13px;
  white-space: nowrap;
}
.batch-sep {
  color: var(--el-text-color-secondary);
}
.batch-results {
  margin-top: 16px;
}
.batch-summary {
  font-size: 13px;
  color: var(--el-text-color-regular);
}
</style>
