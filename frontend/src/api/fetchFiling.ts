import http from './http'
import type { ImportJob } from './importFiling'


export interface StockSecurity {
  code: string
  name: string | null
  org_id: string | null
  category: string | null
  type: string | null
  column: string | null
}
export interface FilingCandidate {
  source: string
  code: string
  name: string | null
  org_id: string | null
  year: number
  title: string
  announce_date: string | null
  announcement_id: string | null
  adjunct_url: string | null
  pdf_url: string
}

export async function searchCninfoSecurities(
  q: string
): Promise<StockSecurity[]> {
  const { data } = await http.get<StockSecurity[]>(
    '/api/imports/fetch/cninfo/securities',
    { params: { q }, timeout: 90000 }
  )
  return data
}

export async function searchCninfoAnnual(
  q: string,
  year: number
): Promise<FilingCandidate[]> {
  const { data } = await http.get<FilingCandidate[]>(
    '/api/imports/fetch/cninfo/search',
    { params: { q, year }, timeout: 90000 }
  )
  return data
}

export async function fetchFromUrl(payload: {
  url: string
  company_id?: number | null
  filename?: string | null
}): Promise<ImportJob> {
  const { data } = await http.post<ImportJob>(
    '/api/imports/fetch/from-url',
    {
      url: payload.url,
      company_id: payload.company_id ?? undefined,
      filename: payload.filename ?? undefined,
    },
    { timeout: 120000 }
  )
  return data
}

export async function downloadCninfoFiling(payload: {
  pdf_url: string
  code?: string | null
  title?: string | null
  year?: number | null
  name?: string | null
  company_id?: number | null
}): Promise<ImportJob> {
  const { data } = await http.post<ImportJob>(
    '/api/imports/fetch/cninfo/download',
    {
      pdf_url: payload.pdf_url,
      code: payload.code ?? undefined,
      title: payload.title ?? undefined,
      year: payload.year ?? undefined,
      name: payload.name ?? undefined,
      company_id: payload.company_id ?? undefined,
    },
    { timeout: 180000 }
  )
  return data
}
