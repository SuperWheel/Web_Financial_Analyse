<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Document } from '@element-plus/icons-vue'
import { type UploadRequestOptions } from 'element-plus'
import { storeToRefs } from 'pinia'
import { uploadFiling } from '@/api/importFiling'
import { useCompanyStore } from '@/stores/company'
import MappingQualityPanel from '@/components/import/MappingQualityPanel.vue'
import ReviewQueueNav from '@/components/import/ReviewQueueNav.vue'
import ExcelImportPanel from '@/components/import/ExcelImportPanel.vue'
import CninfoSearchPanel from '@/components/import/CninfoSearchPanel.vue'
import StatementDraftTables from '@/components/import/StatementDraftTables.vue'
import { useImportReviewQueue } from '@/composables/useImportReviewQueue'

const router = useRouter()
const companyStore = useCompanyStore()
const { companies } = storeToRefs(companyStore)

const mainTab = ref<'fetch' | 'pdf' | 'excel'>('fetch')
const fetchCompanyId = ref<number | null>(null)

const {
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
} = useImportReviewQueue({ fetchCompanyId, mainTab })

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

function goStatements() {
  router.push('/statements')
}

onMounted(async () => {
  await companyStore.load()
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
              coveragePct !== null ? ` · 覆盖 ${coveragePct}%` : ''
            }`"
            :type="
              job.status === 'failed'
                ? 'error'
                : job.status === 'committed'
                  ? 'success'
                  : coveragePct !== null && coveragePct < 50
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
          <StatementDraftTables :statements="statements" />

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
.actions {
  margin-top: 16px;
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}
</style>
