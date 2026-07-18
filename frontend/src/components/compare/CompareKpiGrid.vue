<script setup lang="ts">
import { formatPct } from '@/api/compare'
import { formatMoneySmart, type SummaryCard } from '@/composables/useStatementCompare'

defineProps<{
  cards: SummaryCard[]
  selectedKeys: string[]
  prevLabel: string
}>()

const emit = defineEmits<{
  toggle: [key: string]
}>()

</script>

<template>
  <div class="kpi-grid">
    <el-card
      v-for="card in cards"
      :key="card.key"
      shadow="hover"
      class="kpi-card"
      :class="{ active: selectedKeys.includes(card.key) }"
      @click="emit('toggle', card.key)"
    >
      <div class="kpi-label">{{ card.label }}</div>
      <div class="kpi-value-row">
        <span class="kpi-value">{{ formatMoneySmart(card.current).text }}</span>
        <span class="kpi-unit">{{ formatMoneySmart(card.current).unit }}</span>
      </div>
      <div class="kpi-sub">
        <template v-if="card.deltaPct !== null">
          <span :class="card.deltaPct > 0 ? 'cell-up' : card.deltaPct < 0 ? 'cell-down' : ''">
            较{{ prevLabel }} {{ formatPct(card.deltaPct) }}
          </span>
          <span class="muted">（{{ formatMoneySmart(card.deltaAbs).full }}）</span>
        </template>
        <template v-else>
          <span class="muted">单期无环比</span>
        </template>
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 8px;
}
.kpi-card {
  cursor: pointer;
  border-radius: 8px;
  transition: box-shadow 0.15s, border-color 0.15s;
}
.kpi-card :deep(.el-card__body) {
  padding: 10px 12px;
}
.kpi-card.active {
  border-color: #409eff;
  box-shadow: 0 0 0 1px #409eff inset;
}
.kpi-label {
  font-size: 12px;
  color: #909399;
  line-height: 1.2;
}
.kpi-value-row {
  display: flex;
  align-items: baseline;
  gap: 4px;
  margin-top: 4px;
}
.kpi-value {
  font-size: 20px;
  font-weight: 700;
  color: #303133;
  font-variant-numeric: tabular-nums;
  line-height: 1.15;
}
.kpi-unit {
  font-size: 12px;
  color: #909399;
  font-weight: 500;
}
.kpi-sub {
  margin-top: 4px;
  font-size: 12px;
  line-height: 1.3;
}
.muted {
  color: #c0c4cc;
  margin-left: 4px;
}
.cell-up {
  color: #067647;
}
.cell-down {
  color: #b42318;
}
</style>
