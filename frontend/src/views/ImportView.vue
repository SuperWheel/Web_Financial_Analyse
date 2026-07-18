<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Document } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox, type UploadRequestOptions } from 'element-plus'
import { storeToRefs } from 'pinia'
import {
  type ImportJob,
  commitImportJob,
  updateImportJob,
  uploadFiling,
} from '@/api/importFiling'
import { STATEMENT_META, type StatementKind } from '@/constants/statementFields'
import { useCompanyStore } from '@/stores/company'
import MappingQualityPanel from '@/components/import/MappingQualityPanel.vue'
import ReviewQueueNav from '@/components/import/ReviewQueueNav.vue'
import ExcelImportPanel from '@/components/import/ExcelImportPanel.vue'
import CninfoSearchPanel from '@/components/import/CninfoSearchPanel.vue'
import {
  STATEMENT_KINDS,
  STATEMENT_KIND_LABEL,
  formatMoney,
  overallCoveragePct as calcOverallCoveragePct,
} from '@/utils/importCoverage'

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

const kinds = STATEMENT_KINDS
const kindLabel = STATEMENT_KIND_LABEL

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

const overallCoveragePct = computed(() => calcOverallCoveragePct(job.value?.coverage))

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

// ---- 在线拉取关联企业（面板内状态见 CninfoSearchPanel）----
const fetchCompanyId = ref<number | null>(null)

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
}

async function goPrevReview() {
  if (reviewIndex.value <= 0) return
  await selectReviewIndex(reviewIndex.value - 1)
}

async function goNextReview() {
  if (reviewIndex.value >= reviewJobs.value.length - 1) return
  await selectReviewIndex(reviewIndex.value + 1)
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
        <CninfoSearchPanel
          v-model:company-id="fetchCompanyId"
          :companies="companies"
          @review-jobs="enterReviewQueue"
        />
      </el-tab-pane>

      <el-tab-pane label="Excel 模板导入" name="excel">
        <ExcelImportPanel :companies="companies" @go-statements="goStatements" />
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
          <ReviewQueueNav
            :jobs="reviewJobs"
            :index="reviewIndex"
            :current="job"
            :committed-count="reviewCommittedCount"
            :pending-count="reviewPendingCount"
            @prev="goPrevReview"
            @next="goNextReview"
            @select="selectReviewIndex"
          />
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

          <MappingQualityPanel :job="job" />

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
.issues {
  margin-bottom: 12px;
}
.actions {
  margin-top: 16px;
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}
</style>
