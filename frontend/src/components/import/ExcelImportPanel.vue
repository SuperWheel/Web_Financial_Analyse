<script setup lang="ts">
import { ref } from 'vue'
import { UploadFilled } from '@element-plus/icons-vue'
import { ElMessage, type UploadRequestOptions } from 'element-plus'
import type { Company } from '@/api/company'
import {
  commitExcelImport,
  downloadExcelTemplate,
  previewExcelImport,
  type ExcelImportPreview,
  type ExcelImportResult,
} from '@/api/excel'
import type { PeriodType } from '@/api/compare'
import { formatPeriodLabels } from '@/utils/importCoverage'

defineProps<{
  companies: Company[]
}>()

const emit = defineEmits<{
  'go-statements': []
}>()

const excelCompanyId = ref<number | null>(null)
const excelPeriodType = ref<PeriodType>('annual')
const templateYears = ref(
  `${new Date().getFullYear() - 2},${new Date().getFullYear() - 1},${new Date().getFullYear()}`
)
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
</script>

<template>
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
          <el-option v-for="c in companies" :key="c.id" :label="c.name" :value="c.id" />
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
        <el-button type="primary" plain style="margin-left: 12px" @click="onDownloadTemplate">
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
        <el-button @click="emit('go-statements')">查看三大报表</el-button>
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
</template>

<style scoped>
.panel {
  max-width: 1100px;
  margin: 0 auto;
}
.excel-form {
  margin-bottom: 8px;
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
</style>
