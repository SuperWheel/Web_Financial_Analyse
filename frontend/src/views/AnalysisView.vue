<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart, LineChart, PieChart, RadarChart } from 'echarts/charts'
import {
  DataZoomComponent,
  GraphicComponent,
  GridComponent,
  LegendComponent,
  RadarComponent,
  TooltipComponent,
} from 'echarts/components'
import { useCompanyStore } from '@/stores/company'
import {
  fetchRatioHistory,
  fetchRatioPeriods,
  fetchRatios,
  formatRatioValue,
  type RatioHistory,
  type RatioItem,
  type RatioPeriod,
  type RatioSnapshot,
  type PeriodType,
} from '@/api/ratio'
import { downloadCompanyExcel } from '@/api/export'
import { ElMessage } from 'element-plus'
import {
  ROLE_PROFILES,
  TREND_TABS,
  buildCompareNarrative,
  buildDuPont,
  buildHealthSummary,
  buildPeriodCompareRows,
  buildRadarAxes,
  computeYoY,
  defaultTrendKeysForTab,
  evaluateSignal,
  formatTransition,
  getRoleProfile,
  overallLabel,
  rankMovers,
  semanticChangeValue,
  toDisplayValue,
  type PeriodCompareRow,
  type ViewerRole,
} from '@/utils/ratioInsights'

use([
  CanvasRenderer,
  LineChart,
  BarChart,
  PieChart,
  RadarChart,
  DataZoomComponent,
  GraphicComponent,
  GridComponent,
  RadarComponent,
  TooltipComponent,
  LegendComponent,
])

const companyStore = useCompanyStore()
const { companies, loading: companiesLoading } = storeToRefs(companyStore)

const companyId = ref<number | null>(null)
const periods = ref<RatioPeriod[]>([])
const periodKey = ref<string>('')
const snapshot = ref<RatioSnapshot | null>(null)
const history = ref<RatioHistory | null>(null)
const loading = ref(false)
const trendTab = ref(TREND_TABS[0].key)
/** 当前 Tab 下用户勾选的对比指标（无上限） */
const selectedTrendKeys = ref<string[]>(defaultTrendKeysForTab(TREND_TABS[0].key))
const showAll = ref(false)
const showCompareTable = ref(false)
const viewerRole = ref<ViewerRole>('investor')
const roleProfile = computed(() => getRoleProfile(viewerRole.value))
const highlightedKey = ref<string | null>(null)
const exportingExcel = ref(false)

type TrendAxisMode = 'auto' | 'scale' | 'log' | 'custom'
type TrendValueMode = 'value' | 'index'
const trendAxisMode = ref<TrendAxisMode>('scale')
const trendValueMode = ref<TrendValueMode>('value')
const trendAxisMin = ref<number | undefined>(undefined)
const trendAxisMax = ref<number | undefined>(undefined)
const trendRightMin = ref<number | undefined>(undefined)
const trendRightMax = ref<number | undefined>(undefined)
/** 防止快速切换报告期时旧请求覆盖新结果 */
let snapshotLoadSeq = 0

const companyName = computed(
  () => companies.value.find((c) => c.id === companyId.value)?.name || '企业'
)

const periodOptions = computed(() =>
  periods.value.map((p) => ({
    value: `${p.year}|${p.period_type}|${p.quarter ?? ''}`,
    label:
      p.period_type === 'annual' ? `${p.year} 年报` : `${p.year} Q${p.quarter}`,
    raw: p,
  }))
)

const periodLabel = computed(() => {
  const opt = periodOptions.value.find((o) => o.value === periodKey.value)
  return opt?.label || '—'
})

const byKey = computed(() => {
  const m = new Map<string, RatioItem>()
  for (const r of snapshot.value?.ratios || []) m.set(r.key, r)
  return m
})

const primaryKpis = computed(() => {
  const period = snapshot.value?.period
    ? {
        year: snapshot.value.period.year,
        period_type: snapshot.value.period.period_type,
        quarter: snapshot.value.period.quarter ?? null,
      }
    : null
  return roleProfile.value.kpiKeys.map((key) => {
    const item = byKey.value.get(key)
    const value = item?.value ?? null
    const unit = item?.unit ?? 'ratio'
    const signal = evaluateSignal(key, value)
    const yoy = computeYoY(key, unit, value, history.value, period)
    return {
      key,
      name: item?.name || key,
      unit,
      value,
      signal,
      yoy,
      transition: formatTransition(yoy.prev, value, unit),
      variant: item?.variant,
      description: item?.description || '',
      reason: item?.reason,
      missing: item?.missing || [],
    }
  })
})

const summary = computed(() =>
  buildHealthSummary(companyName.value, periodLabel.value, snapshot.value, history.value)
)
const summaryBadge = computed(() => overallLabel(summary.value.overall))

const groupedRatios = computed(() => {
  const groups = new Map<string, RatioItem[]>()
  for (const r of snapshot.value?.ratios || []) {
    const list = groups.get(r.group) || []
    list.push(r)
    groups.set(r.group, list)
  }
  return Array.from(groups.entries()).map(([group, items]) => ({ group, items }))
})

const periodCompare = computed(() =>
  buildPeriodCompareRows(roleProfile.value.kpiKeys, snapshot.value, history.value)
)
const movers = computed(() => rankMovers(periodCompare.value.rows))
const compareNarrative = computed(() =>
  buildCompareNarrative(periodCompare.value, movers.value)
)

/** 结构环图：改善 / 需关注 / 持平；悬停列出具体指标名 */
const structureDonutOption = computed(() => {
  const rows = periodCompare.value.rows
  const groups: Record<'improve' | 'watch' | 'flat', PeriodCompareRow[]> = {
    improve: [],
    watch: [],
    flat: [],
  }
  for (const r of rows) {
    if (r.yoy.meaning === 'improve') groups.improve.push(r)
    else if (r.yoy.meaning === 'watch') groups.watch.push(r)
    else if (r.yoy.meaning === 'flat') groups.flat.push(r)
  }
  const slices = [
    {
      key: 'improve' as const,
      name: '改善',
      value: groups.improve.length,
      color: '#67c23a',
      items: groups.improve,
    },
    {
      key: 'watch' as const,
      name: '需关注',
      value: groups.watch.length,
      color: '#f56c6c',
      items: groups.watch,
    },
    {
      key: 'flat' as const,
      name: '持平',
      value: groups.flat.length,
      color: '#c0c4cc',
      items: groups.flat,
    },
  ].filter((s) => s.value > 0)
  if (!slices.length) return {}
  const total = slices.reduce((s, d) => s + d.value, 0)
  const data = slices.map((s) => ({
    name: s.name,
    value: s.value,
    itemStyle: { color: s.color },
    // 供 tooltip 使用
    items: s.items.map((r) => ({
      name: r.name,
      delta: r.yoy.deltaDisplay,
      transition: r.transition,
      level: r.signal.label,
    })),
  }))
  return {
    tooltip: {
      trigger: 'item',
      confine: true,
      extraCssText: 'max-width:280px;white-space:normal;line-height:1.5;',
      formatter: (p: {
        name?: string
        value?: number
        percent?: number
        data?: {
          items?: { name: string; delta: string; transition: string; level: string }[]
        }
      }) => {
        const items = p.data?.items || []
        const head = `<div style="font-weight:700;margin-bottom:4px">${p.name}：${p.value} 项（${p.percent?.toFixed(0)}%）</div>`
        if (!items.length) return head
        const list = items
          .map(
            (it) =>
              `<div style="margin:2px 0">· ${it.name} <span style="color:#909399">${it.delta}</span><br/><span style="color:#a0aec0;font-size:11px">${it.transition} · ${it.level}</span></div>`
          )
          .join('')
        return head + list
      },
    },
    series: [
      {
        type: 'pie',
        radius: ['42%', '72%'],
        center: ['50%', '48%'],
        avoidLabelOverlap: true,
        itemStyle: {
          borderRadius: 4,
          borderColor: '#fff',
          borderWidth: 2,
        },
        label: {
          formatter: '{b}\n{c}',
          fontSize: 12,
          color: '#606266',
          lineHeight: 16,
        },
        labelLine: { length: 10, length2: 8 },
        emphasis: {
          scale: true,
          scaleSize: 6,
          itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.12)' },
        },
        data,
      },
    ],
    graphic: [
      {
        type: 'text',
        left: 'center',
        top: '40%',
        style: {
          text: String(total),
          textAlign: 'center',
          fill: '#1f2d3d',
          fontSize: 26,
          fontWeight: 700,
        },
      },
      {
        type: 'text',
        left: 'center',
        top: '52%',
        style: {
          text: '核心指标',
          textAlign: 'center',
          fill: '#909399',
          fontSize: 12,
        },
      },
    ],
  }
})

/** 双向变动条：改善向右、需关注向左（业务语义轴） */
const divergingChangeOption = computed(() => {
  const rows = periodCompare.value.rows
    .map((r) => ({ row: r, v: semanticChangeValue(r) }))
    .filter((x) => x.v !== null && Math.abs(x.v as number) > 1e-9) as {
    row: PeriodCompareRow
    v: number
  }[]
  rows.sort((a, b) => a.v - b.v)
  if (!rows.length) return {}
  const names = rows.map((x) => x.row.name)
  const values = rows.map((x) => Number(x.v.toFixed(2)))
  return {
    animation: false,
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      confine: true,
      formatter: (params: unknown) => {
        const list = params as { dataIndex?: number }[]
        const idx = list[0]?.dataIndex ?? 0
        const r = rows[idx]?.row
        if (!r) return ''
        return [
          `<strong>${r.name}</strong>`,
          `${r.transition}`,
          `${r.yoy.meaningLabel} ${r.yoy.deltaDisplay}`,
          `水平：${r.signal.label}`,
        ].join('<br/>')
      },
    },
    grid: { left: 8, right: 64, top: 12, bottom: 20, containLabel: true },
    xAxis: {
      type: 'value',
      axisLabel: {
        fontSize: 11,
        formatter: (v: number) => (v === 0 ? '0' : `${v > 0 ? '+' : ''}${v}`),
      },
      splitLine: { lineStyle: { type: 'dashed', color: '#ebeef5' } },
    },
    yAxis: {
      type: 'category',
      data: names,
      axisLabel: {
        fontSize: 12,
        color: '#606266',
        width: 90,
        overflow: 'truncate',
      },
      axisTick: { show: false },
      axisLine: { show: false },
    },
    series: [
      {
        type: 'bar',
        data: values.map((v) => ({
          value: v,
          itemStyle: {
            color: v > 0 ? '#67c23a' : '#f56c6c',
            borderRadius: v > 0 ? [0, 4, 4, 0] : [4, 0, 0, 4],
          },
          label: { position: v >= 0 ? 'right' : 'left' },
        })),
        barMaxWidth: 18,
        barCategoryGap: '40%',
        label: {
          show: true,
          fontSize: 11,
          formatter: (p: { dataIndex?: number }) => {
            const r = rows[p.dataIndex ?? 0]?.row
            return r?.yoy.deltaDisplay || ''
          },
          color: '#606266',
        },
      },
    ],
  }
})

/** 上期 vs 本期 分组柱 */
const periodPairOption = computed(() => {
  const rows = periodCompare.value.rows.filter(
    (r) => r.previous !== null && r.current !== null
  )
  if (!rows.length) return {}
  const cats = rows.map((r) => r.name)
  const prev = rows.map((r) => toDisplayValue(r.previous, r.unit))
  const cur = rows.map((r) => toDisplayValue(r.current, r.unit))
  return {
    animation: false,
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      confine: true,
      formatter: (params: unknown) => {
        const list = params as {
          seriesName?: string
          value?: number | null
          dataIndex?: number
        }[]
        if (!list?.length) return ''
        const idx = list[0]?.dataIndex ?? 0
        const r = rows[idx]
        const head = r
          ? `${r.name}<br/>${r.transition}<br/>${r.yoy.meaningLabel} ${r.yoy.deltaDisplay}`
          : ''
        const lines = list
          .map((p) => {
            const unitHint = r?.unit === 'percent' ? '%' : '×'
            const v =
              p.value === null || p.value === undefined
                ? '—'
                : `${Number(p.value).toFixed(2)}${unitHint}`
            return `${p.seriesName}：${v}`
          })
          .join('<br/>')
        return `${head}<br/>${lines}`
      },
    },
    legend: {
      data: [
        periodCompare.value.previousLabel || '上期',
        periodCompare.value.currentLabel || '本期',
      ],
      top: 0,
      textStyle: { fontSize: 11 },
    },
    grid: { left: 16, right: 16, top: 40, bottom: 8, containLabel: true },
    xAxis: {
      type: 'category',
      data: cats,
      axisLabel: {
        fontSize: 11,
        interval: 0,
        rotate: cats.length > 5 ? 28 : 0,
        color: '#606266',
      },
    },
    yAxis: {
      type: 'value',
      scale: true,
      name: '展示值（% 或 倍）',
      nameTextStyle: { fontSize: 10, color: '#909399' },
      splitLine: { lineStyle: { type: 'dashed', color: '#ebeef5' } },
    },
    series: [
      {
        name: periodCompare.value.previousLabel || '上期',
        type: 'bar',
        data: prev,
        barMaxWidth: 24,
        itemStyle: { color: '#a0cfff', borderRadius: [3, 3, 0, 0] },
      },
      {
        name: periodCompare.value.currentLabel || '本期',
        type: 'bar',
        data: cur,
        barMaxWidth: 24,
        itemStyle: { color: '#409eff', borderRadius: [3, 3, 0, 0] },
      },
    ],
  }
})

const divergingChartHeight = computed(() => {
  const n = periodCompare.value.rows.filter(
    (r) => r.yoy.delta !== null && r.yoy.direction !== 'flat' && r.yoy.direction !== 'na'
  ).length
  return Math.min(480, Math.max(200, 48 + n * 40))
})

const trendCandidateKeys = computed(() => {
  return TREND_TABS.find((t) => t.key === trendTab.value)?.keys || []
})

const trendCandidateOptions = computed(() => {
  return trendCandidateKeys.value.map((key) => {
    const item = byKey.value.get(key)
    const series = history.value?.series[key]
    return {
      key,
      label: item?.name || series?.name || key,
      unit: (item?.unit || series?.unit || 'ratio') as 'ratio' | 'percent',
    }
  })
})

/** 实际绘图 keys：勾选 ∩ 当前 Tab 候选；若为空则回退默认 */
const activeTrendKeys = computed(() => {
  const allowed = new Set(trendCandidateKeys.value)
  const picked = selectedTrendKeys.value.filter((k) => allowed.has(k))
  if (picked.length) return picked
  return defaultTrendKeysForTab(trendTab.value)
})
const chartAxisHint = computed(() => {
  const h = history.value
  if (!h) return ''
  if (trendValueMode.value === 'index') {
    return '走势指数：各序列首个有效值=100，只比相对涨跌。'
  }
  const units = activeTrendKeys.value.map((k) => h.series[k]?.unit || 'ratio')
  const hasP = units.includes('percent')
  const hasR = units.includes('ratio')
  if (hasP && hasR) return '左轴为百分比，右轴为倍数；两轴刻度不可直接比高度。'
  if (hasP) return '单位：%'
  return '单位：倍数'
})

function resetTrendAxisCustom() {
  trendAxisMin.value = undefined
  trendAxisMax.value = undefined
  trendRightMin.value = undefined
  trendRightMax.value = undefined
}

function applyTrendNiceScale() {
  const h = history.value
  if (!h) return
  const vals: number[] = []
  for (const k of activeTrendKeys.value) {
    const s = h.series[k]
    if (!s) continue
    for (const pt of s.points) {
      if (pt.value === null || pt.value === undefined) continue
      if (trendValueMode.value === 'index') continue
      vals.push(s.unit === 'percent' ? pt.value * 100 : pt.value)
    }
  }
  // index mode: range around 100
  if (trendValueMode.value === 'index') {
    for (const k of activeTrendKeys.value) {
      const s = h.series[k]
      if (!s) continue
      const pts = [...s.points].reverse()
      const first = pts.find((p) => p.value !== null && p.value !== undefined)?.value
      if (first === null || first === undefined || first === 0) continue
      for (const pt of pts) {
        if (pt.value === null || pt.value === undefined) continue
        vals.push((Number(pt.value) / Number(first)) * 100)
      }
    }
  }
  if (!vals.length) {
    ElMessage.warning('当前序列无有效数值')
    return
  }
  const min = Math.min(...vals)
  const max = Math.max(...vals)
  const pad = (max - min) * 0.08 || Math.abs(max) * 0.05 || 1
  trendAxisMode.value = 'custom'
  trendAxisMin.value = Number((min - pad).toFixed(4))
  trendAxisMax.value = Number((max + pad).toFixed(4))
  ElMessage.success('已按所选指标写入 Y 轴范围')
}

const chartOption = computed(() => {
  const h = history.value
  if (!h) return {}
  const cats = (h.periods || [])
    .map((p) =>
      p.period_type === 'annual' ? `${p.year}` : `${p.year}Q${p.quarter}`
    )
    .reverse()
  const keys = activeTrendKeys.value
  const seriesMeta = keys
    .map((k) => h.series[k])
    .filter(Boolean)
    .map((s) => {
      const pts = [...s.points].reverse()
      const raw = pts.map((pt) => {
        if (pt.value === null || pt.value === undefined) return null
        return s.unit === 'percent'
          ? Number((pt.value * 100).toFixed(4))
          : Number(pt.value.toFixed(4))
      })
      let display = raw
      if (trendValueMode.value === 'index') {
        const first = raw.find((v) => v !== null && v !== undefined)
        if (first === null || first === undefined || first === 0) {
          display = raw.map(() => null)
        } else {
          display = raw.map((v) =>
            v === null || v === undefined
              ? null
              : Number(((v / first) * 100).toFixed(2))
          )
        }
      }
      return {
        key: s.key,
        name: s.name,
        unit: (s.unit || 'ratio') as 'ratio' | 'percent',
        raw,
        display,
      }
    })
  if (!seriesMeta.length) return {}

  const hasPercent = seriesMeta.some((s) => s.unit === 'percent')
  const hasRatio = seriesMeta.some((s) => s.unit === 'ratio')
  // 指数模式统一量纲，不拆双轴；原始值时 % 与倍数拆轴
  const mixedUnits =
    trendValueMode.value === 'value' && hasPercent && hasRatio
  const isLog =
    trendAxisMode.value === 'log' && trendValueMode.value === 'value'

  function buildAxis(
    side: 'left' | 'right',
    name: string
  ): Record<string, unknown> {
    const cMin = side === 'left' ? trendAxisMin.value : trendRightMin.value
    const cMax = side === 'left' ? trendAxisMax.value : trendRightMax.value
    const base: Record<string, unknown> = {
      type: isLog ? 'log' : 'value',
      name,
      nameTextStyle: { fontSize: 11, color: '#909399' },
      position: side,
      splitLine: side === 'left' ? { show: true } : { show: false },
    }
    if (trendAxisMode.value === 'scale' && !isLog) base.scale = true
    if (trendAxisMode.value === 'custom') {
      if (cMin !== undefined && cMin !== null && !Number.isNaN(cMin)) base.min = cMin
      if (cMax !== undefined && cMax !== null && !Number.isNaN(cMax)) base.max = cMax
    }
    if (isLog && cMin && cMin > 0) base.min = cMin
    return base
  }

  const yAxis = mixedUnits
    ? [
        buildAxis('left', '百分比 %'),
        buildAxis('right', '倍数'),
      ]
    : [
        buildAxis(
          'left',
          trendValueMode.value === 'index'
            ? '指数（首期=100）'
            : hasPercent
              ? '单位：%'
              : '单位：倍数'
        ),
      ]

  const series = seriesMeta.map((s) => ({
    name: s.name,
    type: 'line' as const,
    smooth: true,
    showSymbol: true,
    symbolSize: 6,
    yAxisIndex: mixedUnits ? (s.unit === 'percent' ? 0 : 1) : 0,
    data: s.display.map((v) => {
      if (v === null || v === undefined) return null
      if (isLog && v <= 0) return null
      return Number(v.toFixed(2))
    }),
  }))

  return {
    tooltip: {
      trigger: 'axis',
      formatter: (params: unknown) => {
        const list = params as {
          axisValue?: string
          seriesName?: string
          data?: number | null
          seriesIndex?: number
        }[]
        if (!Array.isArray(list) || !list.length) return ''
        const head = list[0]?.axisValue ?? ''
        const lines = list.map((p) => {
          const meta = seriesMeta[p.seriesIndex ?? 0]
          const idx = cats.indexOf(String(head))
          const disp =
            meta && idx >= 0 ? meta.display[idx] : p.data === undefined ? null : p.data
          const rawV = meta && idx >= 0 ? meta.raw[idx] : null
          if (trendValueMode.value === 'index') {
            const idxText =
              disp === null || disp === undefined ? '—' : Number(disp).toFixed(1)
            const rawText =
              rawV === null || rawV === undefined
                ? '—'
                : meta?.unit === 'percent'
                  ? `${Number(rawV).toFixed(2)}%`
                  : Number(rawV).toFixed(2)
            return `${p.seriesName}: <b>${idxText}</b> <span style="color:#909399">(原值 ${rawText})</span>`
          }
          const rawText =
            disp === null || disp === undefined
              ? '—'
              : meta?.unit === 'percent'
                ? `${Number(disp).toFixed(2)}%`
                : Number(disp).toFixed(2)
          return `${p.seriesName}: <b>${rawText}</b>`
        })
        return [`<div>${head}</div>`, ...lines].join('<br/>')
      },
    },
    legend: { type: 'scroll', data: series.map((s) => s.name), bottom: 0 },
    grid: {
      left: mixedUnits ? 52 : 48,
      right: mixedUnits ? 64 : 36,
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
      {
        type: 'inside',
        yAxisIndex: mixedUnits ? [0, 1] : [0],
        filterMode: 'none',
        zoomOnMouseWheel: 'shift',
        moveOnMouseMove: true,
      },
      {
        type: 'slider',
        yAxisIndex: mixedUnits ? [0, 1] : [0],
        width: 14,
        right: 4,
        top: 40,
        bottom: 58,
        brushSelect: false,
        showDetail: true,
      },
    ],
    xAxis: { type: 'category', data: cats, boundaryGap: false },
    yAxis,
    series,
  }
})

const radarAxes = computed(() => buildRadarAxes(snapshot.value))
const duPont = computed(() => buildDuPont(snapshot.value))

const radarOption = computed(() => {
  const axes = radarAxes.value
  if (!axes.length) return {}
  const values = axes.map((a) => (a.score === null ? 0 : a.score))
  const hasAny = axes.some((a) => a.score !== null)
  if (!hasAny) return {}
  return {
    tooltip: {
      trigger: 'item',
      formatter: () => {
        // radar tooltip varies; list all axes
        return axes
          .map((a) => `${a.name}：${a.score === null ? '—' : a.score + ' 分'}<br/><span style="color:#909399;font-size:12px">${a.detail}</span>`)
          .join('<br/>')
      },
    },
    radar: {
      indicator: axes.map((a) => ({ name: a.name, max: 100 })),
      radius: '62%',
      axisName: { color: '#606266', fontSize: 13 },
      splitArea: { areaStyle: { color: ['#fafafa', '#fff'] } },
    },
    series: [
      {
        type: 'radar',
        symbol: 'circle',
        symbolSize: 6,
        lineStyle: { width: 2, color: '#409eff' },
        areaStyle: { color: 'rgba(64,158,255,0.25)' },
        data: [{ value: values, name: periodLabel.value }],
      },
    ],
  }
})

const duPontBarsOption = computed(() => {
  const d = duPont.value
  const rows = [
    { name: '净利率', value: d.netMargin, unit: 'percent' as const },
    { name: '总资产周转率', value: d.assetTurnover, unit: 'ratio' as const },
    { name: '权益乘数', value: d.equityMultiplier, unit: 'ratio' as const },
  ]
  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (items: { name: string; data: number | null; dataIndex: number }[]) => {
        const it = items[0]
        if (!it) return ''
        const row = rows[it.dataIndex]
        if (!row || row.value === null) return `${it.name}：—`
        return `${row.name}：${formatRatioValue(row.value, row.unit)}`
      },
    },
    grid: { left: 100, right: 24, top: 16, bottom: 24 },
    xAxis: { type: 'value', scale: true },
    yAxis: {
      type: 'category',
      data: rows.map((r) => r.name),
      axisLabel: { fontSize: 12 },
    },
    series: [
      {
        type: 'bar',
        data: rows.map((r) =>
          r.value === null
            ? null
            : r.unit === 'percent'
              ? Number((r.value * 100).toFixed(2))
              : Number(r.value.toFixed(2))
        ),
        barWidth: 18,
        itemStyle: {
          color: (p: { dataIndex: number }) =>
            ['#67c23a', '#409eff', '#e6a23c'][p.dataIndex] || '#409eff',
          borderRadius: [0, 4, 4, 0],
        },
        label: {
          show: true,
          position: 'right',
          formatter: (p: { dataIndex: number; value: number | null }) => {
            const row = rows[p.dataIndex]
            if (!row || row.value === null) return '—'
            return formatRatioValue(row.value, row.unit)
          },
        },
      },
    ],
  }
})

function parsePeriodKey(key: string): {
  year: number
  period_type: PeriodType
  quarter: number | null
} | null {
  if (!key) return null
  const [y, pt, q] = key.split('|')
  return {
    year: Number(y),
    period_type: pt as PeriodType,
    quarter: q === '' || q === undefined ? null : Number(q),
  }
}

async function loadPeriods() {
  if (!companyId.value) {
    periods.value = []
    periodKey.value = ''
    snapshot.value = null
    history.value = null
    return
  }
  periods.value = await fetchRatioPeriods(companyId.value)
  if (!periods.value.length) {
    periodKey.value = ''
    snapshot.value = null
    history.value = null
    return
  }
  // 切换企业时：若当前 periodKey 仍有效则保留，否则默认最新一期
  const stillValid = periods.value.some(
    (p) => `${p.year}|${p.period_type}|${p.quarter ?? ''}` === periodKey.value
  )
  if (!stillValid) {
    const p = periods.value[0]
    periodKey.value = `${p.year}|${p.period_type}|${p.quarter ?? ''}`
  }
}

async function loadSnapshotAndHistory() {
  if (!companyId.value || !periodKey.value) {
    snapshot.value = null
    history.value = null
    return
  }
  const p = parsePeriodKey(periodKey.value)
  if (!p || Number.isNaN(p.year)) return
  const seq = ++snapshotLoadSeq
  const cid = companyId.value
  const key = periodKey.value
  loading.value = true
  try {
    const allKeys = [
      ...ROLE_PROFILES.flatMap((r) => [...r.kpiKeys]),
      ...TREND_TABS.flatMap((t) => t.keys),
    ]
    const uniq = Array.from(new Set(allKeys))
    const [snap, hist] = await Promise.all([
      fetchRatios(cid, p),
      fetchRatioHistory(cid, {
        period_type: p.period_type,
        keys: uniq,
      }),
    ])
    if (seq !== snapshotLoadSeq || companyId.value !== cid || periodKey.value !== key) {
      return
    }
    snapshot.value = snap
    history.value = hist
  } finally {
    if (seq === snapshotLoadSeq) loading.value = false
  }
}

function yoyClass(improved: boolean | null, direction: string): string {
  if (direction === 'flat' || direction === 'na') return 'yoy-flat'
  if (improved === true) return 'yoy-up'
  if (improved === false) return 'yoy-down'
  return 'yoy-flat'
}

function yoyArrow(direction: string): string {
  if (direction === 'up') return '↑'
  if (direction === 'down') return '↓'
  if (direction === 'flat') return '→'
  return ''
}

function meaningClass(meaning: string): string {
  if (meaning === 'improve') return 'meaning-improve'
  if (meaning === 'watch') return 'meaning-watch'
  return 'meaning-flat'
}

function focusMetric(key: string) {
  highlightedKey.value = highlightedKey.value === key ? null : key
}

function compareRowClassName({ row }: { row: PeriodCompareRow }): string {
  return highlightedKey.value === row.key ? 'row-highlight' : ''
}

function onCompareRowClick(row: PeriodCompareRow) {
  focusMetric(row.key)
}

function onDivergingClick(params: { name?: string }) {
  const name = params?.name
  if (!name) return
  const row = periodCompare.value.rows.find((r) => r.name === name)
  if (row) focusMetric(row.key)
}

function onPairClick(params: { name?: string }) {
  // category axis click may put name on axisValue via data; vue-echarts passes params
  const name = (params as { name?: string }).name
  // bar click: name is series; use dataIndex via full event if available
  const p = params as { name?: string; dataIndex?: number; componentType?: string }
  if (typeof p.dataIndex === 'number') {
    const rows = periodCompare.value.rows.filter(
      (r) => r.previous !== null && r.current !== null
    )
    const row = rows[p.dataIndex]
    if (row) focusMetric(row.key)
    return
  }
  if (name) {
    const row = periodCompare.value.rows.find((r) => r.name === name)
    if (row) focusMetric(row.key)
  }
}

function detailReason(item: RatioItem): string {
  if (item.value !== null && item.value !== undefined) return item.description
  if (item.reason === 'zero_denominator') return '分母为 0，无法计算'
  if (item.missing?.length) return `缺字段：${item.missing.join(', ')}`
  return item.reason || '无法计算'
}

function applyRoleDefaults(role: ViewerRole) {
  const p = getRoleProfile(role)
  trendTab.value = p.defaultTrendTab
  selectedTrendKeys.value = defaultTrendKeysForTab(p.defaultTrendTab)
  showAll.value = p.expandAll
  showCompareTable.value = role === 'pro'
}

function onRoleChange(role: ViewerRole) {
  viewerRole.value = role
  applyRoleDefaults(role)
}

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

function exportSnapshotHtml() {
  if (!snapshot.value) return
  const lines = summary.value.lines.map((l) => `<li>${escapeHtml(l)}</li>`).join('')
  const narrativeLines = compareNarrative.value.sublines
    .map((l) => `<li>${escapeHtml(l)}</li>`)
    .join('')
  const kpis = primaryKpis.value
    .map((k) => {
      const val = formatRatioValue(k.value, k.unit)
      const change = k.yoy.deltaDisplay
      const meaning = k.yoy.meaningLabel
      const path = k.yoy.prev !== null ? k.transition : '—'
      return `<tr><td>${escapeHtml(k.name)}</td><td>${escapeHtml(path)}</td><td>${val}</td><td>${escapeHtml(k.signal.label)}</td><td>${escapeHtml(meaning)} ${escapeHtml(change)}</td></tr>`
    })
    .join('')
  const allRows = (snapshot.value.ratios || [])
    .map((r) => {
      const sig = evaluateSignal(r.key, r.value)
      return `<tr><td>${escapeHtml(r.group)}</td><td>${escapeHtml(r.name)}</td><td>${formatRatioValue(r.value, r.unit)}</td><td>${escapeHtml(sig.label)}</td><td>${escapeHtml(r.description)}</td></tr>`
    })
    .join('')
  const html = `<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8"/><title>${escapeHtml(summary.value.title)} 财务快照</title>
<style>
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;padding:24px;color:#1f2d3d;max-width:900px;margin:0 auto}
h1{font-size:20px;margin:0 0 8px} .meta{color:#909399;font-size:12px;margin-bottom:16px}
ul{line-height:1.7} table{border-collapse:collapse;width:100%;margin:16px 0;font-size:13px}
th,td{border:1px solid #ebeef5;padding:8px;text-align:left} th{background:#f5f7fa}
.badge{display:inline-block;padding:2px 8px;border-radius:4px;background:#ecf5ff;color:#409eff;font-size:12px}
</style></head><body>
<h1>${escapeHtml(summary.value.title)}</h1>
<div class="meta">视图：${escapeHtml(roleProfile.value.label)} · 完整度 ${snapshot.value.summary.available}/${snapshot.value.summary.total} · 导出时间 ${new Date().toLocaleString()} · 非投资建议</div>
<p><span class="badge">${escapeHtml(summaryBadge.value.text)}</span></p>
<p>${escapeHtml(compareNarrative.value.headline)}</p>
<ul>${lines}${narrativeLines}</ul>
<h2>核心指标</h2>
<table><thead><tr><th>指标</th><th>上期→本期</th><th>本期</th><th>水平</th><th>变动</th></tr></thead><tbody>${kpis}</tbody></table>
<h2>全部比率</h2>
<table><thead><tr><th>分组</th><th>指标</th><th>数值</th><th>状态</th><th>说明</th></tr></thead><tbody>${allRows}</tbody></table>
<p style="color:#a0aec0;font-size:12px">本快照由 Web_Financial_Analyse 本地生成，阈值与评分为沟通辅助。</p>
</body></html>`
  const blob = new Blob([html], { type: 'text/html;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  const safe = `${companyName.value}_${periodLabel.value}_财务快照`.replace(/[\\/:*?"<>|]/g, '_')
  a.href = url
  a.download = `${safe}.html`
  a.click()
  URL.revokeObjectURL(url)
}

async function exportExcelWorkbook() {
  if (!companyId.value) {
    ElMessage.warning('请先选择企业')
    return
  }
  const p = parsePeriodKey(periodKey.value)
  exportingExcel.value = true
  try {
    // 导出当前期间类型下全部有数据年份（与 history 一致），不按单期裁剪
    const years = periods.value
      .filter((x) => x.period_type === (p?.period_type || 'annual'))
      .map((x) => x.year)
    const uniqYears = [...new Set(years)].sort((a, b) => a - b)
    await downloadCompanyExcel(companyId.value, {
      period_type: p?.period_type || 'annual',
      years: uniqYears.length ? uniqYears : undefined,
    })
    ElMessage.success('Excel 已开始下载（含三表与财务比率）')
  } catch {
    // http 拦截器已提示
  } finally {
    exportingExcel.value = false
  }
}

function printSnapshot() {
  showAll.value = true
  requestAnimationFrame(() => {
    setTimeout(() => window.print(), 80)
  })
}


watch(trendTab, (tab) => {
  selectedTrendKeys.value = defaultTrendKeysForTab(tab)
})

watch(companyId, async () => {
  await loadPeriods()
  await loadSnapshotAndHistory()
})

// 报告期下拉变更必须重新拉快照（此前缺失导致 UI 年份变了数据仍是首期）
watch(periodKey, async (key, prev) => {
  if (!key || key === prev) return
  await loadSnapshotAndHistory()
})

onMounted(async () => {
  applyRoleDefaults(viewerRole.value)
  await companyStore.load()
  if (companies.value.length) {
    companyId.value = companies.value[0].id
  }
})
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
      <!-- 健康摘要 -->
      <el-card class="summary-card" shadow="never">
        <div class="summary-head">
          <div>
            <div class="summary-title">{{ summary.title }}</div>
            <div class="summary-sub">
              {{ roleProfile.blurb }} · 规则阈值仅供参考，非投资建议
            </div>
          </div>
          <el-tag :type="summaryBadge.type" effect="dark" size="large">
            {{ summaryBadge.text }}
          </el-tag>
        </div>
        <ul class="summary-lines">
          <li v-for="(line, i) in summary.lines" :key="i">{{ line }}</li>
        </ul>
      </el-card>

      <!-- 核心 KPI（主读路径：含上期→本期） -->
      <div class="section-label">核心指标</div>
      <el-row :gutter="12" class="kpi-row">
        <el-col
          v-for="kpi in primaryKpis"
          :key="kpi.key"
          :xs="24"
          :sm="12"
          :md="8"
          :lg="4"
        >
          <el-card
            shadow="hover"
            class="kpi-card"
            :class="[
              'sig-' + kpi.signal.level,
              { 'kpi-highlight': highlightedKey === kpi.key },
            ]"
            @click="focusMetric(kpi.key)"
          >
            <div class="kpi-top">
              <span class="kpi-name">{{ kpi.name }}</span>
              <el-tag :type="kpi.signal.tagType" size="small" effect="light">
                {{ kpi.signal.label }}
              </el-tag>
            </div>
            <div class="kpi-value" :class="{ muted: kpi.value === null }">
              {{ formatRatioValue(kpi.value, kpi.unit) }}
            </div>
            <div v-if="kpi.yoy.prev !== null" class="kpi-transition">
              {{ kpi.transition }}
            </div>
            <div
              class="kpi-yoy"
              :class="yoyClass(kpi.yoy.improved, kpi.yoy.direction)"
            >
              <template v-if="kpi.yoy.direction !== 'na'">
                <span class="arrow">{{ yoyArrow(kpi.yoy.direction) }}</span>
                <span :class="meaningClass(kpi.yoy.meaning)">{{ kpi.yoy.meaningLabel }}</span>
                <span class="kpi-delta">{{ kpi.yoy.deltaDisplay }}</span>
                <span v-if="kpi.yoy.relChangeDisplay" class="kpi-rel">
                  ({{ kpi.yoy.relChangeDisplay }})
                </span>
              </template>
              <template v-else>
                <span class="yoy-flat">较上期 —</span>
              </template>
            </div>
            <div v-if="kpi.variant" class="kpi-variant">口径 {{ kpi.variant }}</div>
            <div v-else-if="kpi.value === null" class="kpi-variant">
              {{
                kpi.missing.length
                  ? '缺：' + kpi.missing.slice(0, 2).join(',')
                  : kpi.reason || '暂不可算'
              }}
            </div>
          </el-card>
        </el-col>
      </el-row>

      <!-- 较上期变动：图表模块 -->
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
                    @click="focusMetric(m.key)"
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
                    @click="focusMetric(m.key)"
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
                @click="onDivergingClick"
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
                @click="onPairClick"
              />
            </div>
          </div>

          <!-- 明细表：默认折叠 -->
          <div class="compare-table-toggle">
            <el-button text type="primary" @click="showCompareTable = !showCompareTable">
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
            @row-click="onCompareRowClick"
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

      <!-- 雷达 + 杜邦 -->
      <el-row
        v-if="roleProfile.showRadar || roleProfile.showDupont"
        :gutter="12"
        class="insight-row"
      >
        <el-col v-if="roleProfile.showRadar" :xs="24" :md="roleProfile.showDupont ? 12 : 24">
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
        <el-col v-if="roleProfile.showDupont" :xs="24" :md="roleProfile.showRadar ? 12 : 24">
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

      <!-- 分主题趋势 -->
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
              <el-button size="small" @click="applyTrendNiceScale">按所选填范围</el-button>
              <el-button size="small" text @click="resetTrendAxisCustom">清空</el-button>
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

      <!-- 全部指标（可折叠） -->
      <div class="all-toggle">
        <el-button text type="primary" @click="showAll = !showAll">
          {{ showAll ? '收起全部指标' : '展开全部指标与公式' }}
        </el-button>
      </div>
      <div v-show="showAll">
        <div v-for="block in groupedRatios" :key="block.group" class="group">
          <h3 class="group-title">{{ block.group }}</h3>
          <el-table :data="block.items" border stripe size="small" class="detail-table">
            <el-table-column prop="name" label="指标" min-width="120" />
            <el-table-column label="数值" width="110">
              <template #default="{ row }">
                <span :class="{ muted: row.value === null }">
                  {{ formatRatioValue(row.value, row.unit) }}
                </span>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="100">
              <template #default="{ row }">
                <el-tag
                  :type="evaluateSignal(row.key, row.value).tagType"
                  size="small"
                  effect="plain"
                >
                  {{ evaluateSignal(row.key, row.value).label }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="说明" min-width="200">
              <template #default="{ row }">
                <span class="table-desc">{{ detailReason(row) }}</span>
                <div v-if="row.variant" class="kpi-variant">{{ row.variant }}</div>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>
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
.summary-card {
  margin-bottom: 12px;
  border-radius: 8px;
  border: 1px solid #ebeef5;
}
.summary-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 10px;
}
.summary-title {
  font-size: 18px;
  font-weight: 700;
  color: #1f2d3d;
}
.summary-sub {
  margin-top: 4px;
  font-size: 12px;
  color: #909399;
}
.summary-lines {
  margin: 0;
  padding-left: 18px;
  color: #606266;
  line-height: 1.7;
  font-size: 13px;
}
.section-label {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  margin: 8px 4px 10px;
}
.section-label.inline {
  margin: 0;
}
.kpi-row {
  margin-bottom: 4px;
}
.kpi-card {
  margin-bottom: 12px;
  border-radius: 8px;
  border-top: 3px solid #dcdfe6;
  cursor: pointer;
  transition: box-shadow 0.15s ease, border-color 0.15s ease;
}
.kpi-card.sig-good {
  border-top-color: #67c23a;
}
.kpi-card.sig-watch {
  border-top-color: #e6a23c;
}
.kpi-card.sig-risk {
  border-top-color: #f56c6c;
}
.kpi-card.sig-na,
.kpi-card.sig-neutral {
  border-top-color: #c0c4cc;
}
.kpi-card.kpi-highlight {
  box-shadow: 0 0 0 2px #409eff inset;
}
.kpi-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 6px;
}
.kpi-name {
  font-size: 13px;
  color: #606266;
  font-weight: 500;
}
.kpi-value {
  font-size: 26px;
  font-weight: 700;
  color: #1f2d3d;
  margin: 10px 0 4px;
  letter-spacing: 0.02em;
}
.kpi-value.muted {
  color: #c0c4cc;
  font-size: 20px;
}
.kpi-transition {
  font-size: 12px;
  color: #909399;
  margin-bottom: 4px;
  font-variant-numeric: tabular-nums;
}
.kpi-yoy {
  font-size: 12px;
  font-weight: 600;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px;
}
.kpi-yoy .arrow {
  margin-right: 0;
}
.kpi-delta {
  font-variant-numeric: tabular-nums;
}
.kpi-rel {
  font-weight: 500;
  color: #a0aec0;
}
.kpi-variant {
  margin-top: 4px;
  font-size: 11px;
  color: #a0aec0;
  line-height: 1.3;
  word-break: break-all;
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
/* 顶部两栏：CSS grid，高度随内容，互不拉伸溢出 */
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
/* 结构：环图 + 芯片纵向填满，减少大块留白 */
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
.stat-chip.improve .stat-num { color: #67c23a; }
.stat-chip.watch .stat-num { color: #f56c6c; }
.stat-chip.flat .stat-num { color: #909399; }
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
.axis-chip.improve { color: #67c23a; background: #f0f9eb; }
.axis-chip.watch { color: #f56c6c; background: #fef0f0; }
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
/* 重点变动：两列均分，卡片填满列宽 */
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
.focus-col-title.improve { color: #67c23a; }
.focus-col-title.watch { color: #f56c6c; }
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
.focus-card.improve { border-left: 3px solid #67c23a; }
.focus-card.watch { border-left: 3px solid #f56c6c; }
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
.focus-badge.improve { color: #67c23a; background: #f0f9eb; }
.focus-badge.watch { color: #f56c6c; background: #fef0f0; }
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
.dumbbell-val.prev { color: #909399; text-align: right; }
.dumbbell-val.curr { color: #1f2d3d; text-align: left; }
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
.dumbbell-line.improve { background: #b3e19d; }
.dumbbell-line.watch { background: #fab6b6; }
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
.dumbbell-dot.curr.improve { background: #67c23a; }
.dumbbell-dot.curr.watch { background: #f56c6c; }
.focus-bar-track,
.table-bar-track {
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
.focus-bar-fill.improve { background: #67c23a; }
.focus-bar-fill.watch { background: #f56c6c; }
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
.table-bar-fill {
  height: 100%;
  border-radius: 3px;
  background: #909399;
  min-width: 4px;
}
.table-bar-fill.improve { background: #67c23a; }
.table-bar-fill.watch { background: #f56c6c; }
.table-bar-fill.flat,
.table-bar-fill.na { background: #c0c4cc; }
:deep(.row-highlight) > td {
  background: #ecf5ff !important;
}

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
.dupont-roe {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 8px;
}
.dupont-label {
  font-size: 13px;
  color: #606266;
}
.dupont-value {
  font-size: 28px;
  font-weight: 700;
  color: #1f2d3d;
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
.chart {
  height: 360px;
  width: 100%;
}
.all-toggle {
  text-align: center;
  padding: 8px 0 12px;
}
.group {
  background: #fff;
  padding: 12px 16px 16px;
  border-radius: 8px;
  margin-bottom: 12px;
}
.group-title {
  margin: 0 0 10px;
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}
.detail-table {
  width: 100%;
}
.table-desc {
  font-size: 12px;
  color: #909399;
}
.muted {
  color: #c0c4cc;
}
@media print {
  .no-print {
    display: none !important;
  }
  .analysis {
    background: #fff !important;
  }
  .kpi-card,
  .insight-card,
  .chart-card,
  .summary-card,
  .compare-card,
  .group {
    break-inside: avoid;
    box-shadow: none !important;
    border: 1px solid #ddd !important;
  }
  .chart,
  .radar-chart,
  .dupont-chart {
    break-inside: avoid;
  }
}

/* 趋势图 Y 轴控制与紧凑布局（对齐多期对比） */
.chart-host.trend-host {
  height: 360px;
  min-height: 360px;
}
.chart-host .chart {
  width: 100% !important;
  height: 100% !important;
  min-height: inherit;
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
.axis-row:last-child { margin-bottom: 0; }
.axis-label {
  font-size: 12px;
  color: #606266;
  white-space: nowrap;
}
.axis-num { width: 100px; }
.axis-panel kbd {
  display: inline-block;
  padding: 0 4px;
  border: 1px solid #dcdfe6;
  border-radius: 3px;
  background: #fff;
  font-size: 11px;
}
.kpi-card :deep(.el-card__body) { padding: 10px 12px; }
.summary-card :deep(.el-card__body) { padding: 12px 14px; }
</style>
