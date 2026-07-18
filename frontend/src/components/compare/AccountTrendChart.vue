<script setup lang="ts">
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import {
  DataZoomComponent,
  GridComponent,
  LegendComponent,
  TitleComponent,
  TooltipComponent,
} from 'echarts/components'
import type { EChartsOption } from 'echarts'
import type { CompareMatrix } from '@/api/compare'
import type { AxisMode, ChartValueMode } from '@/composables/useStatementCompare'

use([
  CanvasRenderer,
  LineChart,
  GridComponent,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  DataZoomComponent,
])

const selectedKeys = defineModel<string[]>('selectedKeys', { required: true })
const chartValueMode = defineModel<ChartValueMode>('chartValueMode', { required: true })
const dualAxis = defineModel<boolean>('dualAxis', { required: true })
const axisMode = defineModel<AxisMode>('axisMode', { required: true })
const axisMin = defineModel<number | undefined>('axisMin', { required: true })
const axisMax = defineModel<number | undefined>('axisMax', { required: true })
const rightAxisMin = defineModel<number | undefined>('rightAxisMin', { required: true })
const rightAxisMax = defineModel<number | undefined>('rightAxisMax', { required: true })

defineProps<{
  matrix: CompareMatrix
  chartOption: EChartsOption
  remountKey: string
}>()

const emit = defineEmits<{
  applyNiceScale: []
  resetAxis: []
}>()

const showRightAxis = computed(
  () => dualAxis.value && chartValueMode.value === 'amount'
)
</script>

<template>
  <el-card shadow="never" class="chart-card">
    <template #header>
      <div class="card-head">
        <span>科目趋势</span>
        <el-select
          v-model="selectedKeys"
          multiple
          filterable
          collapse-tags
          collapse-tags-tooltip
          placeholder="选择科目"
          style="min-width: 260px; max-width: 420px"
        >
          <el-option-group v-for="g in matrix.groups" :key="g.key" :label="g.label">
            <el-option
              v-for="r in g.rows"
              :key="r.key"
              :label="r.label"
              :value="r.key"
            />
          </el-option-group>
        </el-select>
      </div>
    </template>

    <div class="axis-panel">
      <div class="axis-row">
        <span class="label">数值</span>
        <el-radio-group v-model="chartValueMode" size="small">
          <el-radio-button value="amount">原始金额</el-radio-button>
          <el-radio-button value="index">走势指数(首期=100)</el-radio-button>
        </el-radio-group>
        <el-checkbox v-model="dualAxis" :disabled="chartValueMode === 'index'">
          双 Y 轴（大小量级分离）
        </el-checkbox>
      </div>
      <div class="axis-row">
        <span class="label">坐标轴</span>
        <el-radio-group v-model="axisMode" size="small">
          <el-radio-button value="auto">自动含 0</el-radio-button>
          <el-radio-button value="scale">自适应缩放</el-radio-button>
          <el-radio-button value="log" :disabled="chartValueMode === 'index'">
            对数
          </el-radio-button>
          <el-radio-button value="custom">自定义</el-radio-button>
        </el-radio-group>
        <el-button size="small" @click="emit('applyNiceScale')">
          按所选填范围
        </el-button>
        <el-button size="small" text @click="emit('resetAxis')">清空范围</el-button>
      </div>
      <div v-if="axisMode === 'custom'" class="axis-row custom-range">
        <span class="label">左轴</span>
        <el-input-number
          v-model="axisMin"
          :controls="false"
          placeholder="min"
          class="axis-num"
        />
        <span>—</span>
        <el-input-number
          v-model="axisMax"
          :controls="false"
          placeholder="max"
          class="axis-num"
        />
        <template v-if="showRightAxis">
          <span class="label" style="margin-left: 12px">右轴</span>
          <el-input-number
            v-model="rightAxisMin"
            :controls="false"
            placeholder="min"
            class="axis-num"
          />
          <span>—</span>
          <el-input-number
            v-model="rightAxisMax"
            :controls="false"
            placeholder="max"
            class="axis-num"
          />
        </template>
      </div>
      <p class="axis-hint">
        <b>Y 轴调节：</b>右侧滑条拖动缩放/平移；按住
        <kbd>Shift</kbd> + 滚轮在图上缩放 Y 轴；底部滑条缩放时间轴。
        小数被压扁时开「双 Y 轴」或「走势指数」，也可用「自定义」填 min/max。
      </p>
    </div>

    <div class="chart-host">
      <v-chart
        class="chart"
        :option="chartOption"
        :key="remountKey"
        autoresize
      />
    </div>
  </el-card>
</template>

<style scoped>
.chart-card {
  border-radius: 8px;
}
.chart-card :deep(.el-card__body) {
  padding: 12px;
}
.chart-card :deep(.el-card__header) {
  padding: 10px 12px;
}
.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  flex-wrap: wrap;
}
.label {
  color: #606266;
  font-size: 13px;
  white-space: nowrap;
}
.axis-panel {
  background: #f8fafc;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 8px 10px;
  margin-bottom: 8px;
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
.axis-num {
  width: 110px;
}
.axis-hint {
  margin: 4px 0 0;
  font-size: 12px;
  color: #909399;
  line-height: 1.4;
}
.axis-hint kbd {
  display: inline-block;
  padding: 0 4px;
  border: 1px solid #dcdfe6;
  border-radius: 3px;
  background: #fff;
  font-size: 11px;
}
.chart-host {
  height: 340px;
  width: 100%;
}
.chart {
  height: 100%;
  width: 100%;
}
</style>
