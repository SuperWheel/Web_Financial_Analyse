<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Document, UploadFilled } from '@element-plus/icons-vue'
import { ElMessage, type UploadRequestOptions } from 'element-plus'
import { storeToRefs } from 'pinia'
import {
  type ImportJob,
  commitImportJob,
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
  searchCninfoAnnual,
  searchCninfoSecurities,
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
const job = ref<ImportJob | null>(null)

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

function formatMoney(v: unknown): string {
  if (v === null || v === undefined || v === '') return '—'
  const n = Number(v)
  if (Number.isNaN(n)) return '—'
  return n.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
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
    job.value = await uploadFiling(file)
    step.value = 1
    if (job.value.status === 'failed') {
      ElMessage.warning(job.value.error_message || '解析失败')
    } else {
      ElMessage.success('识别完成，请核对结果')
    }
    opt.onSuccess?.(job.value)
  } catch (e) {
    opt.onError?.(e as Error)
  } finally {
    loading.value = false
  }
}

async function saveMeta() {
  if (!job.value) return
  loading.value = true
  try {
    job.value = await updateImportJob(job.value.id, {
      company_hint: job.value.company_hint,
      report_year: job.value.report_year,
      period_type: job.value.period_type || 'annual',
      quarter: job.value.quarter,
      statements: statements.value,
    })
    ElMessage.success('已更新')
  } finally {
    loading.value = false
  }
}

async function handleCommit() {
  if (!job.value) return
  if (!job.value.report_year) {
    ElMessage.warning('请先填写报告年份')
    return
  }
  committing.value = true
  try {
    await saveMeta()
    job.value = await commitImportJob(job.value.id, { overwrite: true })
    ElMessage.success('已入库')
    step.value = 2
  } finally {
    committing.value = false
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
    opt.onError?.(e as Error)
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
const fetchQuery = ref('科沃斯')
const fetchYear = ref(new Date().getFullYear() - 1)
const fetchUrl = ref('')
const fetchSecurities = ref<StockSecurity[]>([])
const fetchSelectedCode = ref<string | null>(null)
const fetchCandidates = ref<FilingCandidate[]>([])
const fetchLoading = ref(false)
const fetchDownloading = ref(false)

function openJobForReview(j: ImportJob) {
  job.value = j
  step.value = 1
  mainTab.value = 'pdf'
  if (j.status === 'failed') {
    ElMessage.warning(j.error_message || '解析失败，请检查 PDF')
  } else {
    ElMessage.success('已下载并解析，请在「年报 PDF」页核对后入库')
  }
}

async function loadAnnualForCode(code: string) {
  const requestedYear = fetchYear.value
  let rows = await searchCninfoAnnual(code, requestedYear)
  let usedYear = requestedYear
  // 默认年份无结果时，自动试上一年（年报多在次年披露，年份易点偏）
  if (!rows.length && requestedYear > 1990) {
    const prev = requestedYear - 1
    rows = await searchCninfoAnnual(code, prev)
    if (rows.length) {
      usedYear = prev
      fetchYear.value = prev
      ElMessage.info(`已自动改用 ${prev} 年（${requestedYear} 年无全文年报）`)
    }
  }
  fetchCandidates.value = rows
  if (!rows.length) {
    ElMessage.warning(
      `未找到 ${code} 在 ${requestedYear} 附近的「年度报告」全文。请确认是 A 股代码，或改年份后重试。`
    )
  } else {
    ElMessage.success(`找到 ${rows.length} 份 ${usedYear} 年年报候选`)
  }
}

/** 始终以当前输入解析证券；唯一命中则继续查年报 */
async function onSearchCninfo() {
  const q = fetchQuery.value.trim()
  if (!q) {
    ElMessage.warning('请填写证券代码或公司名称')
    return
  }
  fetchLoading.value = true
  fetchSecurities.value = []
  fetchCandidates.value = []
  fetchSelectedCode.value = null
  try {
    fetchSecurities.value = await searchCninfoSecurities(q)
    if (!fetchSecurities.value.length) {
      ElMessage.warning(`未找到证券：${q}（可试简称，如「科沃斯」「贵州茅台」）`)
      return
    }
    // 输入本身是 6 位代码时优先精确代码
    let pick = fetchSecurities.value[0]
    if (/^\d{6}$/.test(q)) {
      pick =
        fetchSecurities.value.find((s) => s.code === q) || fetchSecurities.value[0]
    }
    if (fetchSecurities.value.length === 1 || /^\d{6}$/.test(q)) {
      fetchSelectedCode.value = pick.code
      await loadAnnualForCode(pick.code)
    } else {
      ElMessage.success(
        `找到 ${fetchSecurities.value.length} 只证券，请点击「选此公司」查看年报`
      )
    }
  } catch {
    // http 拦截器已提示
  } finally {
    fetchLoading.value = false
  }
}

async function onPickSecurity(row: StockSecurity) {
  fetchSelectedCode.value = row.code
  fetchQuery.value = row.code
  fetchLoading.value = true
  fetchCandidates.value = []
  try {
    await loadAnnualForCode(row.code)
  } catch {
    // interceptor
  } finally {
    fetchLoading.value = false
  }
}

async function onDownloadCandidate(row: FilingCandidate) {
  fetchDownloading.value = true
  try {
    const j = await downloadCninfoFiling({
      pdf_url: row.pdf_url,
      code: row.code,
      title: row.title,
      year: row.year,
      name: row.name,
      company_id: fetchCompanyId.value,
    })
    openJobForReview(j)
  } catch {
    // interceptor
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
    // interceptor
  } finally {
    fetchDownloading.value = false
  }
}


onMounted(async () => {
  await companyStore.load()
  if (companies.value.length) {
    if (excelCompanyId.value == null) excelCompanyId.value = companies.value[0].id
    if (fetchCompanyId.value == null) fetchCompanyId.value = companies.value[0].id
  }
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
            title="支持证券代码或公司名称（全称会自动回退简称）。A 股走巨潮公开披露；下载后人工核对，不自动入库。请控制频率。"
          />
          <el-form label-width="100px" class="excel-form">
            <el-form-item label="关联企业">
              <el-select
                v-model="fetchCompanyId"
                clearable
                filterable
                placeholder="可选，入库时绑定"
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
          </el-form>
          <el-card shadow="never" class="fetch-card">
            <template #header><strong>巨潮 · 代码 / 公司名称 + 年份</strong></template>
            <div class="fetch-row">
              <el-input
                v-model="fetchQuery"
                placeholder="代码或名称，如 603486 / 科沃斯 / 贵州茅台酒股份有限公司"
                clearable
                style="min-width: 280px; flex: 1"
                @keyup.enter="onSearchCninfo"
              />
              <el-input-number v-model="fetchYear" :min="1990" :max="2100" />
              <el-button type="primary" :loading="fetchLoading" @click="onSearchCninfo">
                检索年报
              </el-button>
            </div>

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
              <el-table-column prop="category" label="类型" width="100" />
              <el-table-column label="操作" width="120" fixed="right">
                <template #default="{ row }">
                  <el-button type="primary" link @click.stop="onPickSecurity(row)">
                    {{ fetchSelectedCode === row.code ? '已选·查年报' : '选此公司' }}
                  </el-button>
                </template>
              </el-table-column>
            </el-table>

            <el-table
              v-if="fetchCandidates.length"
              :data="fetchCandidates"
              size="small"
              border
              style="margin-top: 12px"
            >
              <el-table-column prop="code" label="代码" width="90" />
              <el-table-column prop="name" label="简称" width="100" />
              <el-table-column prop="title" label="标题" min-width="220" show-overflow-tooltip />
              <el-table-column prop="announce_date" label="公告日" width="120" />
              <el-table-column label="操作" width="120" fixed="right">
                <template #default="{ row }">
                  <el-button
                    type="primary"
                    link
                    :loading="fetchDownloading"
                    @click="onDownloadCandidate(row)"
                  >
                    下载解析
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
            <p v-else class="sub" style="margin-top: 12px">
              先匹配证券（名称支持全称），再列出该年「年度报告」全文（自动排除摘要/英文）。
            </p>
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
                  {{ row.periods.map((p: { label: string }) => p.label).join('、') }}
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
          <el-step title="上传年报 PDF" />
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
              <div class="sub">解析后请人工核对科目映射再入库</div>
            </div>
          </el-upload>
        </div>

        <div v-else-if="step >= 1 && job" class="panel" v-loading="loading">
          <el-alert
            :title="`状态：${job.status} · ${fillModeText}`"
            :type="job.status === 'failed' ? 'error' : 'success'"
            show-icon
            :closable="false"
            style="margin-bottom: 12px"
          />
          <el-form label-width="100px" class="meta-form" :inline="true">
            <el-form-item label="公司名">
              <el-input v-model="job.company_hint" style="width: 220px" />
            </el-form-item>
            <el-form-item label="年份">
              <el-input-number v-model="job.report_year" :min="1990" :max="2100" />
            </el-form-item>
            <el-form-item label="期间">
              <el-select v-model="job.period_type" style="width: 120px">
                <el-option label="年报" value="annual" />
                <el-option label="季报" value="quarterly" />
              </el-select>
            </el-form-item>
            <el-form-item v-if="job.period_type === 'quarterly'" label="季度">
              <el-input-number v-model="job.quarter" :min="1" :max="4" />
            </el-form-item>
          </el-form>

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
            <el-button @click="saveMeta" :loading="loading">保存修改</el-button>
            <el-button
              type="primary"
              :loading="committing"
              :disabled="step >= 2"
              @click="handleCommit"
            >
              确认入库
            </el-button>
            <el-button v-if="step >= 2" type="success" plain @click="goStatements">
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
</style>
