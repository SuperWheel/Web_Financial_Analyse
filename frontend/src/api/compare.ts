import http from './http'

export type PeriodType = 'annual' | 'quarterly'
export type StatementType = 'balance' | 'income' | 'cashflow'

export interface ComparePeriod {
  year: number
  period_type: PeriodType
  quarter: number | null
  has_balance: boolean
  has_income: boolean
  has_cashflow: boolean
}

export interface ComparePeriodMeta {
  year: number
  period_type: PeriodType
  quarter: number | null
  label: string
  statement_id: number | null
}

export interface CompareFieldRow {
  key: string
  label: string
  values: Array<number | null>
  deltas: Array<number | null>
  delta_pcts: Array<number | null>
  structure_pcts: Array<number | null>
}

export interface CompareGroup {
  key: string
  label: string
  rows: CompareFieldRow[]
}

export interface CompareMatrix {
  company_id: number
  statement_type: StatementType
  period_type: PeriodType
  base_field: string | null
  base_label: string | null
  periods: ComparePeriodMeta[]
  groups: CompareGroup[]
}

export async function fetchComparePeriods(
  companyId: number
): Promise<ComparePeriod[]> {
  const { data } = await http.get<ComparePeriod[]>(
    `/api/companies/${companyId}/compare-periods`
  )
  return data
}

export async function fetchCompare(
  companyId: number,
  params: {
    statement_type: StatementType
    period_type?: PeriodType
    years?: number[]
  }
): Promise<CompareMatrix> {
  const { data } = await http.get<CompareMatrix>(
    `/api/companies/${companyId}/compare`,
    {
      params: {
        statement_type: params.statement_type,
        period_type: params.period_type ?? 'annual',
        years: params.years?.length ? params.years.join(',') : undefined,
      },
    }
  )
  return data
}

/** 金额千分位；null → — */
export function formatAmount(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '—'
  return value.toLocaleString('zh-CN', {
    maximumFractionDigits: 2,
    minimumFractionDigits: 0,
  })
}

/** 变动率 / 结构占比 → 百分比文案（输入为 0–1 比例） */
export function formatPct(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '—'
  const pct = value * 100
  const sign = pct > 0 ? '+' : ''
  return `${sign}${pct.toFixed(1)}%`
}
