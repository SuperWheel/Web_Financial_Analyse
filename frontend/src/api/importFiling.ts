import http from './http'

export interface CoverageStats {
  core_total?: number
  core_hit?: number
  mapped_fields?: number
  /** 0–1 core-field hit rate */
  coverage?: number
}

export interface UnmappedRow {
  statement?: string
  label?: string
  amount?: number | null
  page?: number | null
  reason?: string
}

export interface ImportJob {
  id: number
  source_type: string
  original_filename: string
  status: string
  company_hint: string | null
  company_code_hint: string | null
  company_id: number | null
  report_year: number | null
  period_type: string | null
  quarter: number | null
  accounting_standard: string | null
  unit_scale: number | null
  scope: string | null
  confidence: number | null
  fill_mode: string | null
  error_message: string | null
  coverage: Record<string, CoverageStats>
  issues: string[]
  unmapped: UnmappedRow[]
  draft: {
    statements?: Record<string, Record<string, number>>
    [key: string]: unknown
  }
  raw_extract: Record<string, unknown>
  commit_result: Record<string, unknown> | null
  created_at: string | null
  updated_at: string | null
}

export async function uploadFiling(file: File): Promise<ImportJob> {
  const form = new FormData()
  form.append('file', file)
  const { data } = await http.post<ImportJob>('/api/imports/filings', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120000,
  })
  return data
}

export async function fetchImportJob(id: number): Promise<ImportJob> {
  const { data } = await http.get<ImportJob>(`/api/imports/filings/${id}`)
  return data
}

export async function updateImportJob(
  id: number,
  payload: {
    company_id?: number | null
    company_hint?: string | null
    report_year?: number | null
    period_type?: string | null
    quarter?: number | null
    statements?: Record<string, Record<string, number | null>>
  }
): Promise<ImportJob> {
  const { data } = await http.patch<ImportJob>(`/api/imports/filings/${id}`, payload)
  return data
}

export async function commitImportJob(
  id: number,
  payload?: { company_id?: number | null; overwrite?: boolean }
): Promise<ImportJob> {
  const { data } = await http.post<ImportJob>(`/api/imports/filings/${id}/commit`, payload ?? {})
  return data
}

export async function listImportJobs(): Promise<ImportJob[]> {
  const { data } = await http.get<ImportJob[]>('/api/imports/filings')
  return data
}
