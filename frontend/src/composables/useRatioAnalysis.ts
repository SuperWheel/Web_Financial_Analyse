/** 比率分析页：企业/期间加载、快照/历史、KPI、变动、图表与导出 */
import { computed, onMounted, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
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

export type TrendAxisMode = 'auto' | 'scale' | 'log' | 'custom'
export type TrendValueMode = 'value' | 'index'

export function useRatioAnalysis() {
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

  return {
    ROLE_PROFILES,
    TREND_TABS,
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
    periodLabel,
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
    formatRatioValue,
    evaluateSignal,
  }
}
