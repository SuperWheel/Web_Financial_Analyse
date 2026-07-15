import http from './http'

export type PeriodType = 'annual' | 'quarterly'

export interface RatioPeriod {
  year: number
  period_type: PeriodType
  quarter: number | null
  has_balance: boolean
  has_income: boolean
  has_cashflow: boolean
}

export interface RatioItem {
  key: string
  name: string
  group: string
  unit: 'ratio' | 'percent'
  description: string
  formula: string
  value: number | null
  missing: string[]
  reason: string | null
  variant?: string | null
}

export interface RatioSnapshot {
  company_id: number
  period: {
    year: number
    period_type: PeriodType
    quarter: number | null
  }
  sources: {
    balance_sheet_id: number | null
    income_statement_id: number | null
    cash_flow_statement_id: number | null
  }
  ratios: RatioItem[]
  summary: {
    total: number
    available: number
    unavailable: number
  }
}

export interface RatioHistoryPoint {
  year: number
  period_type: PeriodType
  quarter: number | null
  value: number | null
  reason?: string | null
}

export interface RatioHistorySeries {
  key: string
  name: string
  group?: string
  unit?: 'ratio' | 'percent'
  points: RatioHistoryPoint[]
}

export interface RatioHistory {
  company_id: number
  period_type: string
  periods: Array<{ year: number; period_type: PeriodType; quarter: number | null }>
  series: Record<string, RatioHistorySeries>
}

export async function fetchRatioPeriods(companyId: number): Promise<RatioPeriod[]> {
  const { data } = await http.get<RatioPeriod[]>(
    `/api/companies/${companyId}/ratio-periods`
  )
  return data
}

export async function fetchRatios(
  companyId: number,
  params: { year: number; period_type: PeriodType; quarter?: number | null }
): Promise<RatioSnapshot> {
  const { data } = await http.get<RatioSnapshot>(`/api/companies/${companyId}/ratios`, {
    params: {
      year: params.year,
      period_type: params.period_type,
      quarter: params.period_type === 'annual' ? undefined : params.quarter,
    },
  })
  return data
}

export async function fetchRatioHistory(
  companyId: number,
  params?: { period_type?: PeriodType; keys?: string[] }
): Promise<RatioHistory> {
  const { data } = await http.get<RatioHistory>(
    `/api/companies/${companyId}/ratios/history`,
    {
      params: {
        period_type: params?.period_type || 'annual',
        keys: params?.keys?.join(','),
      },
    }
  )
  return data
}

export function formatRatioValue(
  value: number | null | undefined,
  unit: 'ratio' | 'percent'
): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '—'
  if (unit === 'percent') return `${(value * 100).toFixed(2)}%`
  return value.toFixed(2)
}
