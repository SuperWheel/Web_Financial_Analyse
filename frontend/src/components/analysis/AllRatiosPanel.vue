<script setup lang="ts">
import { formatRatioValue, type RatioItem } from '@/api/ratio'
import { evaluateSignal } from '@/utils/ratioInsights'

const showAll = defineModel<boolean>('showAll', { required: true })

defineProps<{
  groupedRatios: { group: string; items: RatioItem[] }[]
  detailReason: (item: RatioItem) => string
}>()
</script>

<template>
  <div>
    <div class="all-toggle">
      <el-button text type="primary" @click="showAll = !showAll">
        {{ showAll ? '收起全部指标' : '展开全部指标与公式' }}
      </el-button>
    </div>
    <div v-show="showAll">
      <div v-for="block in groupedRatios" :key="block.group" class="group">
        <h3 class="group-title">{{ block.group }}</h3>
        <el-table :data="block.items" border stripe size="small" class="detail-table">
          <el-table-column prop="name" label="指标" min-width="120" />
          <el-table-column label="数值" width="110">
            <template #default="{ row }">
              <span :class="{ muted: row.value === null }">
                {{ formatRatioValue(row.value, row.unit) }}
              </span>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag
                :type="evaluateSignal(row.key, row.value).tagType"
                size="small"
                effect="plain"
              >
                {{ evaluateSignal(row.key, row.value).label }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="说明" min-width="200">
            <template #default="{ row }">
              <span class="table-desc">{{ detailReason(row) }}</span>
              <div v-if="row.variant" class="kpi-variant">{{ row.variant }}</div>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>
  </div>
</template>

<style scoped>
.all-toggle {
  text-align: center;
  padding: 8px 0 12px;
}
.group {
  background: #fff;
  padding: 12px 16px 16px;
  border-radius: 8px;
  margin-bottom: 12px;
}
.group-title {
  margin: 0 0 10px;
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}
.detail-table {
  width: 100%;
}
.table-desc {
  font-size: 12px;
  color: #909399;
}
.kpi-variant {
  margin-top: 4px;
  font-size: 11px;
  color: #a0aec0;
  line-height: 1.3;
  word-break: break-all;
}
.muted {
  color: #c0c4cc;
}
@media print {
  .group {
    break-inside: avoid;
    box-shadow: none !important;
    border: 1px solid #ddd !important;
  }
}
</style>
