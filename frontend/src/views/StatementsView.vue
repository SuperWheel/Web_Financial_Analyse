<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import {
  ElMessage,
  ElMessageBox,
  type FormInstance,
  type FormRules,
} from 'element-plus'
import { useCompanyStore } from '@/stores/company'
import { useStatementStore } from '@/stores/statement'
import {
  STATEMENT_META,
  allFieldKeys,
  flattenRows,
  type FieldMeta,
  type LayoutRow,
  type StatementKind,
} from '@/constants/statementFields'
import type { PeriodType, StatementPayload, StatementRecord } from '@/api/statement'

const companyStore = useCompanyStore()
const statementStore = useStatementStore()
const { companies } = storeToRefs(companyStore)
const { items, loading } = storeToRefs(statementStore)

const selectedCompanyId = ref<number | null>(null)
const activeKind = ref<StatementKind>('balance')

const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const formRef = ref<FormInstance>()
const saving = ref(false)

const currentYear = new Date().getFullYear()

const form = reactive<{
  year: number
  period_type: PeriodType
  quarter: number | null
  amounts: Record<string, number | null>
}>({
  year: currentYear,
  period_type: 'annual',
  quarter: null,
  amounts: {},
})

const meta = computed(() => STATEMENT_META[activeKind.value])
const groups = computed(() => meta.value.groups)
const summaryKeys = computed(() => meta.value.summaryKeys)
const layout = computed(() => meta.value.layout)

const selectedCompany = computed(
  () => companies.value.find((c) => c.id === selectedCompanyId.value) ?? null
)

const periodText = computed(() => {
  if (form.period_type === 'annual') return `${form.year} 年度`
  return `${form.year} 年 第 ${form.quarter ?? '—'} 季度`
})

const allRows = computed(() => flattenRows(groups.value))
const assetRows = computed(() => allRows.value.filter((r) => r.side === 'asset'))
const liabilityRows = computed(() => allRows.value.filter((r) => r.side === 'liability'))

/** 左右栏对齐：按行数 pad 空行 */
const balancePairRows = computed(() => {
  const left = assetRows.value
  const right = liabilityRows.value
  const n = Math.max(left.length, right.length)
  const pairs: { left?: LayoutRow; right?: LayoutRow }[] = []
  for (let i = 0; i < n; i++) {
    pairs.push({ left: left[i], right: right[i] })
  }
  return pairs
})

const rules: FormRules = {
  year: [{ required: true, message: '请输入年份', trigger: 'blur' }],
  period_type: [{ required: true, message: '请选择报告期类型', trigger: 'change' }],
}

function periodTypeLabel(t: PeriodType): string {
  return t === 'annual' ? '年报' : '季报'
}

function formatMoney(v: unknown): string {
  if (v === null || v === undefined || v === '') return '—'
  const n = Number(v)
  if (Number.isNaN(n)) return '—'
  return n.toLocaleString('zh-CN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
}

function fieldLabel(key: string): string {
  for (const g of groups.value) {
    const f = g.fields.find((x) => x.key === key)
    if (f) return f.label
  }
  return key
}

function rowClass(row?: FieldMeta): string {
  if (!row) return ''
  if (row.role === 'section') return 'row-section'
  if (row.role === 'total') return 'row-total'
  return 'row-item'
}

function resetAmounts() {
  const keys = allFieldKeys(groups.value)
  const next: Record<string, number | null> = {}
  for (const k of keys) next[k] = null
  form.amounts = next
}

function openCreate() {
  if (selectedCompanyId.value == null) {
    ElMessage.warning('请先选择企业')
    return
  }
  editingId.value = null
  form.year = currentYear
  form.period_type = 'annual'
  form.quarter = null
  resetAmounts()
  dialogVisible.value = true
}

function openEdit(row: StatementRecord) {
  editingId.value = row.id
  form.year = row.year
  form.period_type = row.period_type
  form.quarter = row.quarter
  resetAmounts()
  for (const k of Object.keys(form.amounts)) {
    const v = row[k]
    form.amounts[k] = v === null || v === undefined ? null : Number(v)
  }
  dialogVisible.value = true
}

async function handleSubmit() {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    if (form.period_type === 'quarterly' && !form.quarter) {
      ElMessage.warning('季报必须选择季度')
      return
    }
    const payload: StatementPayload = {
      year: form.year,
      period_type: form.period_type,
      quarter: form.period_type === 'annual' ? null : form.quarter,
    }
    for (const [k, v] of Object.entries(form.amounts)) {
      payload[k] = v
    }
    saving.value = true
    try {
      if (editingId.value == null) {
        await statementStore.add(payload)
        ElMessage.success('创建成功')
      } else {
        await statementStore.patch(editingId.value, payload)
        ElMessage.success('已更新')
      }
      dialogVisible.value = false
    } finally {
      saving.value = false
    }
  })
}

async function handleDelete(row: StatementRecord) {
  await ElMessageBox.confirm(
    `确认删除 ${row.year} ${periodTypeLabel(row.period_type)}${
      row.quarter ? ` Q${row.quarter}` : ''
    } 报表？`,
    '删除确认',
    { type: 'warning' }
  )
  await statementStore.remove(row.id)
  ElMessage.success('已删除')
}

async function reload() {
  if (selectedCompanyId.value == null) {
    statementStore.clear()
    return
  }
  await statementStore.load(selectedCompanyId.value, activeKind.value)
}

watch(activeKind, () => {
  resetAmounts()
  reload()
})

watch(selectedCompanyId, () => {
  reload()
})

watch(
  () => form.period_type,
  (t) => {
    if (t === 'annual') form.quarter = null
    else if (!form.quarter) form.quarter = 1
  }
)

onMounted(async () => {
  await companyStore.load()
  if (companies.value.length > 0) {
    selectedCompanyId.value = companies.value[0].id
  }
  resetAmounts()
})
</script>

<template>
  <div class="statements">
    <div class="toolbar">
      <el-select
        v-model="selectedCompanyId"
        placeholder="选择企业"
        filterable
        clearable
        style="width: 240px"
      >
        <el-option
          v-for="c in companies"
          :key="c.id"
          :label="c.code ? `${c.name} (${c.code})` : c.name"
          :value="c.id"
        />
      </el-select>
      <el-button type="primary" :disabled="!selectedCompanyId" @click="openCreate">
        新建报告期
      </el-button>
      <el-button type="success" @click="$router.push('/import')">年报导入</el-button>
      <el-button :disabled="!selectedCompanyId" @click="reload">刷新</el-button>
    </div>

    <el-tabs v-model="activeKind" type="border-card">
      <el-tab-pane
        v-for="(m, key) in STATEMENT_META"
        :key="key"
        :label="m.label"
        :name="key"
      />
    </el-tabs>

    <el-table
      :data="items"
      v-loading="loading"
      border
      stripe
      style="margin-top: 12px"
      empty-text="暂无数据，请先选择企业并新建报告期"
    >
      <el-table-column prop="year" label="年份" width="90" />
      <el-table-column label="类型" width="90">
        <template #default="{ row }">
          {{ periodTypeLabel(row.period_type) }}
        </template>
      </el-table-column>
      <el-table-column label="季度" width="80">
        <template #default="{ row }">
          {{ row.quarter ?? '—' }}
        </template>
      </el-table-column>
      <el-table-column
        v-for="key in summaryKeys"
        :key="key"
        :label="fieldLabel(key)"
        min-width="140"
        align="right"
      >
        <template #default="{ row }">
          {{ formatMoney(row[key]) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="140" fixed="right">
        <template #default="{ row }">
          <el-button type="primary" link @click="openEdit(row)">编辑</el-button>
          <el-button type="danger" link @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 会计报表样式录入 -->
    <el-dialog
      v-model="dialogVisible"
      :title="editingId ? `编辑${meta.label}` : `新建${meta.label}`"
      :width="layout === 'balance' ? '1080px' : '760px'"
      destroy-on-close
      top="3vh"
      class="stmt-dialog"
      align-center
    >
      <el-form ref="formRef" :model="form" :rules="rules" class="period-form">
        <div class="period-bar">
          <el-form-item label="年份" prop="year" class="period-item">
            <el-input-number
              v-model="form.year"
              :min="1990"
              :max="2100"
              controls-position="right"
              style="width: 130px"
            />
          </el-form-item>
          <el-form-item label="类型" prop="period_type" class="period-item">
            <el-select v-model="form.period_type" style="width: 120px">
              <el-option label="年报" value="annual" />
              <el-option label="季报" value="quarterly" />
            </el-select>
          </el-form-item>
          <el-form-item
            v-if="form.period_type === 'quarterly'"
            label="季度"
            class="period-item"
          >
            <el-select v-model="form.quarter" style="width: 100px">
              <el-option v-for="q in [1, 2, 3, 4]" :key="q" :label="`Q${q}`" :value="q" />
            </el-select>
          </el-form-item>
        </div>
      </el-form>

      <div class="sheet-paper">
        <h2 class="sheet-title">{{ meta.label }}</h2>
        <div class="sheet-meta">
          <span>公司名称：{{ selectedCompany?.name || '—' }}</span>
          <span>{{ periodText }}</span>
          <span>单位：元</span>
        </div>

        <!-- 资产负债表：左右对照 -->
        <table v-if="layout === 'balance'" class="acct-table balance-table">
          <thead>
            <tr>
              <th class="col-label">资产</th>
              <th class="col-amount">期末数</th>
              <th class="col-label">负债及所有者权益</th>
              <th class="col-amount">期末数</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(pair, idx) in balancePairRows" :key="idx">
              <td
                class="col-label"
                :class="rowClass(pair.left)"
                :style="{ paddingLeft: `${12 + (pair.left?.indent ?? 0) * 16}px` }"
              >
                {{ pair.left?.label || '' }}
              </td>
              <td class="col-amount" :class="rowClass(pair.left)">
                <el-input-number
                  v-if="pair.left?.key"
                  v-model="form.amounts[pair.left.key]"
                  :precision="2"
                  :controls="false"
                  :value-on-clear="null"
                  placeholder=""
                  class="money-input"
                />
              </td>
              <td
                class="col-label"
                :class="rowClass(pair.right)"
                :style="{ paddingLeft: `${12 + (pair.right?.indent ?? 0) * 16}px` }"
              >
                {{ pair.right?.label || '' }}
              </td>
              <td class="col-amount" :class="rowClass(pair.right)">
                <el-input-number
                  v-if="pair.right?.key"
                  v-model="form.amounts[pair.right.key]"
                  :precision="2"
                  :controls="false"
                  :value-on-clear="null"
                  placeholder=""
                  class="money-input"
                />
              </td>
            </tr>
          </tbody>
        </table>

        <!-- 利润表 / 现金流量表：竖式 -->
        <table v-else class="acct-table vertical-table">
          <thead>
            <tr>
              <th class="col-label">项目</th>
              <th class="col-amount">金额</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, idx) in allRows" :key="idx">
              <td
                class="col-label"
                :class="rowClass(row)"
                :style="{ paddingLeft: `${12 + (row.indent ?? 0) * 16}px` }"
              >
                {{ row.label }}
              </td>
              <td class="col-amount" :class="rowClass(row)">
                <el-input-number
                  v-if="row.key"
                  v-model="form.amounts[row.key]"
                  :precision="2"
                  :controls="false"
                  :value-on-clear="null"
                  placeholder=""
                  class="money-input"
                />
              </td>
            </tr>
          </tbody>
        </table>

        <div class="sheet-footer">
          <span>单位负责人：</span>
          <span>财务负责人：</span>
          <span>制表人：</span>
        </div>
      </div>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSubmit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.statements {
  background: #fff;
  padding: 16px;
  border-radius: 6px;
}
.toolbar {
  margin-bottom: 16px;
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}
:deep(.el-tabs--border-card) {
  box-shadow: none;
  border-bottom: none;
}
:deep(.el-tabs__content) {
  display: none;
}

.period-form {
  margin-bottom: 8px;
}
.period-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 16px;
  align-items: center;
}
.period-item {
  margin-bottom: 0;
}

/* —— 会计报表纸面 —— */
.sheet-paper {
  border: 1px solid #c5cdd8;
  background: #fafbfc;
  padding: 16px 20px 12px;
  max-height: min(68vh, 720px);
  overflow: auto;
}
.sheet-title {
  margin: 0 0 10px;
  text-align: center;
  font-size: 22px;
  font-weight: 600;
  color: #1a3a8a;
  letter-spacing: 4px;
}
.sheet-meta {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  color: #333;
  margin-bottom: 10px;
  padding: 0 4px;
}

.acct-table {
  width: 100%;
  border-collapse: collapse;
  background: #fff;
  font-size: 13px;
  table-layout: fixed;
}
.acct-table th,
.acct-table td {
  border: 1px solid #333;
  height: 34px;
  vertical-align: middle;
}
.acct-table thead th {
  background: #f3f5f8;
  font-weight: 600;
  text-align: center;
  color: #222;
}
.col-label {
  text-align: left;
  color: #222;
  line-height: 1.35;
}
.col-amount {
  width: 148px;
  text-align: right;
  padding: 2px 4px;
}
.balance-table .col-label {
  width: auto;
}
.balance-table .col-amount {
  width: 140px;
}

.row-section {
  font-weight: 700;
  background: #f7f8fa;
}
.row-total {
  font-weight: 700;
  background: #f0f4fa;
}
.row-item {
  font-weight: 400;
}

.money-input {
  width: 100%;
}
:deep(.money-input .el-input__wrapper) {
  box-shadow: none;
  background: transparent;
  padding: 0 6px;
}
:deep(.money-input .el-input__inner) {
  text-align: right;
  height: 28px;
  font-size: 13px;
}
:deep(.money-input .el-input__wrapper:hover),
:deep(.money-input .el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px var(--el-color-primary) inset;
  background: #fff;
}

.sheet-footer {
  display: flex;
  justify-content: space-between;
  margin-top: 14px;
  padding: 0 8px 4px;
  font-size: 13px;
  color: #444;
}
</style>
