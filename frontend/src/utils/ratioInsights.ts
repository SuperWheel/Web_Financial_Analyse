/** 比率展示：阈值、同比、健康摘要（前端规则，不改计算口径）。 */

import type { RatioHistory, RatioItem, RatioSnapshot } from '@/api/ratio'
import { formatRatioValue } from '@/api/ratio'

export type SignalLevel = 'good' | 'watch' | 'risk' | 'neutral' | 'na'

export interface SignalMeta {
  level: SignalLevel
  label: string
  /** Element Plus tag type */
  tagType: 'success' | 'warning' | 'danger' | 'info'
}

/** 越高越好 / 越低越好（在合理区间内） */
type Prefer = 'higher' | 'lower' | 'band'

interface ThresholdRule {
  prefer: Prefer
  /** good 边界 */
  good?: number
  /** watch 边界；越过则 risk */
  risk?: number
  /** band: [low, high] 内 good */
  band?: [number, number]
}

/** 数值均为小数口径（percent 类 0.4=40%）；ratio 类为倍数 */
const RULES: Record<string, ThresholdRule> = {
  current_ratio: { prefer: 'higher', good: 1.5, risk: 1.0 },
  quick_ratio: { prefer: 'higher', good: 1.0, risk: 0.8 },
  cash_ratio: { prefer: 'higher', good: 0.5, risk: 0.2 },
  debt_to_asset: { prefer: 'band', band: [0.2, 0.65], risk: 0.75 },
  equity_ratio: { prefer: 'band', band: [0.25, 0.8] },
  debt_to_equity: { prefer: 'lower', good: 1.0, risk: 2.0 },
  gross_margin: { prefer: 'higher', good: 0.25, risk: 0.1 },
  operating_margin: { prefer: 'higher', good: 0.08, risk: 0.0 },
  net_margin: { prefer: 'higher', good: 0.05, risk: 0.0 },
  roe: { prefer: 'higher', good: 0.1, risk: 0.0 },
  roa: { prefer: 'higher', good: 0.05, risk: 0.0 },
  asset_turnover: { prefer: 'higher', good: 0.5, risk: 0.2 },
  ocfr: { prefer: 'higher', good: 0.05, risk: 0.0 },
}

export const PRIMARY_KPI_KEYS = [
  'roe',
  'net_margin',
  'gross_margin',
  'debt_to_asset',
  'current_ratio',
  'ocfr',
] as const

export const TREND_TABS: { key: string; label: string; keys: string[] }[] = [
  {
    key: 'profit',
    label: '盈利',
    keys: ['gross_margin', 'operating_margin', 'net_margin', 'roe', 'roa'],
  },
  {
    key: 'solvency',
    label: '偿债',
    keys: ['current_ratio', 'quick_ratio', 'cash_ratio', 'debt_to_asset', 'debt_to_equity'],
  },
  {
    key: 'ops_cash',
    label: '营运与现金流',
    keys: ['asset_turnover', 'ocfr'],
  },
]

/** 各趋势 Tab 默认勾选的对比指标（切换 Tab 时重置） */
export const DEFAULT_TREND_SELECTION: Record<string, string[]> = {
  profit: ['gross_margin', 'net_margin'],
  solvency: ['current_ratio', 'debt_to_asset'],
  ops_cash: ['asset_turnover', 'ocfr'],
}

export function defaultTrendKeysForTab(tabKey: string): string[] {
  const tab = TREND_TABS.find((t) => t.key === tabKey)
  const defaults = DEFAULT_TREND_SELECTION[tabKey] || []
  if (!tab) return [...defaults]
  const allowed = new Set(tab.keys)
  const picked = defaults.filter((k) => allowed.has(k))
  return picked.length ? picked : tab.keys.slice(0, 2)
}

export type ViewerRole = 'manager' | 'investor' | 'pro'

export interface RoleProfile {
  key: ViewerRole
  label: string
  blurb: string
  kpiKeys: readonly string[]
  defaultTrendTab: string
  /** 专业视图默认展开全表 */
  expandAll: boolean
  showRadar: boolean
  showDupont: boolean
}

export const ROLE_PROFILES: RoleProfile[] = [
  {
    key: 'manager',
    label: '管理层',
    blurb: '关注偿债、流动性与经营现金流，快速识别经营风险',
    kpiKeys: ['current_ratio', 'quick_ratio', 'cash_ratio', 'debt_to_asset', 'ocfr', 'operating_margin'],
    defaultTrendTab: 'ops_cash',
    expandAll: false,
    showRadar: true,
    showDupont: false,
  },
  {
    key: 'investor',
    label: '投资人',
    blurb: '关注回报、利润率与杠杆，把握盈利质量与股东收益',
    kpiKeys: ['roe', 'roa', 'gross_margin', 'net_margin', 'debt_to_asset', 'asset_turnover'],
    defaultTrendTab: 'profit',
    expandAll: false,
    showRadar: true,
    showDupont: true,
  },
  {
    key: 'pro',
    label: '专业全量',
    blurb: '完整 13 项指标、公式与口径，适合复核与深入分析',
    kpiKeys: [
      'roe',
      'net_margin',
      'gross_margin',
      'debt_to_asset',
      'current_ratio',
      'ocfr',
    ],
    defaultTrendTab: 'profit',
    expandAll: true,
    showRadar: true,
    showDupont: true,
  },
]

export function getRoleProfile(role: ViewerRole): RoleProfile {
  return ROLE_PROFILES.find((r) => r.key === role) || ROLE_PROFILES[1]
}

export function evaluateSignal(key: string, value: number | null | undefined): SignalMeta {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return { level: 'na', label: '暂无', tagType: 'info' }
  }
  const rule = RULES[key]
  if (!rule) return { level: 'neutral', label: '—', tagType: 'info' }

  if (rule.prefer === 'band' && rule.band) {
    const [lo, hi] = rule.band
    if (value >= lo && value <= hi) return { level: 'good', label: '稳健', tagType: 'success' }
    if (rule.risk !== undefined && value > rule.risk)
      return { level: 'risk', label: '偏高风险', tagType: 'danger' }
    if (value < lo) return { level: 'watch', label: '偏低关注', tagType: 'warning' }
    return { level: 'watch', label: '偏离关注', tagType: 'warning' }
  }

  if (rule.prefer === 'higher') {
    if (rule.good !== undefined && value >= rule.good)
      return { level: 'good', label: '较好', tagType: 'success' }
    if (rule.risk !== undefined && value < rule.risk)
      return { level: 'risk', label: '偏弱', tagType: 'danger' }
    return { level: 'watch', label: '一般', tagType: 'warning' }
  }

  // lower better
  if (rule.good !== undefined && value <= rule.good)
    return { level: 'good', label: '可控', tagType: 'success' }
  if (rule.risk !== undefined && value >= rule.risk)
    return { level: 'risk', label: '偏高', tagType: 'danger' }
  return { level: 'watch', label: '关注', tagType: 'warning' }
}

/** 对「越高越好」的指标，上升为改善；资产负债率等越低越好则相反 */
function improvementPrefer(key: string): Prefer {
  return RULES[key]?.prefer ?? 'higher'
}

export type ChangeMeaning = 'improve' | 'watch' | 'flat' | 'na'

export interface YoYInfo {
  prev: number | null
  delta: number | null
  /** 绝对变动展示：+2.8pp / +0.15× / 持平 / — */
  deltaDisplay: string
  /** 相对上期变动（|prev| 足够大时），如 +10.7%；否则 null */
  relChangeDisplay: string | null
  direction: 'up' | 'down' | 'flat' | 'na'
  /** 从业务语义看是否改善 */
  improved: boolean | null
  /** 业务含义：改善 / 需关注 / 持平 / — */
  meaning: ChangeMeaning
  meaningLabel: string
  /** 对比所用上期标签，如 2023 年报 */
  previousPeriodLabel: string | null
}

export type PeriodRef = {
  year: number
  period_type: 'annual' | 'quarterly' | string
  quarter?: number | null
}

type HistoryValuePoint = PeriodRef & { value: number }

function emptyYoY(): YoYInfo {
  return {
    prev: null,
    delta: null,
    deltaDisplay: '—',
    relChangeDisplay: null,
    direction: 'na',
    improved: null,
    meaning: 'na',
    meaningLabel: '—',
    previousPeriodLabel: null,
  }
}

function periodPointLabel(pt: PeriodRef): string {
  return pt.period_type === 'annual'
    ? `${pt.year} 年报`
    : `${pt.year} Q${pt.quarter}`
}


/** 时间序：年 → 季；用于找「当前期之前」的一期 */
function periodRank(p: PeriodRef): number {
  return p.year * 10 + (p.quarter ?? 0)
}

/**
 * 在 history 点中找相对 currentPeriod 的上一期（严格更早，且有值）。
 * 年报：通常即「本年的前一年」；若缺数年则回退到更早有数的一期。
 * 不再使用「全局最新的前一期」（会把未来年误当上期）。
 */
function findPreviousHistoryPoint(
  points: Array<PeriodRef & { value: number | null | undefined }>,
  currentPeriod: PeriodRef
): HistoryValuePoint | null {
  const withVal: HistoryValuePoint[] = []
  for (const p of points) {
    if (p.value === null || p.value === undefined || Number.isNaN(Number(p.value))) continue
    withVal.push({ ...p, value: Number(p.value) })
  }
  if (!withVal.length) return null

  const curRank = periodRank(currentPeriod)
  // 只要严格早于当前报告期的点，取其中最晚一期（即紧邻上期）
  const earlier = withVal
    .filter((p) => periodRank(p) < curRank)
    .sort((a, b) => periodRank(a) - periodRank(b))

  if (!earlier.length) return null
  return earlier[earlier.length - 1]
}

function formatDeltaDisplay(unit: 'ratio' | 'percent', delta: number): string {
  if (Math.abs(delta) < 1e-9) return '持平'
  if (unit === 'percent') {
    const pct = delta * 100
    return `${pct > 0 ? '+' : ''}${pct.toFixed(1)}pp`
  }
  return `${delta > 0 ? '+' : ''}${delta.toFixed(2)}×`
}

function formatRelChange(prev: number, delta: number): string | null {
  if (Math.abs(prev) < 1e-6) return null
  if (Math.abs(delta) < 1e-9) return null
  const rel = (delta / Math.abs(prev)) * 100
  if (!Number.isFinite(rel) || Math.abs(rel) > 9999) return null
  return `${rel > 0 ? '+' : ''}${rel.toFixed(1)}%`
}

function meaningFromImproved(
  improved: boolean | null,
  direction: YoYInfo['direction']
): { meaning: ChangeMeaning; meaningLabel: string } {
  if (direction === 'na') return { meaning: 'na', meaningLabel: '—' }
  if (direction === 'flat') return { meaning: 'flat', meaningLabel: '持平' }
  if (improved === true) return { meaning: 'improve', meaningLabel: '改善' }
  if (improved === false) return { meaning: 'watch', meaningLabel: '需关注' }
  // band 等无明确好坏：只标方向
  if (direction === 'up') return { meaning: 'flat', meaningLabel: '上升' }
  if (direction === 'down') return { meaning: 'flat', meaningLabel: '下降' }
  return { meaning: 'flat', meaningLabel: '持平' }
}

export function computeYoY(
  key: string,
  unit: 'ratio' | 'percent',
  current: number | null | undefined,
  history: RatioHistory | null,
  /** 当前选中的报告期；必须传入，否则无法正确定位「前一年」 */
  currentPeriod?: PeriodRef | null
): YoYInfo {
  const empty = emptyYoY()
  if (current === null || current === undefined || !history?.series[key]) return empty

  const points = history.series[key].points || []
  let prevPoint: HistoryValuePoint | null = null

  if (currentPeriod) {
    prevPoint = findPreviousHistoryPoint(points, currentPeriod)
  } else {
    // 无报告期时退化为：有值序列按时间升序的最后两期（避免误用「最新全局」）
    const withVal: HistoryValuePoint[] = []
    for (const p of points) {
      if (p.value === null || p.value === undefined || Number.isNaN(Number(p.value))) continue
      withVal.push({ ...p, value: Number(p.value) })
    }
    withVal.sort((a, b) => periodRank(a) - periodRank(b))
    if (withVal.length < 2) return empty
    prevPoint = withVal[withVal.length - 2]
  }

  if (!prevPoint) return empty
  const prevV = Number(prevPoint.value)
  const cur = current
  const delta = cur - prevV
  const prefer = improvementPrefer(key)
  const previousPeriodLabel = periodPointLabel(prevPoint)

  if (Math.abs(delta) < 1e-9) {
    return {
      prev: prevV,
      delta: 0,
      deltaDisplay: '持平',
      relChangeDisplay: null,
      direction: 'flat',
      improved: null,
      meaning: 'flat',
      meaningLabel: '持平',
      previousPeriodLabel,
    }
  }

  let improved: boolean | null = null
  if (prefer === 'higher') improved = delta > 0
  else if (prefer === 'lower') improved = delta < 0
  else improved = null

  const direction: YoYInfo['direction'] = delta > 0 ? 'up' : 'down'
  const { meaning, meaningLabel } = meaningFromImproved(improved, direction)

  return {
    prev: prevV,
    delta,
    deltaDisplay: formatDeltaDisplay(unit, delta),
    relChangeDisplay: formatRelChange(prevV, delta),
    direction,
    improved,
    meaning,
    meaningLabel,
    previousPeriodLabel,
  }
}

/** 上期 → 本期 展示串 */
export function formatTransition(
  previous: number | null | undefined,
  current: number | null | undefined,
  unit: 'ratio' | 'percent'
): string {
  if (previous === null || previous === undefined) {
    return `${formatRatioValue(current, unit)}`
  }
  return `${formatRatioValue(previous, unit)} → ${formatRatioValue(current, unit)}`
}

/** 图表展示值：percent → 百分点数值，ratio → 倍数 */
export function toDisplayValue(
  value: number | null | undefined,
  unit: 'ratio' | 'percent'
): number | null {
  if (value === null || value === undefined || Number.isNaN(value)) return null
  return unit === 'percent' ? Number((value * 100).toFixed(4)) : Number(value.toFixed(4))
}

/** 图表用绝对变动：percent → pp，ratio → 倍数差 */
export function toDisplayDelta(
  delta: number | null | undefined,
  unit: 'ratio' | 'percent'
): number | null {
  if (delta === null || delta === undefined || Number.isNaN(delta)) return null
  return unit === 'percent' ? Number((delta * 100).toFixed(4)) : Number(delta.toFixed(4))
}

/**
 * 语义条形值：改善为正、需关注为负（与涨跌方向解耦）。
 * 便于「谁变好/变差」一眼扫读。
 */
export function semanticChangeValue(row: PeriodCompareRow): number | null {
  const d = toDisplayDelta(row.yoy.delta, row.unit)
  if (d === null) return null
  if (row.yoy.meaning === 'improve') return Math.abs(d)
  if (row.yoy.meaning === 'watch') return -Math.abs(d)
  return 0
}

export interface PeriodCompareRow {
  key: string
  name: string
  unit: 'ratio' | 'percent'
  current: number | null
  previous: number | null
  previousLabel: string
  currentLabel: string
  yoy: YoYInfo
  signal: SignalMeta
  /** 上期 → 本期 */
  transition: string
  /** 组内 |delta| 归一化 0–100，供条形宽度 */
  barPct: number
}

export interface PeriodCompareResult {
  rows: PeriodCompareRow[]
  /** 按 |delta| 降序 */
  rowsByMagnitude: PeriodCompareRow[]
  previousLabel: string
  currentLabel: string
  hasPrevious: boolean
  counts: { improve: number; watch: number; flat: number; na: number }
}


/** 本期 vs 上期：上期 = 当前选中报告期之前最近一期（年报即前一年）。 */
export function buildPeriodCompareRows(
  keys: readonly string[],
  snapshot: RatioSnapshot | null,
  history: RatioHistory | null
): PeriodCompareResult {
  const empty: PeriodCompareResult = {
    rows: [],
    rowsByMagnitude: [],
    previousLabel: '',
    currentLabel: '',
    hasPrevious: false,
    counts: { improve: 0, watch: 0, flat: 0, na: 0 },
  }
  if (!snapshot) return empty

  const map = Object.fromEntries(snapshot.ratios.map((r) => [r.key, r])) as Record<
    string,
    RatioItem
  >
  const currentPeriod: PeriodRef = {
    year: snapshot.period.year,
    period_type: snapshot.period.period_type,
    quarter: snapshot.period.quarter ?? null,
  }
  const currentLabel = periodPointLabel(currentPeriod)

  let previousLabel = '上期'
  let hasPrevious = false

  const rawRows: Omit<PeriodCompareRow, 'barPct'>[] = keys.map((key) => {
    const item = map[key]
    const unit = item?.unit || 'ratio'
    const current = item?.value ?? null
    const yoy = computeYoY(key, unit, current, history, currentPeriod)
    if (yoy.prev !== null) hasPrevious = true
    if (yoy.previousPeriodLabel) previousLabel = yoy.previousPeriodLabel
    return {
      key,
      name: item?.name || key,
      unit,
      current,
      previous: yoy.prev,
      previousLabel: yoy.previousPeriodLabel || previousLabel,
      currentLabel,
      yoy,
      signal: evaluateSignal(key, current),
      transition: formatTransition(yoy.prev, current, unit),
    }
  })

  const maxAbs = Math.max(
    0,
    ...rawRows.map((r) => (r.yoy.delta !== null ? Math.abs(r.yoy.delta) : 0))
  )
  const rows: PeriodCompareRow[] = rawRows.map((r) => ({
    ...r,
    barPct:
      maxAbs > 0 && r.yoy.delta !== null
        ? Math.max(6, Math.round((Math.abs(r.yoy.delta) / maxAbs) * 100))
        : 0,
  }))

  const rowsByMagnitude = [...rows].sort((a, b) => {
    const da = a.yoy.delta !== null ? Math.abs(a.yoy.delta) : -1
    const db = b.yoy.delta !== null ? Math.abs(b.yoy.delta) : -1
    return db - da
  })

  const counts = { improve: 0, watch: 0, flat: 0, na: 0 }
  for (const r of rows) {
    if (r.yoy.meaning === 'improve') counts.improve += 1
    else if (r.yoy.meaning === 'watch') counts.watch += 1
    else if (r.yoy.meaning === 'flat') counts.flat += 1
    else counts.na += 1
  }

  return { rows, rowsByMagnitude, previousLabel, currentLabel, hasPrevious, counts }
}

export interface RankedMovers {
  improved: PeriodCompareRow[]
  worsened: PeriodCompareRow[]
  /** 别名：需关注（与 worsened 相同） */
  watch: PeriodCompareRow[]
}

/** 改善 Top / 需关注 Top（按 |delta| 排序）。 */
export function rankMovers(rows: PeriodCompareRow[], topN = 3): RankedMovers {
  const withDelta = rows.filter((r) => r.yoy.delta !== null && r.yoy.direction !== 'flat')
  const improved = withDelta
    .filter((r) => r.yoy.improved === true)
    .sort((a, b) => Math.abs(b.yoy.delta || 0) - Math.abs(a.yoy.delta || 0))
    .slice(0, topN)
  const worsened = withDelta
    .filter((r) => r.yoy.improved === false)
    .sort((a, b) => Math.abs(b.yoy.delta || 0) - Math.abs(a.yoy.delta || 0))
    .slice(0, topN)
  return { improved, worsened, watch: worsened }
}

export interface CompareNarrative {
  headline: string
  sublines: string[]
  topImprove: PeriodCompareRow | null
  topWatch: PeriodCompareRow | null
}

/** 结论条文案：相对上期整体情况 + 最大改善/关注。 */
export function buildCompareNarrative(
  compare: PeriodCompareResult,
  movers: RankedMovers
): CompareNarrative {
  if (!compare.hasPrevious) {
    return {
      headline: '当前仅有一期数据，录入更多报告期后可看变动',
      sublines: [],
      topImprove: null,
      topWatch: null,
    }
  }
  const { counts, previousLabel } = compare
  const headline = `相对 ${previousLabel}：改善 ${counts.improve} · 需关注 ${counts.watch} · 持平 ${counts.flat}`
  const sublines: string[] = []
  const topImprove = movers.improved[0] || null
  const topWatch = movers.watch[0] || null
  if (topImprove) {
    sublines.push(
      `最大改善：${topImprove.name} ${topImprove.yoy.deltaDisplay}（${topImprove.transition}）`
    )
  }
  if (topWatch) {
    const levelHint =
      topWatch.signal.level === 'risk' || topWatch.signal.level === 'watch'
        ? `，水平${topWatch.signal.label}`
        : ''
    sublines.push(
      `最大关注：${topWatch.name} ${topWatch.yoy.deltaDisplay}（${topWatch.transition}${levelHint}）`
    )
  }
  if (!topImprove && !topWatch && counts.flat > 0) {
    sublines.push('核心指标较上期整体变动不大')
  }
  return { headline, sublines, topImprove, topWatch }
}

export function buildHealthSummary(
  companyName: string,
  periodLabel: string,
  snapshot: RatioSnapshot | null,
  history: RatioHistory | null
): { title: string; lines: string[]; overall: SignalLevel } {
  if (!snapshot) {
    return { title: companyName, lines: ['暂无比率数据'], overall: 'na' }
  }
  const byKey = Object.fromEntries(snapshot.ratios.map((r) => [r.key, r])) as Record<
    string,
    RatioItem
  >
  const lines: string[] = []
  const signals = PRIMARY_KPI_KEYS.map((k) => ({
    key: k,
    item: byKey[k],
    signal: evaluateSignal(k, byKey[k]?.value),
  }))

  const goods = signals.filter((s) => s.signal.level === 'good')
  const risks = signals.filter((s) => s.signal.level === 'risk')
  const watches = signals.filter((s) => s.signal.level === 'watch')

  // 盈利一句
  const gm = byKey.gross_margin
  const nm = byKey.net_margin
  const roe = byKey.roe
  if (gm?.value != null || nm?.value != null || roe?.value != null) {
    const parts: string[] = []
    if (gm?.value != null) parts.push(`毛利率 ${formatRatioValue(gm.value, 'percent')}`)
    if (nm?.value != null) parts.push(`净利率 ${formatRatioValue(nm.value, 'percent')}`)
    if (roe?.value != null) parts.push(`ROE ${formatRatioValue(roe.value, 'percent')}`)
    const tone =
      evaluateSignal('roe', roe?.value).level === 'good' ||
      evaluateSignal('net_margin', nm?.value).level === 'good'
        ? '盈利能力整体较好'
        : evaluateSignal('roe', roe?.value).level === 'risk'
          ? '盈利能力偏弱'
          : '盈利能力中性'
    lines.push(`${tone}：${parts.join('，')}。`)
  }

  // 偿债一句
  const da = byKey.debt_to_asset
  const cr = byKey.current_ratio
  if (da?.value != null || cr?.value != null) {
    const parts: string[] = []
    if (da?.value != null) parts.push(`资产负债率 ${formatRatioValue(da.value, 'percent')}`)
    if (cr?.value != null) parts.push(`流动比率 ${formatRatioValue(cr.value, 'ratio')}`)
    const riskDebt = evaluateSignal('debt_to_asset', da?.value).level === 'risk'
    const riskLiq = evaluateSignal('current_ratio', cr?.value).level === 'risk'
    const tone = riskDebt || riskLiq ? '偿债与杠杆需关注' : '偿债结构相对稳健'
    lines.push(`${tone}：${parts.join('，')}。`)
  }

  // 现金流一句
  const ocfr = byKey.ocfr
  if (ocfr?.value != null) {
    const period: PeriodRef = {
      year: snapshot.period.year,
      period_type: snapshot.period.period_type,
      quarter: snapshot.period.quarter ?? null,
    }
    const yoy = computeYoY('ocfr', 'percent', ocfr.value, history, period)
    let extra = ''
    if (yoy.improved === false) extra = '；较上期走弱'
    else if (yoy.improved === true) extra = '；较上期改善'
    if (ocfr.value < 0) {
      lines.push(
        `经营现金流/营收为 ${formatRatioValue(ocfr.value, 'percent')}，利润含金量需警惕${extra}。`
      )
    } else {
      lines.push(
        `经营现金流/营收 ${formatRatioValue(ocfr.value, 'percent')}${extra || '，现金流与收入匹配尚可'}。`
      )
    }
  }

  // 完整度
  const { available, total } = snapshot.summary
  lines.push(`数据完整度：${available}/${total} 项可计算。`)

  if (risks.length) {
    lines.push(`风险提示：${risks.map((r) => r.item?.name || r.key).join('、')} 处于偏弱区间。`)
  } else if (watches.length && goods.length < 3) {
    lines.push(`关注项：${watches.map((r) => r.item?.name || r.key).join('、')}。`)
  }

  let overall: SignalLevel = 'neutral'
  if (risks.length >= 2) overall = 'risk'
  else if (risks.length === 1) overall = 'watch'
  else if (goods.length >= 4) overall = 'good'
  else if (goods.length >= 2) overall = 'good'
  else overall = 'watch'

  return {
    title: `${companyName} · ${periodLabel}`,
    lines,
    overall,
  }
}

export function overallLabel(level: SignalLevel): { text: string; type: SignalMeta['tagType'] } {
  switch (level) {
    case 'good':
      return { text: '整体稳健', type: 'success' }
    case 'risk':
      return { text: '风险偏高', type: 'danger' }
    case 'watch':
      return { text: '需要关注', type: 'warning' }
    default:
      return { text: '待评估', type: 'info' }
  }
}

/** 将指标映射到 0–100 沟通分（非精确估值）。 */
export function scoreRatio(key: string, value: number | null | undefined): number | null {
  if (value === null || value === undefined || Number.isNaN(value)) return null
  const rule = RULES[key]
  if (!rule) return null

  if (rule.prefer === 'higher') {
    const good = rule.good ?? 1
    const risk = rule.risk ?? 0
    if (value >= good) return Math.min(100, 80 + ((value - good) / Math.max(good, 0.01)) * 20)
    if (value <= risk) return Math.max(0, (value / Math.max(risk, 0.01)) * 40)
    const t = (value - risk) / Math.max(good - risk, 0.01)
    return 40 + t * 40
  }

  if (rule.prefer === 'lower') {
    const good = rule.good ?? 1
    const risk = rule.risk ?? 2
    if (value <= good) return Math.min(100, 85 + ((good - value) / Math.max(good, 0.01)) * 15)
    if (value >= risk) return Math.max(0, 40 - ((value - risk) / Math.max(risk, 0.01)) * 40)
    const t = (risk - value) / Math.max(risk - good, 0.01)
    return 40 + t * 45
  }

  // band：区间中心最高
  if (rule.band) {
    const [lo, hi] = rule.band
    const mid = (lo + hi) / 2
    const half = (hi - lo) / 2 || 0.1
    if (value >= lo && value <= hi) {
      const dist = Math.abs(value - mid) / half
      return 100 - dist * 20
    }
    if (value < lo) {
      const dist = (lo - value) / Math.max(lo, 0.05)
      return Math.max(0, 55 - dist * 40)
    }
    const dist = (value - hi) / Math.max(hi, 0.05)
    return Math.max(0, 55 - dist * 50)
  }
  return 50
}

export interface RadarAxis {
  key: string
  name: string
  score: number | null
  detail: string
}

const RADAR_GROUPS: { key: string; name: string; keys: string[] }[] = [
  { key: 'solvency', name: '偿债', keys: ['current_ratio', 'quick_ratio', 'debt_to_asset'] },
  { key: 'profit', name: '盈利', keys: ['gross_margin', 'net_margin', 'roe'] },
  { key: 'ops', name: '营运', keys: ['asset_turnover', 'roa'] },
  { key: 'cash', name: '现金流', keys: ['ocfr'] },
]

export function buildRadarAxes(snapshot: RatioSnapshot | null): RadarAxis[] {
  if (!snapshot) return []
  const map = Object.fromEntries(snapshot.ratios.map((r) => [r.key, r])) as Record<
    string,
    RatioItem
  >
  return RADAR_GROUPS.map((g) => {
    const scores: number[] = []
    const parts: string[] = []
    for (const k of g.keys) {
      const item = map[k]
      const s = scoreRatio(k, item?.value)
      if (s !== null) {
        scores.push(s)
        parts.push(
          `${item?.name || k} ${formatRatioValue(item?.value ?? null, item?.unit || 'ratio')}`
        )
      }
    }
    const score =
      scores.length === 0
        ? null
        : Math.round(scores.reduce((a, b) => a + b, 0) / scores.length)
    return {
      key: g.key,
      name: g.name,
      score,
      detail: parts.join('；') || '数据不足',
    }
  })
}

export interface DuPontBreakdown {
  /** 展示用 ROE（优先接口 roe） */
  roe: number | null
  netMargin: number | null
  assetTurnover: number | null
  /** 权益乘数 = 1 / 权益比率，约等于 资产/权益 */
  equityMultiplier: number | null
  /** 三因子乘积，用于核对 */
  product: number | null
  /** 与 roe 的相对误差 */
  gapPct: number | null
  note: string
}

export function buildDuPont(snapshot: RatioSnapshot | null): DuPontBreakdown {
  const empty: DuPontBreakdown = {
    roe: null,
    netMargin: null,
    assetTurnover: null,
    equityMultiplier: null,
    product: null,
    gapPct: null,
    note: '缺少净利率、周转率或权益结构，无法拆解',
  }
  if (!snapshot) return empty
  const map = Object.fromEntries(snapshot.ratios.map((r) => [r.key, r.value])) as Record<
    string,
    number | null
  >
  const netMargin = map.net_margin ?? null
  const assetTurnover = map.asset_turnover ?? null
  const equityRatio = map.equity_ratio ?? null
  const debtToEquity = map.debt_to_equity ?? null
  let equityMultiplier: number | null = null
  if (equityRatio !== null && equityRatio !== 0) {
    equityMultiplier = 1 / equityRatio
  } else if (debtToEquity !== null) {
    equityMultiplier = 1 + debtToEquity
  }
  const roe = map.roe ?? null
  if (netMargin === null || assetTurnover === null || equityMultiplier === null) {
    return { ...empty, roe, netMargin, assetTurnover, equityMultiplier }
  }
  const product = netMargin * assetTurnover * equityMultiplier
  let gapPct: number | null = null
  if (roe !== null && Math.abs(roe) > 1e-9) {
    gapPct = ((product - roe) / Math.abs(roe)) * 100
  }
  return {
    roe,
    netMargin,
    assetTurnover,
    equityMultiplier,
    product,
    gapPct,
    note:
      gapPct !== null && Math.abs(gapPct) > 8
        ? '三因子乘积与 ROE 有偏差（归母口径或缺字段），以 ROE 卡片为准'
        : 'ROE ≈ 净利率 × 总资产周转率 × 权益乘数',
  }
}
