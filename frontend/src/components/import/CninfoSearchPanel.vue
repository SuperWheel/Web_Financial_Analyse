<script setup lang="ts">
import { computed, nextTick, ref } from 'vue'
import { ElMessage, type TableInstance } from 'element-plus'
import type { Company } from '@/api/company'
import {
  type ImportJob,
  fetchImportJob,
} from '@/api/importFiling'
import {
  downloadCninfoFiling,
  fetchFromUrl,
  searchCninfoAnnualYears,
  searchCninfoSecurities,
  type CninfoBatchYearResult,
  type FilingCandidate,
  type StockSecurity,
} from '@/api/fetchFiling'
import { useCompanyStore } from '@/stores/company'

const props = defineProps<{
  companies: Company[]
  companyId: number | null
}>()

const emit = defineEmits<{
  'update:companyId': [id: number | null]
  'review-jobs': [jobs: ImportJob[], opts?: { message?: string }]
}>()

const companyStore = useCompanyStore()

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

function matchLocalCompany(stock: StockSecurity) {
  const byCode = props.companies.find((c) => c.code && c.code === stock.code)
  if (byCode) {
    emit('update:companyId', byCode.id)
    return
  }
  if (stock.name) {
    const byName = props.companies.find((c) => c.name === stock.name)
    if (byName) emit('update:companyId', byName.id)
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
      pick = fetchSecurities.value.find((s) => s.code === q) || fetchSecurities.value[0]
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
    emit('update:companyId', created.id)
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
          company_id: props.companyId,
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
      jobs.sort((a, b) => (a.report_year || 0) - (b.report_year || 0))
      emit('review-jobs', jobs)
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
      company_id: props.companyId,
    })
    emit('review-jobs', [j])
  } catch {
    /* interceptor */
  } finally {
    fetchDownloading.value = false
  }
}

async function openBatchJob(jobId: number) {
  try {
    const j = await fetchImportJob(jobId)
    emit('review-jobs', [j])
  } catch {
    /* interceptor */
  }
}

function companyOptionLabel(c: {
  name: string
  code: string | null
  industry: string | null
}) {
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
</script>

<template>
  <div class="panel" v-loading="fetchLoading || fetchDownloading">
    <el-alert
      type="info"
      :closable="false"
      show-icon
      style="margin-bottom: 16px"
      title="年份填一个=单年，填 2022-2024 或 2022,2023,2024=多年。检索后勾选年报再导入；可新建关联企业（自动带代码/行业）。不自动入库。"
    />

    <el-form label-width="100px" class="meta-form">
      <el-form-item label="关联企业">
        <div class="fetch-row">
          <el-select
            :model-value="companyId"
            clearable
            filterable
            placeholder="可选，入库时绑定"
            style="width: 320px"
            @update:model-value="emit('update:companyId', $event)"
          >
            <el-option
              v-for="c in companies"
              :key="c.id"
              :label="companyOptionLabel(c)"
              :value="c.id"
            />
          </el-select>
          <el-button type="primary" plain @click="openCreateCompanyDialog"> 新建企业 </el-button>
          <span v-if="fetchSelected" class="sub">
            当前证券：{{ fetchSelected.code }}
            {{ fetchSelected.name || '' }}
            <template v-if="fetchSelected.industry"> · {{ fetchSelected.industry }} </template>
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
        <el-button type="primary" :loading="fetchLoading" @click="onSearchCninfo"> 检索 </el-button>
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
                  row.status === 'ok' ? 'success' : row.status === 'empty' ? 'info' : 'danger'
                "
              >
                {{
                  row.status === 'ok' ? '成功' : row.status === 'empty' ? '无全文' : '失败'
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

    <el-dialog v-model="createCompanyVisible" title="新建关联企业" width="420px" destroy-on-close>
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
</template>

<style scoped>
.panel {
  max-width: 1100px;
  margin: 0 auto;
}
.meta-form {
  margin-bottom: 8px;
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
.batch-results {
  margin-top: 16px;
}
.batch-summary {
  font-size: 13px;
  color: var(--el-text-color-regular);
}
.sub {
  margin-top: 8px;
  font-size: 12px;
  color: #909399;
}
</style>
