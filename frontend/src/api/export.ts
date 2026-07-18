import http from './http'
import type { PeriodType } from './compare'

function parseFilename(disposition: string | undefined): string | null {
  if (!disposition) return null
  // filename*=UTF-8''...
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

/** 下载企业三表 + 财务比率 Excel */
export async function downloadCompanyExcel(
  companyId: number,
  params?: { period_type?: PeriodType; years?: number[] }
): Promise<void> {
  const res = await http.get(`/api/companies/${companyId}/export.xlsx`, {
    params: {
      period_type: params?.period_type ?? 'annual',
      years: params?.years?.length ? params.years.join(',') : undefined,
    },
    responseType: 'blob',
  })

  const disposition = res.headers['content-disposition'] as string | undefined
  const filename =
    parseFilename(disposition) ||
    `export_${params?.period_type || 'annual'}.xlsx`

  const contentType = res.headers['content-type']
  const blob = new Blob([res.data], {
    type:
      typeof contentType === 'string'
        ? contentType
        : 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}
