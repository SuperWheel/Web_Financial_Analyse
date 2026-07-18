<script setup lang="ts">
import type { ViewerRole } from '@/utils/ratioInsights'
import { useRatioAnalysis } from '@/composables/useRatioAnalysis'
import HealthSummary from '@/components/analysis/HealthSummary.vue'
import RatioKpiGrid from '@/components/analysis/RatioKpiGrid.vue'
import PeriodComparePanel from '@/components/analysis/PeriodComparePanel.vue'
import InsightPanels from '@/components/analysis/InsightPanels.vue'
import RatioTrendChart from '@/components/analysis/RatioTrendChart.vue'
import AllRatiosPanel from '@/components/analysis/AllRatiosPanel.vue'

const {
  ROLE_PROFILES,
  companies,
  companiesLoading,
  companyId,
  periods,
  periodKey,
  snapshot,
  history,
  loading,
  trendTab,
  selectedTrendKeys,
  showAll,
  showCompareTable,
  viewerRole,
  roleProfile,
  highlightedKey,
  exportingExcel,
  trendAxisMode,
  trendValueMode,
  trendAxisMin,
  trendAxisMax,
  trendRightMin,
  trendRightMax,
  periodOptions,
  primaryKpis,
  summary,
  summaryBadge,
  groupedRatios,
  periodCompare,
  movers,
  structureDonutOption,
  divergingChangeOption,
  periodPairOption,
  divergingChartHeight,
  trendCandidateOptions,
  chartAxisHint,
  chartOption,
  radarAxes,
  duPont,
  radarOption,
  duPontBarsOption,
  resetTrendAxisCustom,
  applyTrendNiceScale,
  yoyClass,
  yoyArrow,
  meaningClass,
  focusMetric,
  compareRowClassName,
  onCompareRowClick,
  onDivergingClick,
  onPairClick,
  detailReason,
  onRoleChange,
  exportSnapshotHtml,
  exportExcelWorkbook,
  printSnapshot,
} = useRatioAnalysis()
</script>

<template>
  <div class="analysis" v-loading="loading || companiesLoading">
    <div class="toolbar">
      <el-select
        v-model="companyId"
        placeholder="选择企业"
        filterable
        style="width: 240px"
      >
        <el-option
          v-for="c in companies"
          :key="c.id"
          :label="c.name"
          :value="c.id"
        />
      </el-select>
      <el-select
        v-model="periodKey"
        placeholder="报告期"
        style="width: 160px"
        :disabled="!periodOptions.length"
      >
        <el-option
          v-for="opt in periodOptions"
          :key="opt.value"
          :label="opt.label"
          :value="opt.value"
        />
      </el-select>
      <el-tag v-if="snapshot" type="info" effect="plain">
        数据期
        {{
          snapshot.period?.period_type === 'annual'
            ? `${snapshot.period.year} 年报`
            : `${snapshot.period?.year} Q${snapshot.period?.quarter}`
        }}
        · 完整度 {{ snapshot.summary.available }}/{{ snapshot.summary.total }}
      </el-tag>
      <el-radio-group
        v-if="snapshot"
        :model-value="viewerRole"
        size="small"
        class="role-switch no-print"
        @change="(v: string | number | boolean | undefined) => onRoleChange(String(v) as ViewerRole)"
      >
        <el-radio-button
          v-for="r in ROLE_PROFILES"
          :key="r.key"
          :value="r.key"
        >
          {{ r.label }}
        </el-radio-button>
      </el-radio-group>
      <div v-if="snapshot" class="toolbar-actions no-print">
        <el-button size="small" @click="exportSnapshotHtml">导出 HTML 快照</el-button>
        <el-button
          size="small"
          type="success"
          plain
          :loading="exportingExcel"
          @click="exportExcelWorkbook"
        >
          导出 Excel
        </el-button>
        <el-button size="small" type="primary" plain @click="printSnapshot">
          打印 / PDF
        </el-button>
      </div>
    </div>

    <el-empty
      v-if="!companyId"
      description="请先选择企业（可在仪表盘创建）"
    />
    <el-empty
      v-else-if="!periods.length"
      description="该企业暂无报表数据，请先在「年报导入」或「三大报表」录入"
    />

    <template v-else-if="snapshot">
      <HealthSummary
        :title="summary.title"
        :blurb="roleProfile.blurb"
        :badge-type="summaryBadge.type"
        :badge-text="summaryBadge.text"
        :lines="summary.lines"
      />

      <RatioKpiGrid
        :kpis="primaryKpis"
        :highlighted-key="highlightedKey"
        :yoy-class="yoyClass"
        :yoy-arrow="yoyArrow"
        :meaning-class="meaningClass"
        @focus="focusMetric"
      />

      <PeriodComparePanel
        :period-key="periodKey"
        :viewer-role="viewerRole"
        :period-compare="periodCompare"
        :movers="movers"
        :highlighted-key="highlightedKey"
        :show-compare-table="showCompareTable"
        :structure-donut-option="structureDonutOption"
        :diverging-change-option="divergingChangeOption"
        :period-pair-option="periodPairOption"
        :diverging-chart-height="divergingChartHeight"
        :yoy-class="yoyClass"
        :yoy-arrow="yoyArrow"
        :meaning-class="meaningClass"
        :compare-row-class-name="compareRowClassName"
        @focus="focusMetric"
        @update:show-compare-table="showCompareTable = $event"
        @diverging-click="onDivergingClick"
        @pair-click="onPairClick"
        @row-click="onCompareRowClick"
      />

      <InsightPanels
        :show-radar="roleProfile.showRadar"
        :show-dupont="roleProfile.showDupont"
        :radar-option="radarOption"
        :radar-axes="radarAxes"
        :du-pont="duPont"
        :du-pont-bars-option="duPontBarsOption"
      />

      <RatioTrendChart
        v-model:trend-tab="trendTab"
        v-model:selected-trend-keys="selectedTrendKeys"
        v-model:trend-value-mode="trendValueMode"
        v-model:trend-axis-mode="trendAxisMode"
        v-model:trend-axis-min="trendAxisMin"
        v-model:trend-axis-max="trendAxisMax"
        v-model:trend-right-min="trendRightMin"
        v-model:trend-right-max="trendRightMax"
        :history="history"
        :trend-candidate-options="trendCandidateOptions"
        :chart-axis-hint="chartAxisHint"
        :chart-option="chartOption"
        @apply-nice-scale="applyTrendNiceScale"
        @reset-axis-custom="resetTrendAxisCustom"
      />

      <AllRatiosPanel
        v-model:show-all="showAll"
        :grouped-ratios="groupedRatios"
        :detail-reason="detailReason"
      />
    </template>
  </div>
</template>

<style scoped>
.analysis {
  background: #f5f7fa;
  padding: 0;
  border-radius: 6px;
  min-height: 360px;
}
.toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
  margin-bottom: 12px;
  padding: 12px 16px;
  background: #fff;
  border-radius: 6px;
}
.toolbar-actions {
  display: flex;
  gap: 8px;
  margin-left: auto;
}
.role-switch {
  flex-wrap: wrap;
}
@media print {
  .no-print {
    display: none !important;
  }
  .analysis {
    background: #fff !important;
  }
}
</style>
