<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { ImportJob, UnmappedRow } from '@/api/importFiling'
import type { StatementKind } from '@/constants/statementFields'
import {
  STATEMENT_KINDS,
  STATEMENT_KIND_LABEL,
  buildCoverageRows,
  coverageTagType,
  formatMoney,
  overallCoveragePct,
  statementKindLabel,
  unmappedReasonLabel,
} from '@/utils/importCoverage'

const props = defineProps<{
  job: ImportJob
}>()

const coverageRows = computed(() => buildCoverageRows(props.job.coverage))
const overallPct = computed(() => overallCoveragePct(props.job.coverage))
const issueList = computed(() => {
  const list = props.job.issues
  return Array.isArray(list) ? list.map(String).filter(Boolean) : []
})
const unmappedRows = computed((): UnmappedRow[] => {
  const list = props.job.unmapped
  return Array.isArray(list) ? list : []
})

const filterKind = ref<'all' | StatementKind>('all')

watch(
  () => props.job.id,
  () => {
    filterKind.value = 'all'
  }
)

const filteredUnmapped = computed(() => {
  const rows = unmappedRows.value
  if (filterKind.value === 'all') return rows
  return rows.filter((r) => r.statement === filterKind.value)
})

const unmappedCountByKind = computed(() => {
  const counts: Record<string, number> = { all: unmappedRows.value.length }
  for (const k of STATEMENT_KINDS) counts[k] = 0
  for (const r of unmappedRows.value) {
    const s = r.statement || ''
    if (s in counts) counts[s] += 1
  }
  return counts
})
</script>

<template>
  <div class="review-quality">
    <div class="review-quality-head">
      <h4>映射质量</h4>
      <el-tag
        v-if="overallPct !== null"
        :type="coverageTagType(overallPct)"
        effect="dark"
      >
        核心科目覆盖 {{ overallPct }}%
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
                row.pct >= 80
                  ? 'success'
                  : row.pct >= 50
                    ? 'warning'
                    : row.coreTotal
                      ? 'exception'
                      : undefined
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
        <el-radio-group v-model="filterKind" size="small">
          <el-radio-button value="all"> 全部 {{ unmappedCountByKind.all }} </el-radio-button>
          <el-radio-button
            v-for="k in STATEMENT_KINDS"
            :key="k"
            :value="k"
            :disabled="!unmappedCountByKind[k]"
          >
            {{ STATEMENT_KIND_LABEL[k] }} {{ unmappedCountByKind[k] || 0 }}
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
          <template #default="{ row }">{{ statementKindLabel(row.statement) }}</template>
        </el-table-column>
        <el-table-column prop="label" label="原文科目" min-width="180" show-overflow-tooltip />
        <el-table-column label="金额" width="140" align="right">
          <template #default="{ row }">{{ formatMoney(row.amount) }}</template>
        </el-table-column>
        <el-table-column label="页" prop="page" width="64" align="center" />
        <el-table-column label="原因" width="120">
          <template #default="{ row }">
            <el-tag size="small" type="info" effect="plain">{{
              unmappedReasonLabel(row.reason)
            }}</el-tag>
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
</template>

<style scoped>
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
.sub {
  margin-top: 8px;
  font-size: 12px;
  color: #909399;
}
</style>
