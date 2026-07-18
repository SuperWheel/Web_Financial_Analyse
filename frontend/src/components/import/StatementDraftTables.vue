<script setup lang="ts">
import { STATEMENT_KINDS, STATEMENT_KIND_LABEL, formatMoney } from '@/utils/importCoverage'
import { STATEMENT_META, type StatementKind } from '@/constants/statementFields'

defineProps<{
  statements: Record<string, Record<string, number | null | undefined>>
}>()

function fieldLabel(kind: StatementKind, key: string): string {
  for (const g of STATEMENT_META[kind].groups) {
    const f = g.fields.find((x) => x.key === key)
    if (f) return f.label
  }
  return key
}

function rowsOf(
  statements: Record<string, Record<string, number | null | undefined>>,
  kind: StatementKind
) {
  return Object.entries(statements[kind] || {}).map(([key, val]) => ({ key, val }))
}
</script>

<template>
  <div v-for="k in STATEMENT_KINDS" :key="k" class="issues">
    <h4>{{ STATEMENT_KIND_LABEL[k] }}</h4>
    <el-table :data="rowsOf(statements, k)" size="small" max-height="220" border>
      <el-table-column label="科目" min-width="160">
        <template #default="{ row }">{{ fieldLabel(k, row.key) }}</template>
      </el-table-column>
      <el-table-column label="代码" prop="key" width="180" />
      <el-table-column label="金额" width="140" align="right">
        <template #default="{ row }">{{ formatMoney(row.val) }}</template>
      </el-table-column>
    </el-table>
  </div>
</template>

<style scoped>
.issues {
  margin-bottom: 12px;
}
.issues h4 {
  margin: 0 0 8px;
  font-size: 14px;
}
</style>
