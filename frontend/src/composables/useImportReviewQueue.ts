/** PDF 导入核对队列：软保存、单份/批量入库、多年切换 */
import { computed, ref, type Ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  type ImportJob,
  commitImportJob,
  updateImportJob,
} from '@/api/importFiling'
import { STATEMENT_KINDS, overallCoveragePct } from '@/utils/importCoverage'

export function useImportReviewQueue(opts: {
  fetchCompanyId: Ref<number | null>
  mainTab: Ref<'fetch' | 'pdf' | 'excel'>
}) {
  const step = ref(0)
  const loading = ref(false)
  const committing = ref(false)
  const batchCommitting = ref(false)
  const job = ref<ImportJob | null>(null)
  const reviewJobs = ref<ImportJob[]>([])
  const reviewIndex = ref(0)

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
      reviewJobs.value.filter((j) => j.status !== 'committed' && j.status !== 'failed').length
  )
  const coveragePct = computed(() => overallCoveragePct(job.value?.coverage))

  function syncCurrentIntoQueue() {
    if (!job.value || !reviewJobs.value.length) return
    const i = reviewJobs.value.findIndex((j) => j.id === job.value!.id)
    if (i >= 0) reviewJobs.value[i] = job.value
  }

  async function saveMeta(saveOpts?: { silent?: boolean }) {
    if (!job.value) return
    loading.value = true
    try {
      job.value = await updateImportJob(job.value.id, {
        company_id: opts.fetchCompanyId.value ?? job.value.company_id,
        company_hint: job.value.company_hint,
        report_year: job.value.report_year,
        period_type: job.value.period_type || 'annual',
        quarter: job.value.quarter,
        statements: statements.value as Record<string, Record<string, number | null>>,
      })
      syncCurrentIntoQueue()
      if (!saveOpts?.silent) ElMessage.success('已更新')
    } finally {
      loading.value = false
    }
  }

  async function enterReviewQueue(jobs: ImportJob[], queueOpts?: { message?: string }) {
    const list = jobs.filter(Boolean)
    if (!list.length) {
      ElMessage.warning('没有可核对的导入任务')
      return
    }
    const bound: ImportJob[] = []
    for (const j of list) {
      if (
        opts.fetchCompanyId.value &&
        j.company_id !== opts.fetchCompanyId.value &&
        j.status !== 'committed'
      ) {
        try {
          bound.push(await updateImportJob(j.id, { company_id: opts.fetchCompanyId.value }))
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
    opts.mainTab.value = 'pdf'
    const failed = bound.filter((j) => j.status === 'failed').length
    if (queueOpts?.message) {
      ElMessage.success(queueOpts.message)
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

  async function handleCommit() {
    if (!job.value) return
    if (!job.value.report_year) {
      ElMessage.warning('请先填写报告年份')
      return
    }
    if (coveragePct.value !== null && coveragePct.value < 50) {
      try {
        await ElMessageBox.confirm(
          `核心科目覆盖仅 ${coveragePct.value}%，仍可能有重要科目未识别。确认入库？`,
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
        company_id: opts.fetchCompanyId.value ?? job.value.company_id,
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
      for (const k of STATEMENT_KINDS) {
        const c = cov[k]
        if (!c) continue
        hit += Number(c.core_hit ?? 0)
        total += Number(c.core_total ?? 0)
      }
      if (!total) return false
      return hit / total < 0.5
    })
    if (lowCov.length) {
      const years = lowCov.map((j) => j.report_year || `#${j.id}`).join('、')
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
          const saved = await updateImportJob(j.id, {
            company_id: opts.fetchCompanyId.value ?? j.company_id,
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
            company_id: opts.fetchCompanyId.value ?? saved.company_id,
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

  return {
    step,
    loading,
    committing,
    batchCommitting,
    job,
    reviewJobs,
    reviewIndex,
    statements,
    fillModeText,
    reviewCommittedCount,
    reviewPendingCount,
    coveragePct,
    saveMeta,
    enterReviewQueue,
    selectReviewIndex,
    goPrevReview,
    goNextReview,
    handleCommit,
    handleBatchCommit,
  }
}
