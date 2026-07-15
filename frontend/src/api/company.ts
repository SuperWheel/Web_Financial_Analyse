import http from './http'

/** 企业实体（对应后端 CompanyRead）。 */
export interface Company {
  id: number
  name: string
  code: string | null
  industry: string | null
  created_at: string
  updated_at: string
}

/** 创建企业请求体。 */
export interface CompanyCreatePayload {
  name: string
  code?: string | null
  industry?: string | null
}

/** 获取企业列表。 */
export async function fetchCompanies(): Promise<Company[]> {
  const { data } = await http.get<Company[]>('/api/companies')
  return data
}

/** 创建企业。 */
export async function createCompany(payload: CompanyCreatePayload): Promise<Company> {
  const { data } = await http.post<Company>('/api/companies', payload)
  return data
}

/** 删除企业。 */
export async function deleteCompany(id: number): Promise<void> {
  await http.delete(`/api/companies/${id}`)
}
