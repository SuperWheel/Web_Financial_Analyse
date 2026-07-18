/** 导入核对：核心科目覆盖率聚合（纯函数，供 UI 与入库确认共用）。 */
import type { CoverageStats } from '@/api/importFiling'
import type { StatementKind } from '@/constants/statementFields'

export const STATEMENT_KINDS: StatementKind[] = ['balance', 'income', 'cashflow']

export const STATEMENT_KIND_LABEL: Record<StatementKind, string> = {
  balance: '资产负债表',
  income: '利润表',
  cashflow: '现金流量表',
}

export const UNMAPPED_REASON_LABEL: Record<string, string> = {
  no_alias_match: '无别名匹配',
  low_score: '匹配分过低',
  ambiguous: '多科目歧义',
  skip_total_cost: '跳过营业总成本',
}

export type CoverageRow = {
  kind: StatementKind
  label: string
  coreHit: number
  coreTotal: number
  mappedFields: number
  /** 0–100 */
  pct: number
}

export function buildCoverageRows(
  coverage: Record<string, CoverageStats> | null | undefined
): CoverageRow[] {
  const cov = coverage || {}
  return STATEMENT_KINDS.map((kind) => {
    const c = cov[kind] || {}
    const coreTotal = Number(c.core_total ?? 0)
    const coreHit = Number(c.core_hit ?? 0)
    const mappedFields = Number(c.mapped_fields ?? 0)
    const rate =
      typeof c.coverage === 'number' ? c.coverage : coreTotal ? coreHit / coreTotal : 0
    return {
      kind,
      label: STATEMENT_KIND_LABEL[kind],
      coreHit,
      coreTotal,
      mappedFields,
      pct: Math.round(Math.max(0, Math.min(1, rate)) * 100),
    }
  })
}

/** 三表合计核心覆盖 0–100；无 core_total 时返回 null */
export function overallCoveragePct(
  coverage: Record<string, CoverageStats> | null | undefined
): number | null {
  const rows = buildCoverageRows(coverage)
  const total = rows.reduce((s, r) => s + r.coreTotal, 0)
  if (!total) return null
  const hit = rows.reduce((s, r) => s + r.coreHit, 0)
  return Math.round((hit / total) * 100)
}

export function coverageTagType(pct: number): 'success' | 'warning' | 'danger' | 'info' {
  if (pct >= 80) return 'success'
  if (pct >= 50) return 'warning'
  if (pct > 0) return 'danger'
  return 'info'
}

export function unmappedReasonLabel(reason?: string): string {
  if (!reason) return '—'
  return UNMAPPED_REASON_LABEL[reason] || reason
}

export function statementKindLabel(kind?: string): string {
  if (!kind) return '—'
  if (kind in STATEMENT_KIND_LABEL) return STATEMENT_KIND_LABEL[kind as StatementKind]
  return kind
}

export function formatMoney(v: unknown): string {
  if (v === null || v === undefined || v === '') return '—'
  const n = Number(v)
  if (Number.isNaN(n)) return '—'
  return n.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

/** Excel 预览期间标签（避免模板内 TS 注解） */
export function formatPeriodLabels(
  periods: { label?: string }[] | null | undefined
): string {
  if (!periods?.length) return '—'
  return periods.map((p) => p.label || '—').join('、')
}
