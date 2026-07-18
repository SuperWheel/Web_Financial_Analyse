<script setup lang="ts">
import type { CompareMatrix } from '@/api/compare'
import type { MetricMode, TableRow } from '@/composables/useStatementCompare'

const tableFilter = defineModel<string>('tableFilter', { required: true })
const hideEmptyRows = defineModel<boolean>('hideEmptyRows', { required: true })

defineProps<{
  matrix: CompareMatrix
  tableRows: TableRow[]
  selectedKeys: string[]
  metricMode: MetricMode
  cellDisplay: (row: TableRow, idx: number) => string
  cellClass: (row: TableRow, idx: number) => string
  rowClassName: (args: { row: TableRow }) => string
}>()

const emit = defineEmits<{
  rowClick: [row: TableRow]
}>()
</script>


<template>
  <el-card shadow="never" class="table-card">
    <template #header>
      <div class="card-head">
        <span>科目对照表</span>
        <div class="table-tools">
          <el-input
            v-model="tableFilter"
            clearable
            size="small"
            placeholder="筛选科目"
            style="width: 160px"
          />
          <el-checkbox v-model="hideEmptyRows" size="small">隐藏全空行</el-checkbox>
          <span class="meta">
            {{ matrix.periods.length }} 期 ·
            {{
              metricMode === 'combo'
                ? '金额+环比'
                : metricMode === 'amount'
                  ? '金额'
                  : metricMode === 'structure'
                    ? '结构占比'
                    : '环比'
            }}
          </span>
        </div>
      </div>
    </template>

    <el-table
      :data="tableRows"
      border
      stripe
      size="small"
      height="520"
      :row-class-name="rowClassName"
      @row-click="(row: TableRow) => emit('rowClick', row)"
    >
      <el-table-column prop="label" label="科目" fixed min-width="200" show-overflow-tooltip>
        <template #default="{ row }">
          <strong v-if="row.isGroupHeader">{{ row.label }}</strong>
          <span v-else class="item-label">
            {{ row.label }}
            <el-tag
              v-if="selectedKeys.includes(row.key)"
              size="small"
              type="primary"
              effect="plain"
              style="margin-left: 6px"
            >
              趋势
            </el-tag>
          </span>
        </template>
      </el-table-column>
      <el-table-column
        v-for="(p, idx) in matrix.periods"
        :key="`${p.year}-${p.quarter ?? ''}-${idx}`"
        :label="p.label"
        min-width="140"
        align="right"
      >
        <template #default="{ row }">
          <span v-if="row.isGroupHeader" />
          <span v-else :class="cellClass(row, idx)">{{ cellDisplay(row, idx) }}</span>
        </template>
      </el-table-column>
    </el-table>
  </el-card>
</template>

<style scoped>
.table-card {
  border-radius: 8px;
}
.table-card :deep(.el-card__body) {
  padding: 12px;
}
.table-card :deep(.el-card__header) {
  padding: 10px 12px;
}
.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  flex-wrap: wrap;
}
.meta {
  color: #909399;
  font-size: 12px;
  font-weight: 400;
}
.table-tools {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.item-label {
  cursor: pointer;
}
.cell-up {
  color: #067647;
}
.cell-down {
  color: #b42318;
}
.cell-muted {
  color: #c0c4cc;
}
:deep(.group-header-row) {
  background: #f5f7fa !important;
  cursor: default;
}
:deep(.group-header-row td) {
  font-weight: 600;
}
:deep(.row-charted) {
  background: #ecf5ff !important;
}
:deep(.el-table__row) {
  cursor: pointer;
}
</style>
