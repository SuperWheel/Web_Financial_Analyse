<script setup lang="ts">
import CompareKpiGrid from '@/components/compare/CompareKpiGrid.vue'
import AccountTrendChart from '@/components/compare/AccountTrendChart.vue'
import ChangeRanking from '@/components/compare/ChangeRanking.vue'
import StatementMatrix from '@/components/compare/StatementMatrix.vue'
import { useStatementCompare } from '@/composables/useStatementCompare'

const {
  companies,
  companiesLoading,
  companyId,
  companyName,
  statementType,
  periodType,
  selectedYears,
  filteredPeriodOptions,
  matrix,
  loading,
  metricMode,
  selectedKeys,
  errorMsg,
  exporting,
  tableFilter,
  hideEmptyRows,
  axisMode,
  chartValueMode,
  dualAxis,
  axisMin,
  axisMax,
  rightAxisMin,
  rightAxisMax,
  latestLabel,
  prevLabel,
  hasMultiPeriod,
  summaryCards,
  movers,
  moverBarOption,
  chartOption,
  chartRemountKey,
  tableRows,
  cellDisplay,
  cellClass,
  toggleSelectedKey,
  onRowClick,
  rowClassName,
  resetAxisCustom,
  applyNiceScaleFromSelection,
  onExportExcel,
} = useStatementCompare()
</script>

<template>
  <div class="compare-page" v-loading="loading || companiesLoading">
    <el-card shadow="never" class="toolbar-card">
      <div class="toolbar">
        <div class="field">
          <span class="label">企业</span>
          <el-select v-model="companyId" filterable placeholder="选择企业" style="width: 200px">
            <el-option v-for="c in companies" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </div>
        <div class="field">
          <span class="label">报表</span>
          <el-radio-group v-model="statementType" size="default">
            <el-radio-button value="balance">资产负债表</el-radio-button>
            <el-radio-button value="income">利润表</el-radio-button>
            <el-radio-button value="cashflow">现金流量表</el-radio-button>
          </el-radio-group>
        </div>
        <div class="field">
          <span class="label">期间类型</span>
          <el-radio-group v-model="periodType" size="default">
            <el-radio-button value="annual">年报</el-radio-button>
            <el-radio-button value="quarterly">季报</el-radio-button>
          </el-radio-group>
        </div>
        <div class="field grow">
          <span class="label">对比期间</span>
          <el-select
            v-model="selectedYears"
            multiple
            collapse-tags
            collapse-tags-tooltip
            placeholder="选择期间"
            style="min-width: 220px; width: 100%; max-width: 360px"
          >
            <el-option
              v-for="o in filteredPeriodOptions"
              :key="`${o.year}-${o.quarter ?? ''}`"
              :label="o.label"
              :value="o.value"
            />
          </el-select>
        </div>
        <div class="field">
          <span class="label">表格显示</span>
          <el-radio-group v-model="metricMode" size="default">
            <el-radio-button value="combo">金额+环比</el-radio-button>
            <el-radio-button value="amount">仅金额</el-radio-button>
            <el-radio-button value="delta_pct">仅环比%</el-radio-button>
            <el-radio-button value="structure" :disabled="statementType === 'cashflow'">
              结构%
            </el-radio-button>
          </el-radio-group>
        </div>
        <div class="field">
          <el-button
            type="primary"
            plain
            :loading="exporting"
            :disabled="!companyId"
            @click="onExportExcel"
          >
            导出 Excel
          </el-button>
        </div>
      </div>
      <p class="hint">
        {{ companyName }} · 最新期 {{ latestLabel }}
        <template v-if="hasMultiPeriod"> · 环比对照 {{ prevLabel }}</template>
        · 点击表格行加入/移除趋势；环比为序列相邻期（非同比）。
        <template v-if="matrix?.base_label">结构分母：{{ matrix.base_label }}。</template>
      </p>
      <el-alert v-if="errorMsg" :title="errorMsg" type="error" show-icon :closable="false" class="err" />
    </el-card>

    <template v-if="matrix && matrix.periods.length">
      <CompareKpiGrid
        :cards="summaryCards"
        :selected-keys="selectedKeys"
        :prev-label="prevLabel"
        @toggle="toggleSelectedKey"
      />

      <div class="mid-grid">
        <AccountTrendChart
          v-model:selected-keys="selectedKeys"
          v-model:chart-value-mode="chartValueMode"
          v-model:dual-axis="dualAxis"
          v-model:axis-mode="axisMode"
          v-model:axis-min="axisMin"
          v-model:axis-max="axisMax"
          v-model:right-axis-min="rightAxisMin"
          v-model:right-axis-max="rightAxisMax"
          :matrix="matrix"
          :chart-option="chartOption"
          :remount-key="chartRemountKey"
          @apply-nice-scale="applyNiceScaleFromSelection"
          @reset-axis="resetAxisCustom"
        />

        <ChangeRanking
          :movers="movers"
          :mover-bar-option="moverBarOption"
          :prev-label="prevLabel"
          :latest-label="latestLabel"
          @toggle="toggleSelectedKey"
        />
      </div>

      <StatementMatrix
        v-model:table-filter="tableFilter"
        v-model:hide-empty-rows="hideEmptyRows"
        :matrix="matrix"
        :table-rows="tableRows"
        :selected-keys="selectedKeys"
        :metric-mode="metricMode"
        :cell-display="cellDisplay"
        :cell-class="cellClass"
        :row-class-name="rowClassName"
        @row-click="onRowClick"
      />
    </template>

    <el-empty
      v-else-if="!loading"
      description="请选择企业与至少一个有数据的期间"
    />
  </div>
</template>

<style scoped>
.compare-page {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.toolbar-card :deep(.el-card__body) {
  padding: 12px 14px 10px;
}
.toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 10px 14px;
  align-items: center;
}
.field {
  display: flex;
  align-items: center;
  gap: 8px;
}
.field.grow {
  flex: 1 1 220px;
}
.label {
  color: #606266;
  font-size: 13px;
  white-space: nowrap;
}
.hint {
  margin: 8px 0 0;
  color: #909399;
  font-size: 12px;
  line-height: 1.45;
}
.err {
  margin-top: 8px;
}
.mid-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.55fr) minmax(300px, 1fr);
  gap: 10px;
  align-items: stretch;
}
@media (max-width: 1100px) {
  .mid-grid {
    grid-template-columns: 1fr;
  }
}
</style>
