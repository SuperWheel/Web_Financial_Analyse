<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart, LineChart } from 'echarts/charts'
import {
  DataZoomComponent,
  GridComponent,
  LegendComponent,
  MarkLineComponent,
  TitleComponent,
  TooltipComponent,
} from 'echarts/components'
import type { EChartsOption } from 'echarts'
import { useCompanyStore } from '@/stores/company'
import {
  fetchCompare,
  fetchComparePeriods,
  formatAmount,
  formatPct,
  type CompareFieldRow,
  type CompareMatrix,
  type ComparePeriod,
  type PeriodType,
  type StatementType,
} from '@/api/compare'
import { downloadCompanyExcel } from '@/api/export'
import { ElMessage } from 'element-plus'

use([
  CanvasRenderer,
  LineChart,
  BarChart,
  GridComponent,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  DataZoomComponent,
  MarkLineComponent,
])

const DEFAULT_PERIOD_CAP = 5
const DEFAULT_TREND_KEYS: Record<StatementType, string[]> = {
  balance: ['total_assets', 'total_liabilities', 'total_equity', 'monetary_funds'],
  income: ['operating_revenue', 'operating_cost', 'operating_profit', 'net_profit'],
  cashflow: [
    'net_cash_flow_operating',
    'net_cash_flow_investing',
    'net_cash_flow_financing',
    'net_increase_in_cash',
  ],
}

const HIGHLIGHT_KEYS: Record<StatementType, string[]> = {
  balance: [
    'total_assets',
    'total_liabilities',
    'total_equity',
    'monetary_funds',
    'total_current_assets',
    'total_current_liabilities',
  ],
  income: [
    'operating_revenue',
    'operating_cost',
    'operating_profit',
    'net_profit',
    'net_profit_parent',
  ],
  cashflow: [
    'net_cash_flow_operating',
    'net_cash_flow_investing',
    'net_cash_flow_financing',
    'net_increase_in_cash',
  ],
}

type AxisMode = 'auto' | 'scale' | 'log' | 'custom'
type ChartValueMode = 'amount' | 'index'

const companyStore = useCompanyStore()
const { companies, loading: companiesLoading } = storeToRefs(companyStore)

const companyId = ref<number | null>(null)
const statementType = ref<StatementType>('balance')
const periodType = ref<PeriodType>('annual')
const periods = ref<ComparePeriod[]>([])
const selectedYears = ref<number[]>([])
const matrix = ref<CompareMatrix | null>(null)
const loading = ref(false)
const metricMode = ref<'amount' | 'structure' | 'delta_pct' | 'combo'>('combo')
const selectedKeys = ref<string[]>([...DEFAULT_TREND_KEYS.balance])
const errorMsg = ref('')
const exporting = ref(false)
const tableFilter = ref('')
const hideEmptyRows = ref(true)

// 图表坐标控制
const axisMode = ref<AxisMode>('scale')
const chartValueMode = ref<ChartValueMode>('amount')
const dualAxis = ref(true)
const axisMin = ref<number | undefined>(undefined)
const axisMax = ref<number | undefined>(undefined)
const rightAxisMin = ref<number | undefined>(undefined)
const rightAxisMax = ref<number | undefined>(undefined)

const companyName = computed(
  () => companies.value.find((c) => c.id === companyId.value)?.name || '企业'
)

const filteredPeriodOptions = computed(() => {
  const flag =
    statementType.value === 'balance'
      ? 'has_balance'
      : statementType.value === 'income'
        ? 'has_income'
        : 'has_cashflow'
  return periods.value
    .filter((p) => p.period_type === periodType.value && p[flag])
    .map((p) => ({
      year: p.year,
      quarter: p.quarter,
      label:
        p.period_type === 'annual' ? `${p.year} 年报` : `${p.year} Q${p.quarter}`,
      value: p.year,
    }))
})

const flatFieldRows = computed(() => {
  if (!matrix.value) return [] as Array<CompareFieldRow & { groupLabel: string }>
  return matrix.value.groups.flatMap((g) =>
    g.rows.map((r) => ({ ...r, groupLabel: g.label }))
  )
})

const rowByKey = computed(() => {
  const m = new Map<string, CompareFieldRow & { groupLabel: string }>()
  for (const r of flatFieldRows.value) m.set(r.key, r)
  return m
})

const periodLabels = computed(() => matrix.value?.periods.map((p) => p.label) || [])
const lastIdx = computed(() => Math.max(0, (matrix.value?.periods.length || 1) - 1))
const prevIdx = computed(() => Math.max(0, lastIdx.value - 1))
const hasMultiPeriod = computed(() => (matrix.value?.periods.length || 0) >= 2)

const latestLabel = computed(
  () => matrix.value?.periods[lastIdx.value]?.label || '本期'
)
const prevLabel = computed(() =>
  hasMultiPeriod.value ? matrix.value?.periods[prevIdx.value]?.label || '上期' : '—'
)

const trendOptions = computed(() =>
  flatFieldRows.value.map((r) => ({ key: r.key, label: r.label, group: r.groupLabel }))
)

/** 摘要 KPI：重点科目最新值 + 环比 */
const summaryCards = computed(() => {
  const keys = HIGHLIGHT_KEYS[statementType.value]
  return keys
    .map((key) => {
      const row = rowByKey.value.get(key)
      if (!row) return null
      const li = lastIdx.value
      const pi = prevIdx.value
      const cur = row.values[li] ?? null
      const prev = hasMultiPeriod.value ? row.values[pi] ?? null : null
      const dPct = hasMultiPeriod.value ? row.delta_pcts[li] ?? null : null
      const dAbs = hasMultiPeriod.value ? row.deltas[li] ?? null : null
      return {
        key,
        label: row.label,
        current: cur,
        previous: prev,
        deltaPct: dPct,
        deltaAbs: dAbs,
      }
    })
    .filter((x): x is NonNullable<typeof x> => !!x)
})

/** 最近一期变动最大的科目（排除全 null） */
const movers = computed(() => {
  const li = lastIdx.value
  if (!hasMultiPeriod.value) return { up: [] as typeof base, down: [] as typeof base }
  const base = flatFieldRows.value
    .map((r) => {
      const pct = r.delta_pcts[li]
      const abs = r.deltas[li]
      const cur = r.values[li]
      if (pct === null || pct === undefined || cur === null) return null
      return {
        key: r.key,
        label: r.label,
        groupLabel: r.groupLabel,
        pct,
        abs,
        current: cur,
      }
    })
    .filter((x): x is NonNullable<typeof x> => !!x)

  const up = [...base]
    .filter((x) => x.pct > 0)
    .sort((a, b) => b.pct - a.pct)
    .slice(0, 5)
  const down = [...base]
    .filter((x) => x.pct < 0)
    .sort((a, b) => a.pct - b.pct)
    .slice(0, 5)
  return { up, down }
})

const moverBarOption = computed((): EChartsOption => {
  const items = [...movers.value.down].reverse().concat(movers.value.up)
  if (!items.length) {
    return {
      title: {
        text: hasMultiPeriod.value ? '暂无有效环比' : '需至少 2 期才有变动榜',
        left: 'center',
        top: 'middle',
        textStyle: { color: '#909399', fontSize: 13, fontWeight: 400 },
      },
    }
  }
  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      valueFormatter: (v) =>
        typeof v === 'number' ? `${(v * 100).toFixed(1)}%` : '—',
    },
    grid: { left: 8, right: 24, top: 8, bottom: 8, containLabel: true },
    xAxis: {
      type: 'value',
      axisLabel: {
        formatter: (v: number) => `${(v * 100).toFixed(0)}%`,
      },
      splitLine: { lineStyle: { type: 'dashed' } },
    },
    yAxis: {
      type: 'category',
      data: items.map((i) => i.label),
      axisLabel: { width: 100, overflow: 'truncate' },
    },
    series: [
      {
        type: 'bar',
        data: items.map((i) => ({
          value: i.pct,
          itemStyle: {
            color: i.pct >= 0 ? '#67c23a' : '#f56c6c',
          },
        })),
        barMaxWidth: 16,
        label: {
          show: true,
          position: 'right',
          formatter: (p: { value?: number }) =>
            typeof p.value === 'number' ? `${(p.value * 100).toFixed(1)}%` : '',
          fontSize: 11,
        },
      },
    ],
  }
})

function seriesValuesForChart(row: CompareFieldRow): Array<number | null> {
  if (chartValueMode.value === 'index') {
    const first = row.values.find((v) => v !== null && v !== undefined)
    if (first === null || first === undefined || first === 0) {
      return row.values.map(() => null)
    }
    return row.values.map((v) =>
      v === null || v === undefined ? null : Number(((v / first) * 100).toFixed(2))
    )
  }
  return row.values.map((v) => (v === null ? null : v))
}

function maxAbsOf(vals: Array<number | null>): number {
  let m = 0
  for (const v of vals) {
    if (v === null || v === undefined) continue
    m = Math.max(m, Math.abs(v))
  }
  return m
}

const chartOption = computed((): EChartsOption => {
  if (!matrix.value || !selectedKeys.value.length) {
    return {
      title: {
        text: '勾选科目查看趋势（可点表格行）',
        left: 'center',
        top: 'middle',
        textStyle: { color: '#909399', fontSize: 14, fontWeight: 400 },
      },
    }
  }

  const seriesRaw = selectedKeys.value
    .map((key) => {
      const row = rowByKey.value.get(key)
      if (!row) return null
      const data = seriesValuesForChart(row)
      return {
        key,
        name: row.label,
        data,
        mag: maxAbsOf(data),
      }
    })
    .filter((s): s is NonNullable<typeof s> => !!s)

  if (!seriesRaw.length) {
    return {
      title: {
        text: '所选科目无数据',
        left: 'center',
        top: 'middle',
        textStyle: { color: '#909399', fontSize: 14, fontWeight: 400 },
      },
    }
  }

  // 双轴：按量级拆分，避免小数被大数压扁
  let leftKeys = new Set(seriesRaw.map((s) => s.key))
  let rightKeys = new Set<string>()
  if (dualAxis.value && seriesRaw.length >= 2 && chartValueMode.value === 'amount') {
    const mags = seriesRaw.map((s) => s.mag).filter((m) => m > 0)
    const maxM = Math.max(...mags, 0)
    const minM = Math.min(...mags.filter((m) => m > 0), maxM)
    if (maxM > 0 && minM > 0 && maxM / minM >= 20) {
      const threshold = Math.sqrt(maxM * minM) // 几何中位
      leftKeys = new Set(seriesRaw.filter((s) => s.mag >= threshold).map((s) => s.key))
      rightKeys = new Set(seriesRaw.filter((s) => s.mag < threshold).map((s) => s.key))
      // 保证两侧都有
      if (!leftKeys.size || !rightKeys.size) {
        leftKeys = new Set(seriesRaw.map((s) => s.key))
        rightKeys = new Set()
      }
    }
  }

  const useDual = dualAxis.value && rightKeys.size > 0
  const isLog = axisMode.value === 'log' && chartValueMode.value === 'amount'

  function buildYAxis(
    side: 'left' | 'right',
    name: string
  ): Record<string, unknown> {
    const customMin = side === 'left' ? axisMin.value : rightAxisMin.value
    const customMax = side === 'left' ? axisMax.value : rightAxisMax.value
    const base: Record<string, unknown> = {
      type: isLog ? 'log' : 'value',
      name,
      nameTextStyle: { fontSize: 11, color: '#909399' },
      position: side,
      axisLabel: {
        formatter: (v: number) =>
          chartValueMode.value === 'index' ? `${v}` : formatCompact(v),
      },
      splitLine: side === 'left' ? { show: true } : { show: false },
    }
    if (axisMode.value === 'scale' && !isLog) {
      base.scale = true
    }
    if (axisMode.value === 'custom') {
      if (customMin !== undefined && customMin !== null && !Number.isNaN(customMin)) {
        base.min = customMin
      }
      if (customMax !== undefined && customMax !== null && !Number.isNaN(customMax)) {
        base.max = customMax
      }
    }
    if (isLog) {
      // log 轴不能有 <=0；ECharts 会跳过非正值
      base.min = customMin && customMin > 0 ? customMin : undefined
    }
    return base
  }

  const yAxis = useDual
    ? [
        buildYAxis('left', chartValueMode.value === 'index' ? '指数(左)' : '大额(左)'),
        buildYAxis('right', chartValueMode.value === 'index' ? '指数(右)' : '小额(右)'),
      ]
    : [
        buildYAxis(
          'left',
          chartValueMode.value === 'index'
            ? '指数（首期=100）'
            : axisMode.value === 'log'
              ? '对数轴'
              : '金额'
        ),
      ]

  const series = seriesRaw.map((s) => ({
    name: s.name,
    type: 'line' as const,
    smooth: true,
    showSymbol: true,
    symbolSize: 6,
    yAxisIndex: useDual && rightKeys.has(s.key) ? 1 : 0,
    data: s.data.map((v) => {
      if (v === null) return null
      if (isLog && v <= 0) return null
      return v
    }),
  }))

  return {
    tooltip: {
      trigger: 'axis',
      valueFormatter: (v) => {
        if (v === null || v === undefined || v === '') return '—'
        const n = Number(v)
        if (chartValueMode.value === 'index') return `${n.toFixed(1)}（指数）`
        return formatAmount(n)
      },
    },
    legend: { type: 'scroll', bottom: 0 },
    grid: {
      left: 52,
      right: useDual ? 64 : 36,
      top: 36,
      bottom: 52,
      containLabel: true,
    },
    dataZoom: [
      { type: 'inside', xAxisIndex: 0, filterMode: 'none' },
      {
        type: 'slider',
        xAxisIndex: 0,
        height: 16,
        bottom: 26,
        brushSelect: false,
      },
      // Y 轴自由缩放：滚轮 + 右侧滑条
      {
        type: 'inside',
        yAxisIndex: useDual ? [0, 1] : [0],
        filterMode: 'none',
        zoomOnMouseWheel: 'shift',
        moveOnMouseMove: true,
      },
      {
        type: 'slider',
        yAxisIndex: useDual ? [0, 1] : [0],
        width: 14,
        right: 4,
        top: 40,
        bottom: 58,
        brushSelect: false,
        showDetail: true,
        labelFormatter: (v: number) =>
          chartValueMode.value === 'index' ? String(Math.round(v)) : formatCompact(v),
      },
    ],
    xAxis: {
      type: 'category',
      data: periodLabels.value,
      boundaryGap: false,
    },
    yAxis: yAxis as EChartsOption['yAxis'],
    series,
  }
})

const tableRows = computed(() => {
  if (!matrix.value) return [] as Array<
    CompareFieldRow & { groupLabel: string; isGroupHeader?: boolean }
  >
  const q = tableFilter.value.trim().toLowerCase()
  const out: Array<
    CompareFieldRow & { groupLabel: string; isGroupHeader?: boolean }
  > = []
  for (const g of matrix.value.groups) {
    const fields = g.rows.filter((r) => {
      if (q && !r.label.toLowerCase().includes(q) && !r.key.toLowerCase().includes(q)) {
        return false
      }
      if (hideEmptyRows.value) {
        const any = r.values.some((v) => v !== null && v !== undefined)
        if (!any) return false
      }
      return true
    })
    if (!fields.length) continue
    out.push({
      key: `__group_${g.key}`,
      label: g.label,
      values: [],
      deltas: [],
      delta_pcts: [],
      structure_pcts: [],
      groupLabel: g.label,
      isGroupHeader: true,
    })
    for (const row of fields) out.push({ ...row, groupLabel: g.label })
  }
  return out
})

/** 金额智能单位：元 / 万 / 亿（用于 KPI 卡与紧凑轴） */
function formatMoneySmart(
  value: number | null | undefined,
  digits = 2
): { text: string; unit: string; full: string } {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return { text: '—', unit: '', full: '—' }
  }
  const n = Number(value)
  const abs = Math.abs(n)
  const fmt = (x: number) =>
    x.toLocaleString('zh-CN', {
      maximumFractionDigits: digits,
      minimumFractionDigits: 0,
    })
  if (abs >= 1e8) {
    const t = fmt(n / 1e8)
    return { text: t, unit: '亿元', full: `${t} 亿元` }
  }
  if (abs >= 1e4) {
    const t = fmt(n / 1e4)
    return { text: t, unit: '万元', full: `${t} 万元` }
  }
  const t = fmt(n)
  return { text: t, unit: '元', full: `${t} 元` }
}

function formatCompact(v: number): string {
  return formatMoneySmart(v).full.replace(' 元', '')
}

function cellDisplay(row: CompareFieldRow, idx: number): string {
  if (metricMode.value === 'structure') return formatPct(row.structure_pcts[idx] ?? null)
  if (metricMode.value === 'delta_pct') return formatPct(row.delta_pcts[idx] ?? null)
  if (metricMode.value === 'combo') {
    const amt = formatAmount(row.values[idx] ?? null)
    if (idx === 0) return amt
    const p = formatPct(row.delta_pcts[idx] ?? null)
    return p === '—' ? amt : `${amt}（${p}）`
  }
  return formatAmount(row.values[idx] ?? null)
}

function cellClass(row: CompareFieldRow, idx: number): string {
  if (metricMode.value === 'amount') return ''
  const v = row.delta_pcts[idx]
  if (v === null || v === undefined) return metricMode.value === 'structure' ? '' : 'cell-muted'
  if (metricMode.value === 'delta_pct' || metricMode.value === 'combo') {
    if (v > 0) return 'cell-up'
    if (v < 0) return 'cell-down'
  }
  return ''
}

function onRowClick(row: CompareFieldRow & { isGroupHeader?: boolean }) {
  if (row.isGroupHeader) return
  const key = row.key
  if (selectedKeys.value.includes(key)) {
    selectedKeys.value = selectedKeys.value.filter((k) => k !== key)
  } else {
    selectedKeys.value = [...selectedKeys.value, key]
  }
}

function rowClassName({
  row,
}: {
  row: CompareFieldRow & { isGroupHeader?: boolean }
}) {
  const classes: string[] = []
  if (row.isGroupHeader) classes.push('group-header-row')
  if (!row.isGroupHeader && selectedKeys.value.includes(row.key)) {
    classes.push('row-charted')
  }
  return classes.join(' ')
}

function resetAxisCustom() {
  axisMin.value = undefined
  axisMax.value = undefined
  rightAxisMin.value = undefined
  rightAxisMax.value = undefined
}

function applyNiceScaleFromSelection() {
  // 根据当前勾选序列自动填自定义范围（便于微调小数指标）
  const rows = selectedKeys.value
    .map((k) => rowByKey.value.get(k))
    .filter((r): r is NonNullable<typeof r> => !!r)
  const vals = rows.flatMap((r) => seriesValuesForChart(r)).filter((v): v is number => v !== null)
  if (!vals.length) {
    ElMessage.warning('当前科目无有效数值')
    return
  }
  const min = Math.min(...vals)
  const max = Math.max(...vals)
  const pad = (max - min) * 0.08 || Math.abs(max) * 0.05 || 1
  axisMode.value = 'custom'
  axisMin.value = Number((min - pad).toFixed(4))
  axisMax.value = Number((max + pad).toFixed(4))
  ElMessage.success('已按所选序列写入坐标范围，可再微调')
}

async function onExportExcel() {
  if (companyId.value == null) {
    ElMessage.warning('请先选择企业')
    return
  }
  exporting.value = true
  try {
    await downloadCompanyExcel(companyId.value, {
      period_type: periodType.value,
      years: selectedYears.value.length
        ? [...selectedYears.value].sort((a, b) => a - b)
        : undefined,
    })
    ElMessage.success('Excel 已开始下载（含三表与财务比率）')
  } catch {
    // interceptor
  } finally {
    exporting.value = false
  }
}

async function loadPeriods() {
  if (!companyId.value) {
    periods.value = []
    selectedYears.value = []
    matrix.value = null
    return
  }
  periods.value = await fetchComparePeriods(companyId.value)
  applyDefaultYears()
}

function applyDefaultYears() {
  const opts = filteredPeriodOptions.value
  selectedYears.value = opts.slice(0, DEFAULT_PERIOD_CAP).map((o) => o.value)
}

async function loadMatrix() {
  if (!companyId.value) {
    matrix.value = null
    return
  }
  if (!selectedYears.value.length) {
    matrix.value = null
    return
  }
  loading.value = true
  errorMsg.value = ''
  try {
    matrix.value = await fetchCompare(companyId.value, {
      statement_type: statementType.value,
      period_type: periodType.value,
      years: [...selectedYears.value].sort((a, b) => a - b),
    })
    // 保留已选且仍存在的科目，否则回默认
    const present = new Set(flatFieldRows.value.map((r) => r.key))
    const kept = selectedKeys.value.filter((k) => present.has(k))
    selectedKeys.value = kept.length
      ? kept
      : DEFAULT_TREND_KEYS[statementType.value].filter((k) => present.has(k))
  } catch (e: unknown) {
    matrix.value = null
    errorMsg.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

watch(companyId, async () => {
  await loadPeriods()
  await loadMatrix()
})

watch(statementType, async () => {
  selectedKeys.value = [...DEFAULT_TREND_KEYS[statementType.value]]
  applyDefaultYears()
  await loadMatrix()
})

watch(periodType, async () => {
  applyDefaultYears()
  await loadMatrix()
})

watch(selectedYears, async () => {
  await loadMatrix()
})

onMounted(async () => {
  await companyStore.load()
  if (!companyId.value && companies.value.length) {
    companyId.value = companies.value[0].id
  } else {
    await loadPeriods()
    await loadMatrix()
  }
})
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
      <!-- 摘要 KPI -->
      <div class="kpi-grid">
        <el-card
          v-for="card in summaryCards"
          :key="card.key"
          shadow="hover"
          class="kpi-card"
          :class="{ active: selectedKeys.includes(card.key) }"
          @click="
            selectedKeys = selectedKeys.includes(card.key)
              ? selectedKeys.filter((k) => k !== card.key)
              : [...selectedKeys, card.key]
          "
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

      <div class="mid-grid">
        <!-- 趋势 + 坐标控制 -->
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
                <el-option-group
                  v-for="g in matrix.groups"
                  :key="g.key"
                  :label="g.label"
                >
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
              <el-button size="small" @click="applyNiceScaleFromSelection">
                按所选填范围
              </el-button>
              <el-button size="small" text @click="resetAxisCustom">清空范围</el-button>
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
              <template v-if="dualAxis && chartValueMode === 'amount'">
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
              :key="`c-${statementType}-${axisMode}-${chartValueMode}-${dualAxis}-${selectedKeys.join(',')}`"
              autoresize
            />
          </div>
        </el-card>

        <!-- 变动榜 -->
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
                @click="
                  selectedKeys = selectedKeys.includes(m.key)
                    ? selectedKeys.filter((k) => k !== m.key)
                    : [...selectedKeys, m.key]
                "
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
                @click="
                  selectedKeys = selectedKeys.includes(m.key)
                    ? selectedKeys.filter((k) => k !== m.key)
                    : [...selectedKeys, m.key]
                "
              >
                <span>{{ m.label }}</span>
                <span class="cell-down">{{ formatPct(m.pct) }}</span>
              </div>
              <el-empty v-if="!movers.down.length" :image-size="48" description="无" />
            </div>
          </div>
        </el-card>
      </div>

      <!-- 对照表 -->
      <el-card shadow="never" class="table-card">
        <template #header>
          <div class="card-head">
            <span>科目对照表</span>
            <div class="table-tools">
              <el-input
                v-model="tableFilter"
                clearable
                size="small"
                placeholder="筛选科目"
                style="width: 160px"
              />
              <el-checkbox v-model="hideEmptyRows" size="small">隐藏全空行</el-checkbox>
              <span class="meta">
                {{ matrix.periods.length }} 期 ·
                {{
                  metricMode === 'combo'
                    ? '金额+环比'
                    : metricMode === 'amount'
                      ? '金额'
                      : metricMode === 'structure'
                        ? '结构占比'
                        : '环比'
                }}
              </span>
            </div>
          </div>
        </template>

        <el-table
          :data="tableRows"
          border
          stripe
          size="small"
          height="520"
          :row-class-name="rowClassName"
          @row-click="onRowClick"
        >
          <el-table-column prop="label" label="科目" fixed min-width="200" show-overflow-tooltip>
            <template #default="{ row }">
              <strong v-if="row.isGroupHeader">{{ row.label }}</strong>
              <span v-else class="item-label">
                {{ row.label }}
                <el-tag
                  v-if="selectedKeys.includes(row.key)"
                  size="small"
                  type="primary"
                  effect="plain"
                  style="margin-left: 6px"
                >
                  趋势
                </el-tag>
              </span>
            </template>
          </el-table-column>
          <el-table-column
            v-for="(p, idx) in matrix.periods"
            :key="`${p.year}-${p.quarter ?? ''}-${idx}`"
            :label="p.label"
            min-width="140"
            align="right"
          >
            <template #default="{ row }">
              <span v-if="row.isGroupHeader" />
              <span v-else :class="cellClass(row, idx)">{{ cellDisplay(row, idx) }}</span>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
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
.chart-card,
.mover-card,
.table-card {
  border-radius: 8px;
}
.chart-card :deep(.el-card__body),
.mover-card :deep(.el-card__body),
.table-card :deep(.el-card__body) {
  padding: 12px;
}
.chart-card :deep(.el-card__header),
.mover-card :deep(.el-card__header),
.table-card :deep(.el-card__header) {
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
.table-tools {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.item-label {
  cursor: pointer;
}
.cell-up {
  color: #067647;
}
.cell-down {
  color: #b42318;
}
.cell-muted {
  color: #c0c4cc;
}
:deep(.group-header-row) {
  background: #f5f7fa !important;
  cursor: default;
}
:deep(.group-header-row td) {
  font-weight: 600;
}
:deep(.row-charted) {
  background: #ecf5ff !important;
}
:deep(.el-table__row) {
  cursor: pointer;
}
</style>
