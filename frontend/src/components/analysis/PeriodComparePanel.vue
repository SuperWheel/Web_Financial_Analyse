<script setup lang="ts">
import VChart from 'vue-echarts'
import { formatRatioValue } from '@/api/ratio'
import type { PeriodCompareRow } from '@/utils/ratioInsights'

export type MoverCard = PeriodCompareRow & { barPct: number }

defineProps<{
  periodKey: string
  viewerRole: string
  periodCompare: {
    hasPrevious: boolean
    previousLabel: string
    currentLabel: string
    counts: { improve: number; watch: number; flat: number }
    rows: PeriodCompareRow[]
    rowsByMagnitude: PeriodCompareRow[]
  }
  movers: { improved: MoverCard[]; watch: MoverCard[] }
  highlightedKey: string | null
  showCompareTable: boolean
  structureDonutOption: Record<string, unknown>
  divergingChangeOption: Record<string, unknown>
  periodPairOption: Record<string, unknown>
  divergingChartHeight: number
  yoyClass: (improved: boolean | null, direction: string) => string
  yoyArrow: (direction: string) => string
  meaningClass: (meaning: string) => string
  compareRowClassName: (args: { row: PeriodCompareRow }) => string
}>()

const emit = defineEmits<{
  focus: [key: string]
  'update:showCompareTable': [value: boolean]
  divergingClick: [params: { name?: string }]
  pairClick: [params: { name?: string }]
  rowClick: [row: PeriodCompareRow]
}>()

function onDivergingChartClick(params: { name?: string }) {
  emit('divergingClick', params)
}

function onPairChartClick(params: { name?: string }) {
  emit('pairClick', params)
}
</script>

<template>
  <el-card class="compare-card" shadow="never">
    <template #header>
      <div class="compare-head">
        <span>较上期变动</span>
        <el-text type="info" size="small">
          {{
            periodCompare.hasPrevious
              ? `${periodCompare.previousLabel} → ${periodCompare.currentLabel}`
              : '至少需要两个报告期才有对比'
          }}
        </el-text>
      </div>
    </template>

    <el-empty
      v-if="!periodCompare.hasPrevious"
      description="当前仅有一期数据，导入/录入更多年度后可看变动"
      :image-size="64"
    />

    <template v-else>
      <!-- 模块 A：结构 + 重点（紧凑网格，避免空白与溢出） -->
      <div class="compare-top-grid">
        <div class="module-panel structure-panel">
          <div class="module-title">变动结构</div>
          <div class="module-sub">悬停扇区可看具体指标与变动</div>
          <div class="structure-body">
            <v-chart
              v-if="Object.keys(structureDonutOption).length"
              class="structure-chart"
              :option="structureDonutOption"
              autoresize
            />
            <div class="structure-stats">
              <div class="stat-chip improve">
                <span class="stat-num">{{ periodCompare.counts.improve }}</span>
                <span class="stat-label">改善</span>
              </div>
              <div class="stat-chip watch">
                <span class="stat-num">{{ periodCompare.counts.watch }}</span>
                <span class="stat-label">需关注</span>
              </div>
              <div class="stat-chip flat">
                <span class="stat-num">{{ periodCompare.counts.flat }}</span>
                <span class="stat-label">持平</span>
              </div>
            </div>
          </div>
        </div>

        <div class="module-panel focus-panel">
          <div class="module-title">重点变动</div>
          <div class="module-sub">点卡高亮上方 KPI · 哑铃=上期→本期</div>
          <div class="focus-grid visual">
            <div class="focus-col">
              <div class="focus-col-title improve">改善 Top</div>
              <div v-if="!movers.improved.length" class="focus-empty">暂无改善项</div>
              <div
                v-for="m in movers.improved"
                :key="'i-' + m.key"
                class="focus-card improve"
                :class="{ active: highlightedKey === m.key }"
                @click="emit('focus', m.key)"
              >
                <div class="focus-card-top">
                  <span class="focus-name">{{ m.name }}</span>
                  <span class="focus-badge improve">{{ m.yoy.deltaDisplay }}</span>
                </div>
                <div class="dumbbell">
                  <span class="dumbbell-val prev">{{ formatRatioValue(m.previous, m.unit) }}</span>
                  <div class="dumbbell-track">
                    <div class="dumbbell-line improve" />
                    <span class="dumbbell-dot prev" />
                    <span class="dumbbell-dot curr improve" />
                  </div>
                  <span class="dumbbell-val curr">{{ formatRatioValue(m.current, m.unit) }}</span>
                </div>
                <div class="focus-bar-track">
                  <div class="focus-bar-fill improve" :style="{ width: m.barPct + '%' }" />
                </div>
                <div class="focus-level">
                  <el-tag :type="m.signal.tagType" size="small" effect="plain">{{ m.signal.label }}</el-tag>
                </div>
              </div>
            </div>

            <div class="focus-col">
              <div class="focus-col-title watch">需关注 Top</div>
              <div v-if="!movers.watch.length" class="focus-empty">暂无需关注项</div>
              <div
                v-for="m in movers.watch"
                :key="'w-' + m.key"
                class="focus-card watch"
                :class="{ active: highlightedKey === m.key }"
                @click="emit('focus', m.key)"
              >
                <div class="focus-card-top">
                  <span class="focus-name">{{ m.name }}</span>
                  <span class="focus-badge watch">{{ m.yoy.deltaDisplay }}</span>
                </div>
                <div class="dumbbell">
                  <span class="dumbbell-val prev">{{ formatRatioValue(m.previous, m.unit) }}</span>
                  <div class="dumbbell-track">
                    <div class="dumbbell-line watch" />
                    <span class="dumbbell-dot prev" />
                    <span class="dumbbell-dot curr watch" />
                  </div>
                  <span class="dumbbell-val curr">{{ formatRatioValue(m.current, m.unit) }}</span>
                </div>
                <div class="focus-bar-track">
                  <div class="focus-bar-fill watch" :style="{ width: m.barPct + '%' }" />
                </div>
                <div class="focus-level">
                  <el-tag :type="m.signal.tagType" size="small" effect="plain">{{ m.signal.label }}</el-tag>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 模块 B：语义双向条 -->
      <div class="module-panel chart-module">
        <div class="module-title-row">
          <div>
            <div class="module-title">变动幅度（业务语义）</div>
            <div class="module-sub">右=改善 · 左=需关注 · 长度=幅度（% 为百分点，倍数为绝对差）</div>
          </div>
          <div class="axis-legend">
            <span class="axis-chip watch">← 需关注</span>
            <span class="axis-chip improve">改善 →</span>
          </div>
        </div>
        <div
          v-if="Object.keys(divergingChangeOption).length"
          class="chart-host"
          :style="{ height: divergingChartHeight + 'px' }"
        >
          <v-chart
            :key="'div-' + periodKey + '-' + viewerRole"
            class="diverging-chart"
            :option="divergingChangeOption"
            autoresize
            @click="onDivergingChartClick"
          />
        </div>
        <el-empty v-else description="各指标较上期持平或无可比变动" :image-size="56" />
      </div>

      <!-- 模块 C：上期 vs 本期 对照柱 -->
      <div class="module-panel chart-module">
        <div class="module-title">上期 vs 本期对照</div>
        <div class="module-sub">灰蓝=上期 · 亮蓝=本期 · 悬停看完整变动（% 与倍数量纲不同）</div>
        <div
          v-if="Object.keys(periodPairOption).length"
          class="chart-host pair-host"
        >
          <v-chart
            :key="'pair-' + periodKey + '-' + viewerRole"
            class="pair-chart"
            :option="periodPairOption"
            autoresize
            @click="onPairChartClick"
          />
        </div>
      </div>

      <!-- 明细表：默认折叠 -->
      <div class="compare-table-toggle">
        <el-button text type="primary" @click="emit('update:showCompareTable', !showCompareTable)">
          {{ showCompareTable ? '收起数值明细表' : '展开数值明细表' }}
        </el-button>
      </div>
      <el-table
        v-show="showCompareTable"
        :data="periodCompare.rowsByMagnitude"
        size="small"
        border
        stripe
        class="compare-table"
        :row-class-name="compareRowClassName"
        @row-click="(row: PeriodCompareRow) => emit('rowClick', row)"
      >
        <el-table-column prop="name" label="指标" min-width="110" />
        <el-table-column :label="periodCompare.previousLabel || '上期'" width="100">
          <template #default="{ row }">
            {{ formatRatioValue(row.previous, row.unit) }}
          </template>
        </el-table-column>
        <el-table-column :label="periodCompare.currentLabel || '本期'" width="100">
          <template #default="{ row }">
            <strong>{{ formatRatioValue(row.current, row.unit) }}</strong>
          </template>
        </el-table-column>
        <el-table-column label="变动" min-width="140">
          <template #default="{ row }">
            <div class="table-change">
              <span :class="yoyClass(row.yoy.improved, row.yoy.direction)">
                {{ yoyArrow(row.yoy.direction) }} {{ row.yoy.deltaDisplay }}
              </span>
              <span v-if="row.yoy.relChangeDisplay" class="kpi-rel">
                ({{ row.yoy.relChangeDisplay }})
              </span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="业务含义" width="90">
          <template #default="{ row }">
            <span :class="meaningClass(row.yoy.meaning)">{{ row.yoy.meaningLabel }}</span>
          </template>
        </el-table-column>
        <el-table-column label="水平" width="90">
          <template #default="{ row }">
            <el-tag :type="row.signal.tagType" size="small" effect="plain">{{ row.signal.label }}</el-tag>
          </template>
        </el-table-column>
      </el-table>
    </template>
  </el-card>
</template>

<style scoped>
.compare-card {
  margin: 8px 0 12px;
  border-radius: 8px;
  overflow: visible;
}
.compare-card :deep(.el-card__body) {
  overflow: visible;
}
.compare-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  font-weight: 600;
}
.compare-top-grid {
  display: grid;
  grid-template-columns: minmax(280px, 1.05fr) minmax(0, 1.5fr);
  gap: 12px;
  align-items: stretch;
  margin-bottom: 12px;
}
@media (max-width: 992px) {
  .compare-top-grid {
    grid-template-columns: 1fr;
  }
}
.module-panel {
  background: #fafbfc;
  border: 1px solid #ebeef5;
  border-radius: 10px;
  padding: 12px 14px 14px;
  margin-bottom: 12px;
  display: flex;
  flex-direction: column;
  min-height: 0;
  box-sizing: border-box;
}
.compare-top-grid > .module-panel {
  margin-bottom: 0;
  height: 100%;
}
.module-panel.chart-module {
  background: #fff;
  position: relative;
  z-index: 1;
  /* 切勿 overflow:hidden —— 会让 echarts canvas 高度塌成 0 */
  overflow: visible;
}
.chart-host {
  width: 100%;
  min-height: 200px;
  position: relative;
}
.chart-host.pair-host {
  height: 320px;
  min-height: 320px;
}
.chart-host .echarts,
.chart-host .diverging-chart,
.chart-host .pair-chart {
  width: 100% !important;
  height: 100% !important;
  min-height: inherit;
}
.module-title {
  font-size: 14px;
  font-weight: 700;
  color: #1f2d3d;
  flex-shrink: 0;
}
.module-sub {
  margin-top: 2px;
  margin-bottom: 10px;
  font-size: 12px;
  color: #909399;
  flex-shrink: 0;
}
.module-title-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 4px;
}
.structure-panel .structure-body {
  display: flex;
  flex-direction: column;
  flex: 1 1 auto;
  justify-content: space-between;
  gap: 8px;
  min-height: 0;
}
.structure-chart {
  height: 280px;
  width: 100%;
  flex: 0 0 auto;
  min-height: 280px;
}
.structure-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  margin-top: auto;
}
.stat-chip {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 10px 6px;
  border-radius: 8px;
  background: #fff;
  border: 1px solid #ebeef5;
}
.stat-chip.improve .stat-num {
  color: #67c23a;
}
.stat-chip.watch .stat-num {
  color: #f56c6c;
}
.stat-chip.flat .stat-num {
  color: #909399;
}
.stat-num {
  font-size: 22px;
  font-weight: 700;
  line-height: 1.15;
}
.stat-label {
  font-size: 11px;
  color: #909399;
  margin-top: 2px;
}
.axis-legend {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.axis-chip {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 999px;
  background: #f5f7fa;
}
.axis-chip.improve {
  color: #67c23a;
  background: #f0f9eb;
}
.axis-chip.watch {
  color: #f56c6c;
  background: #fef0f0;
}
.diverging-chart {
  width: 100%;
  height: 100%;
  min-height: 200px;
}
.pair-chart {
  width: 100%;
  height: 100%;
  min-height: 320px;
}
.focus-panel {
  min-width: 0;
}
.focus-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  flex: 1 1 auto;
  align-content: start;
  min-height: 0;
}
@media (max-width: 768px) {
  .focus-grid {
    grid-template-columns: 1fr;
  }
}
.focus-grid.visual {
  margin-top: 0;
}
.focus-col {
  display: flex;
  flex-direction: column;
  gap: 0;
  min-width: 0;
}
.focus-col-title {
  font-size: 12px;
  font-weight: 700;
  margin-bottom: 8px;
  letter-spacing: 0.02em;
}
.focus-col-title.improve {
  color: #67c23a;
}
.focus-col-title.watch {
  color: #f56c6c;
}
.focus-empty {
  font-size: 12px;
  color: #c0c4cc;
  padding: 16px 8px;
  text-align: center;
  border: 1px dashed #e4e7ed;
  border-radius: 8px;
  background: #fff;
}
.focus-card {
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 10px 12px;
  margin-bottom: 8px;
  background: #fff;
  cursor: pointer;
  transition: box-shadow 0.15s ease, border-color 0.15s ease;
}
.focus-card:last-child {
  margin-bottom: 0;
}
.focus-card:hover,
.focus-card.active {
  border-color: #c6e2ff;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.12);
}
.focus-card.improve {
  border-left: 3px solid #67c23a;
}
.focus-card.watch {
  border-left: 3px solid #f56c6c;
}
.focus-card-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.focus-name {
  font-size: 13px;
  font-weight: 600;
  color: #303133;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.focus-badge {
  font-size: 12px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  padding: 2px 8px;
  border-radius: 999px;
  flex-shrink: 0;
}
.focus-badge.improve {
  color: #67c23a;
  background: #f0f9eb;
}
.focus-badge.watch {
  color: #f56c6c;
  background: #fef0f0;
}
.dumbbell {
  display: grid;
  grid-template-columns: minmax(48px, auto) 1fr minmax(48px, auto);
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
}
.dumbbell-val {
  font-size: 12px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}
.dumbbell-val.prev {
  color: #909399;
  text-align: right;
}
.dumbbell-val.curr {
  color: #1f2d3d;
  text-align: left;
}
.dumbbell-track {
  position: relative;
  height: 14px;
  display: flex;
  align-items: center;
}
.dumbbell-line {
  position: absolute;
  left: 8%;
  right: 8%;
  height: 3px;
  border-radius: 2px;
  background: #dcdfe6;
}
.dumbbell-line.improve {
  background: #b3e19d;
}
.dumbbell-line.watch {
  background: #fab6b6;
}
.dumbbell-dot {
  position: absolute;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  top: 50%;
  transform: translateY(-50%);
  box-sizing: border-box;
}
.dumbbell-dot.prev {
  left: 6%;
  background: #fff;
  border: 2px solid #c0c4cc;
}
.dumbbell-dot.curr {
  right: 6%;
  border: 2px solid transparent;
}
.dumbbell-dot.curr.improve {
  background: #67c23a;
}
.dumbbell-dot.curr.watch {
  background: #f56c6c;
}
.focus-bar-track {
  height: 6px;
  background: #ebeef5;
  border-radius: 3px;
  overflow: hidden;
}
.focus-bar-fill {
  height: 100%;
  border-radius: 3px;
  min-width: 4px;
}
.focus-bar-fill.improve {
  background: #67c23a;
}
.focus-bar-fill.watch {
  background: #f56c6c;
}
.focus-level {
  margin-top: 8px;
}
.compare-table-toggle {
  text-align: center;
  padding: 4px 0 8px;
}
.compare-table {
  width: 100%;
}
.table-change {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.kpi-rel {
  font-weight: 500;
  color: #a0aec0;
}
.yoy-up {
  color: #67c23a;
}
.yoy-down {
  color: #f56c6c;
}
.yoy-flat {
  color: #909399;
}
.meaning-improve {
  color: #67c23a;
}
.meaning-watch {
  color: #f56c6c;
}
.meaning-flat {
  color: #909399;
}
:deep(.row-highlight) > td {
  background: #ecf5ff !important;
}
@media print {
  .compare-card {
    break-inside: avoid;
    box-shadow: none !important;
    border: 1px solid #ddd !important;
  }
}
</style>
