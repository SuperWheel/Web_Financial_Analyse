<script setup lang="ts">
import VChart from 'vue-echarts'
import { TREND_TABS } from '@/utils/ratioInsights'
import type { TrendAxisMode, TrendValueMode } from '@/composables/useRatioAnalysis'
import type { RatioHistory } from '@/api/ratio'

const trendTab = defineModel<string>('trendTab', { required: true })
const selectedTrendKeys = defineModel<string[]>('selectedTrendKeys', { required: true })
const trendValueMode = defineModel<TrendValueMode>('trendValueMode', { required: true })
const trendAxisMode = defineModel<TrendAxisMode>('trendAxisMode', { required: true })
const trendAxisMin = defineModel<number | undefined>('trendAxisMin', { required: true })
const trendAxisMax = defineModel<number | undefined>('trendAxisMax', { required: true })
const trendRightMin = defineModel<number | undefined>('trendRightMin', { required: true })
const trendRightMax = defineModel<number | undefined>('trendRightMax', { required: true })

defineProps<{
  history: RatioHistory | null
  trendCandidateOptions: { key: string; label: string; unit: 'ratio' | 'percent' }[]
  chartAxisHint: string
  chartOption: Record<string, unknown>
}>()

const emit = defineEmits<{
  applyNiceScale: []
  resetAxisCustom: []
}>()
</script>

<template>
  <el-card class="chart-card" shadow="never">
    <template #header>
      <div class="chart-header">
        <span class="section-label inline">趋势分析</span>
        <div class="chart-controls">
          <el-radio-group v-model="trendTab" size="small">
            <el-radio-button
              v-for="t in TREND_TABS"
              :key="t.key"
              :value="t.key"
            >
              {{ t.label }}
            </el-radio-button>
          </el-radio-group>
        </div>
      </div>
      <div class="trend-select-row">
        <span class="trend-select-label">对比指标</span>
        <el-checkbox-group v-model="selectedTrendKeys" class="trend-checks">
          <el-checkbox
            v-for="opt in trendCandidateOptions"
            :key="opt.key"
            :value="opt.key"
            :label="opt.key"
          >
            {{ opt.label }}
            <el-text type="info" size="small">
              ({{ opt.unit === 'percent' ? '%' : '倍' }})
            </el-text>
          </el-checkbox>
        </el-checkbox-group>
      </div>
      <div class="axis-panel no-print">
        <div class="axis-row">
          <span class="axis-label">数值</span>
          <el-radio-group v-model="trendValueMode" size="small">
            <el-radio-button value="value">原始值</el-radio-button>
            <el-radio-button value="index">走势指数</el-radio-button>
          </el-radio-group>
          <span class="axis-label">Y 轴</span>
          <el-radio-group v-model="trendAxisMode" size="small">
            <el-radio-button value="auto">含 0</el-radio-button>
            <el-radio-button value="scale">自适应</el-radio-button>
            <el-radio-button value="log" :disabled="trendValueMode === 'index'">
              对数
            </el-radio-button>
            <el-radio-button value="custom">自定义</el-radio-button>
          </el-radio-group>
          <el-button size="small" @click="emit('applyNiceScale')">按所选填范围</el-button>
          <el-button size="small" text @click="emit('resetAxisCustom')">清空</el-button>
        </div>
        <div v-if="trendAxisMode === 'custom'" class="axis-row">
          <span class="axis-label">左轴</span>
          <el-input-number
            v-model="trendAxisMin"
            :controls="false"
            placeholder="min"
            class="axis-num"
          />
          <span>—</span>
          <el-input-number
            v-model="trendAxisMax"
            :controls="false"
            placeholder="max"
            class="axis-num"
          />
          <template v-if="trendValueMode === 'value'">
            <span class="axis-label" style="margin-left: 8px">右轴</span>
            <el-input-number
              v-model="trendRightMin"
              :controls="false"
              placeholder="min"
              class="axis-num"
            />
            <span>—</span>
            <el-input-number
              v-model="trendRightMax"
              :controls="false"
              placeholder="max"
              class="axis-num"
            />
          </template>
        </div>
        <div class="chart-hint">
          {{ chartAxisHint }}
          · 右侧滑条调 Y 轴；<kbd>Shift</kbd>+滚轮缩放 Y；底栏缩放时间。
        </div>
      </div>
    </template>
    <div
      v-if="history && (history.periods?.length || 0) > 0"
      class="chart-host trend-host"
    >
      <v-chart
        class="chart"
        :option="chartOption"
        :key="`trend-${trendTab}-${trendAxisMode}-${trendValueMode}-${selectedTrendKeys.join(',')}`"
        autoresize
      />
    </div>
    <el-empty v-else description="暂无多期数据，导入更多年度后可看趋势" :image-size="64" />
  </el-card>
</template>

<style scoped>
.chart-card {
  margin-top: 8px;
  border-radius: 8px;
}
.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}
.section-label.inline {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  margin: 0;
}
.chart-controls {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
  justify-content: flex-end;
}
.chart-hint {
  margin-top: 8px;
  font-size: 12px;
  color: #909399;
  font-weight: 400;
}
.trend-select-row {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  gap: 10px 16px;
  margin-top: 10px;
}
.trend-select-label {
  font-size: 13px;
  color: #606266;
  line-height: 32px;
  flex-shrink: 0;
}
.trend-checks {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 12px;
  align-items: center;
}
.chart-host {
  width: 100%;
  min-height: 200px;
  position: relative;
}
.chart-host.trend-host {
  height: 360px;
  min-height: 360px;
}
.chart-host .chart {
  width: 100% !important;
  height: 100% !important;
  min-height: inherit;
}
.chart {
  height: 360px;
  width: 100%;
}
.axis-panel {
  margin-top: 8px;
  padding: 8px 10px;
  background: #f8fafc;
  border: 1px solid #ebeef5;
  border-radius: 8px;
}
.axis-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}
.axis-row:last-child {
  margin-bottom: 0;
}
.axis-label {
  font-size: 12px;
  color: #606266;
  white-space: nowrap;
}
.axis-num {
  width: 100px;
}
.axis-panel kbd {
  display: inline-block;
  padding: 0 4px;
  border: 1px solid #dcdfe6;
  border-radius: 3px;
  background: #fff;
  font-size: 11px;
}
@media print {
  .no-print {
    display: none !important;
  }
  .chart-card {
    break-inside: avoid;
    box-shadow: none !important;
    border: 1px solid #ddd !important;
  }
  .chart {
    break-inside: avoid;
  }
}
</style>
