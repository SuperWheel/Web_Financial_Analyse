import http from './http'
import { STATEMENT_META, type StatementKind } from '@/constants/statementFields'

export type PeriodType = 'annual' | 'quarterly'

/** 报表通用结构：报告期 + 动态科目金额。 */
export interface StatementRecord {
  id: number
  company_id: number
  year: number
  period_type: PeriodType
  quarter: number | null
  [key: string]: number | string | null
}

export interface StatementPayload {
  year: number
  period_type: PeriodType
  quarter?: number | null
  [key: string]: number | string | null | undefined
}

function basePath(companyId: number, kind: StatementKind): string {
  return `/api/companies/${companyId}/${STATEMENT_META[kind].path}`
}

export async function fetchStatements(
  companyId: number,
  kind: StatementKind,
  params?: { year?: number; period_type?: PeriodType }
): Promise<StatementRecord[]> {
  const { data } = await http.get<StatementRecord[]>(basePath(companyId, kind), {
    params,
  })
  return data
}

export async function createStatement(
  companyId: number,
  kind: StatementKind,
  payload: StatementPayload
): Promise<StatementRecord> {
  const { data } = await http.post<StatementRecord>(basePath(companyId, kind), payload)
  return data
}

export async function updateStatement(
  companyId: number,
  kind: StatementKind,
  id: number,
  payload: Partial<StatementPayload>
): Promise<StatementRecord> {
  const { data } = await http.patch<StatementRecord>(
    `${basePath(companyId, kind)}/${id}`,
    payload
  )
  return data
}

export async function deleteStatement(
  companyId: number,
  kind: StatementKind,
  id: number
): Promise<void> {
  await http.delete(`${basePath(companyId, kind)}/${id}`)
}
