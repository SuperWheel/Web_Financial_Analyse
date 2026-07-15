import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  type Company,
  type CompanyCreatePayload,
  createCompany,
  deleteCompany,
  fetchCompanies,
} from '@/api/company'

/** 企业状态管理：范式参照，后续领域 store 照此组织。 */
export const useCompanyStore = defineStore('company', () => {
  const companies = ref<Company[]>([])
  const loading = ref(false)

  async function load() {
    loading.value = true
    try {
      companies.value = await fetchCompanies()
    } finally {
      loading.value = false
    }
  }

  async function add(payload: CompanyCreatePayload) {
    const created = await createCompany(payload)
    companies.value.push(created)
    return created
  }

  async function remove(id: number) {
    await deleteCompany(id)
    companies.value = companies.value.filter((c) => c.id !== id)
  }

  return { companies, loading, load, add, remove }
})
