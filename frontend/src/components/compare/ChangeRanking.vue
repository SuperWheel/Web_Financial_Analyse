<script setup lang="ts">
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart } from 'echarts/charts'
import {
  GridComponent,
  TitleComponent,
  TooltipComponent,
} from 'echarts/components'
import type { EChartsOption } from 'echarts'
import { formatPct } from '@/api/compare'
import type { MoverItem } from '@/composables/useStatementCompare'

use([CanvasRenderer, BarChart, GridComponent, TitleComponent, TooltipComponent])

defineProps<{
  movers: { up: MoverItem[]; down: MoverItem[] }
  moverBarOption: EChartsOption
  prevLabel: string
  latestLabel: string
}>()

const emit = defineEmits<{
  toggle: [key: string]
}>()
</script>

<template>
  <el-card shadow="never" class="mover-card">
    <template #header>
      <div class="card-head">
        <span>最近一期变动榜</span>
        <span class="meta">{{ prevLabel }} → {{ latestLabel }}</span>
      </div>
    </template>
    <div class="mover-chart-host">
      <v-chart class="chart" :option="moverBarOption" autoresize />
    </div>
    <div class="mover-lists">
      <div>
        <div class="mover-title up">增长 Top</div>
        <div
          v-for="m in movers.up"
          :key="m.key"
          class="mover-item"
          @click="emit('toggle', m.key)"
        >
          <span>{{ m.label }}</span>
          <span class="cell-up">{{ formatPct(m.pct) }}</span>
        </div>
        <el-empty v-if="!movers.up.length" :image-size="48" description="无" />
      </div>
      <div>
        <div class="mover-title down">下降 Top</div>
        <div
          v-for="m in movers.down"
          :key="m.key"
          class="mover-item"
          @click="emit('toggle', m.key)"
        >
          <span>{{ m.label }}</span>
          <span class="cell-down">{{ formatPct(m.pct) }}</span>
        </div>
        <el-empty v-if="!movers.down.length" :image-size="48" description="无" />
      </div>
    </div>
  </el-card>
</template>

<style scoped>
.mover-card {
  border-radius: 8px;
}
.mover-card :deep(.el-card__body) {
  padding: 12px;
}
.mover-card :deep(.el-card__header) {
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
.mover-chart-host {
  height: 200px;
  width: 100%;
}
.chart {
  height: 100%;
  width: 100%;
}
.mover-lists {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin-top: 6px;
}
.mover-title {
  font-size: 12px;
  font-weight: 600;
  margin-bottom: 4px;
}
.mover-title.up {
  color: #067647;
}
.mover-title.down {
  color: #b42318;
}
.mover-item {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  font-size: 12px;
  padding: 3px 0;
  cursor: pointer;
  border-bottom: 1px dashed #f0f0f0;
}
.mover-item:hover {
  color: #409eff;
}
.cell-up {
  color: #067647;
}
.cell-down {
  color: #b42318;
}
</style>
