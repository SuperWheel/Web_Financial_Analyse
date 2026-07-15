import http from './http'
import type { PeriodType } from './compare'

export interface ExcelPeriodRef {
  year: number
  period_type: PeriodType
  quarter: number | null
  label: string
}

export interface ExcelSheetPreview {
  statement_type: 'balance' | 'income' | 'cashflow'
  label: string
  periods: ExcelPeriodRef[]
  non_null_fields: number
  rows_with_code: number
}

export interface ExcelImportPreview {
  company_id: number
  period_type: PeriodType | null
  periods: ExcelPeriodRef[]
  sheets: ExcelSheetPreview[]
  warnings: string[]
  will_create: string[]
  will_update: string[]
  will_skip_empty: string[]
}

export interface ExcelImportResult {
  company_id: number
  created: string[]
  updated: string[]
  skipped: string[]
  warnings: string[]
  statement_ids: Record<string, number>
}

function filenameFromDisposition(disposition: string | undefined): string | null {
  if (!disposition) return null
  const star = /filename\*\s*=\s*UTF-8''([^;]+)/i.exec(disposition)
  if (star?.[1]) {
    try {
      return decodeURIComponent(star[1].trim())
    } catch {
      return star[1].trim()
    }
  }
  const plain = /filename\s*=\s*"?([^";]+)"?/i.exec(disposition)
  return plain?.[1]?.trim() || null
}

function triggerBlobDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

export async function downloadExcelTemplate(params?: {
  period_type?: PeriodType
  years?: number[]
}): Promise<void> {
  const res = await http.get('/api/excel/template.xlsx', {
    params: {
      period_type: params?.period_type ?? 'annual',
      years: params?.years?.length ? params.years.join(',') : undefined,
    },
    responseType: 'blob',
  })
  const name =
    filenameFromDisposition(res.headers['content-disposition'] as string | undefined) ||
    '财务三表模板.xlsx'
  triggerBlobDownload(
    new Blob([res.data], {
      type:
        res.headers['content-type'] ||
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    }),
    name
  )
}

export async function previewExcelImport(
  companyId: number,
  file: File
): Promise<ExcelImportPreview> {
  const form = new FormData()
  form.append('file', file)
  const { data } = await http.post<ExcelImportPreview>(
    `/api/companies/${companyId}/excel/preview`,
    form,
    { headers: { 'Content-Type': 'multipart/form-data' } }
  )
  return data
}

export async function commitExcelImport(
  companyId: number,
  file: File,
  overwrite = true
): Promise<ExcelImportResult> {
  const form = new FormData()
  form.append('file', file)
  form.append('overwrite', overwrite ? 'true' : 'false')
  const { data } = await http.post<ExcelImportResult>(
    `/api/companies/${companyId}/excel/import`,
    form,
    { headers: { 'Content-Type': 'multipart/form-data' } }
  )
  return data
}
