/** 报表对照页：筛选、矩阵加载、KPI/趋势/变动榜与表格状态 */
import { computed, onMounted, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
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

export const DEFAULT_PERIOD_CAP = 5

export const DEFAULT_TREND_KEYS: Record<StatementType, string[]> = {
  balance: ['total_assets', 'total_liabilities', 'total_equity', 'monetary_funds'],
  income: ['operating_revenue', 'operating_cost', 'operating_profit', 'net_profit'],
  cashflow: [
    'net_cash_flow_operating',
    'net_cash_flow_investing',
    'net_cash_flow_financing',
    'net_increase_in_cash',
  ],
}

export const HIGHLIGHT_KEYS: Record<StatementType, string[]> = {
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

export type AxisMode = 'auto' | 'scale' | 'log' | 'custom'
export type ChartValueMode = 'amount' | 'index'
export type MetricMode = 'amount' | 'structure' | 'delta_pct' | 'combo'

export type SummaryCard = {
  key: string
  label: string
  current: number | null
  previous: number | null
  deltaPct: number | null
  deltaAbs: number | null
}

export type MoverItem = {
  key: string
  label: string
  groupLabel: string
  pct: number
  abs: number | null
  current: number
}

export type TableRow = CompareFieldRow & {
  groupLabel: string
  isGroupHeader?: boolean
}

/** 金额智能单位：元 / 万 / 亿（用于 KPI 卡与紧凑轴） */
export function formatMoneySmart(
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

export function formatCompact(v: number): string {
  return formatMoneySmart(v).full.replace(' 元', '')
}

export function useStatementCompare() {
  const companyStore = useCompanyStore()
  const { companies, loading: companiesLoading } = storeToRefs(companyStore)

  const companyId = ref<number | null>(null)
  const statementType = ref<StatementType>('balance')
  const periodType = ref<PeriodType>('annual')
  const periods = ref<ComparePeriod[]>([])
  const selectedYears = ref<number[]>([])
  const matrix = ref<CompareMatrix | null>(null)
  const loading = ref(false)
  const metricMode = ref<MetricMode>('combo')
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

  /** 摘要 KPI：重点科目最新值 + 环比 */
  const summaryCards = computed((): SummaryCard[] => {
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
      .filter((x): x is SummaryCard => !!x)
  })

  /** 最近一期变动最大的科目（排除全 null） */
  const movers = computed(() => {
    const li = lastIdx.value
    if (!hasMultiPeriod.value) return { up: [] as MoverItem[], down: [] as MoverItem[] }
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
      .filter((x): x is MoverItem => !!x)

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
            position: 'right' as const,
            formatter: (p: { value?: unknown }) =>
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

  const chartRemountKey = computed(
    () =>
      `c-${statementType.value}-${axisMode.value}-${chartValueMode.value}-${dualAxis.value}-${selectedKeys.value.join(',')}`
  )

  const tableRows = computed((): TableRow[] => {
    if (!matrix.value) return []
    const q = tableFilter.value.trim().toLowerCase()
    const out: TableRow[] = []
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

  function toggleSelectedKey(key: string) {
    if (selectedKeys.value.includes(key)) {
      selectedKeys.value = selectedKeys.value.filter((k) => k !== key)
    } else {
      selectedKeys.value = [...selectedKeys.value, key]
    }
  }

  function onRowClick(row: TableRow) {
    if (row.isGroupHeader) return
    toggleSelectedKey(row.key)
  }

  function rowClassName({ row }: { row: TableRow }) {
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

  return {
    companies,
    companiesLoading,
    companyId,
    companyName,
    statementType,
    periodType,
    periods,
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
    formatMoneySmart,
    formatPct,
    cellDisplay,
    cellClass,
    toggleSelectedKey,
    onRowClick,
    rowClassName,
    resetAxisCustom,
    applyNiceScaleFromSelection,
    onExportExcel,
  }
}
