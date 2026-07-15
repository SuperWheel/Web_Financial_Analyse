import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  type StatementPayload,
  type StatementRecord,
  createStatement,
  deleteStatement,
  fetchStatements,
  updateStatement,
} from '@/api/statement'
import type { StatementKind } from '@/constants/statementFields'

/** 三大报表状态：按当前选中企业 + 报表类型加载列表。 */
export const useStatementStore = defineStore('statement', () => {
  const items = ref<StatementRecord[]>([])
  const loading = ref(false)
  const companyId = ref<number | null>(null)
  const kind = ref<StatementKind>('balance')

  async function load(cid: number, k: StatementKind) {
    companyId.value = cid
    kind.value = k
    loading.value = true
    try {
      items.value = await fetchStatements(cid, k)
    } finally {
      loading.value = false
    }
  }

  async function add(payload: StatementPayload) {
    if (companyId.value == null) throw new Error('未选择企业')
    const created = await createStatement(companyId.value, kind.value, payload)
    items.value = [created, ...items.value]
    return created
  }

  async function patch(id: number, payload: Partial<StatementPayload>) {
    if (companyId.value == null) throw new Error('未选择企业')
    const updated = await updateStatement(companyId.value, kind.value, id, payload)
    items.value = items.value.map((row) => (row.id === id ? updated : row))
    return updated
  }

  async function remove(id: number) {
    if (companyId.value == null) throw new Error('未选择企业')
    await deleteStatement(companyId.value, kind.value, id)
    items.value = items.value.filter((row) => row.id !== id)
  }

  function clear() {
    items.value = []
    companyId.value = null
  }

  return { items, loading, companyId, kind, load, add, patch, remove, clear }
})
