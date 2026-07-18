<script setup lang="ts">
import VChart from 'vue-echarts'
import { formatRatioValue } from '@/api/ratio'

defineProps<{
  showRadar: boolean
  showDupont: boolean
  radarOption: Record<string, unknown>
  radarAxes: { key: string; name: string; score: number | null; detail: string }[]
  duPont: {
    roe: number | null
    netMargin: number | null
    assetTurnover: number | null
    equityMultiplier: number | null
    product: number | null
    gapPct: number | null
    note: string
  }
  duPontBarsOption: Record<string, unknown>
}>()
</script>

<template>
  <el-row
    v-if="showRadar || showDupont"
    :gutter="12"
    class="insight-row"
  >
    <el-col v-if="showRadar" :xs="24" :md="showDupont ? 12 : 24">
      <el-card shadow="never" class="insight-card">
        <template #header>
          <div class="insight-head">
            <span>能力雷达</span>
            <el-text type="info" size="small">沟通分 0–100，非精确估值</el-text>
          </div>
        </template>
        <v-chart
          v-if="Object.keys(radarOption).length"
          class="radar-chart"
          :option="radarOption"
          autoresize
        />
        <el-empty v-else description="数据不足，无法绘制雷达" :image-size="64" />
        <div class="radar-scores">
          <el-tag
            v-for="a in radarAxes"
            :key="a.key"
            class="radar-tag"
            effect="plain"
            type="info"
          >
            {{ a.name }} {{ a.score === null ? '—' : a.score }}
          </el-tag>
        </div>
      </el-card>
    </el-col>
    <el-col v-if="showDupont" :xs="24" :md="showRadar ? 12 : 24">
      <el-card shadow="never" class="insight-card">
        <template #header>
          <div class="insight-head">
            <span>杜邦拆解</span>
            <el-text type="info" size="small">ROE ≈ 净利率 × 周转 × 权益乘数</el-text>
          </div>
        </template>
        <div class="dupont-eq">
          ROE
          <strong>{{ formatRatioValue(duPont.roe, 'percent') }}</strong>
          ≈
          <strong>{{ formatRatioValue(duPont.netMargin, 'percent') }}</strong>
          ×
          <strong>{{ formatRatioValue(duPont.assetTurnover, 'ratio') }}</strong>
          ×
          <strong>{{ formatRatioValue(duPont.equityMultiplier, 'ratio') }}</strong>
        </div>
        <v-chart
          v-if="duPont.netMargin !== null"
          class="dupont-chart"
          :option="duPontBarsOption"
          autoresize
        />
        <el-empty v-else description="缺少拆解所需比率" :image-size="64" />
        <div class="dupont-note">{{ duPont.note }}</div>
        <div v-if="duPont.product !== null" class="dupont-note">
          三因子乘积 ≈ {{ formatRatioValue(duPont.product, 'percent') }}
          <template v-if="duPont.gapPct !== null">
            （与 ROE 偏差 {{ duPont.gapPct > 0 ? '+' : '' }}{{ duPont.gapPct.toFixed(1) }}%）
          </template>
        </div>
      </el-card>
    </el-col>
  </el-row>
</template>

<style scoped>
.insight-row {
  margin-bottom: 8px;
}
.insight-card {
  margin-bottom: 12px;
  border-radius: 8px;
  min-height: 360px;
}
.insight-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  font-weight: 600;
}
.radar-chart {
  height: 280px;
  width: 100%;
}
.radar-scores {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 4px;
}
.radar-tag {
  font-variant-numeric: tabular-nums;
}
.dupont-eq {
  font-size: 12px;
  color: #909399;
  margin-bottom: 8px;
  line-height: 1.6;
}
.dupont-eq strong {
  color: #303133;
  margin: 0 2px;
}
.dupont-chart {
  height: 160px;
  width: 100%;
}
.dupont-note {
  margin-top: 8px;
  font-size: 12px;
  color: #a0aec0;
  line-height: 1.4;
}
@media print {
  .insight-card {
    break-inside: avoid;
    box-shadow: none !important;
    border: 1px solid #ddd !important;
  }
  .radar-chart,
  .dupont-chart {
    break-inside: avoid;
  }
}
</style>
