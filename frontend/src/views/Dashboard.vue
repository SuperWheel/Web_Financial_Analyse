<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { storeToRefs } from 'pinia'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { useCompanyStore } from '@/stores/company'

// 端到端切片：企业列表 + 新建。验证前后端代理打通。
const store = useCompanyStore()
const { companies, loading } = storeToRefs(store)

const dialogVisible = ref(false)
const formRef = ref<FormInstance>()
const form = reactive({ name: '', code: '', industry: '' })

const rules: FormRules = {
  name: [{ required: true, message: '请输入企业名称', trigger: 'blur' }],
}

async function handleSubmit() {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    await store.add({
      name: form.name,
      code: form.code || null,
      industry: form.industry || null,
    })
    ElMessage.success('创建成功')
    dialogVisible.value = false
    resetForm()
  })
}

function resetForm() {
  form.name = ''
  form.code = ''
  form.industry = ''
  formRef.value?.clearValidate()
}

async function handleDelete(id: number) {
  await store.remove(id)
  ElMessage.success('已删除')
}

onMounted(() => {
  store.load()
})
</script>

<template>
  <div class="dashboard">
    <div class="toolbar">
      <el-button type="primary" :icon="'Plus'" @click="dialogVisible = true">
        新建企业
      </el-button>
      <el-button :icon="'Refresh'" @click="store.load()">刷新</el-button>
    </div>

    <el-table :data="companies" v-loading="loading" border stripe>
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="name" label="企业名称" min-width="160" />
      <el-table-column prop="code" label="代码" width="120" />
      <el-table-column prop="industry" label="行业" width="140" />
      <el-table-column label="操作" width="120" fixed="right">
        <template #default="{ row }">
          <el-button type="danger" link @click="handleDelete(row.id)">删除</el-button>
        </template>
      </el-table-column>
      <template #empty>
        <el-empty description="暂无企业，点击「新建企业」开始" />
      </template>
    </el-table>

    <el-dialog v-model="dialogVisible" title="新建企业" width="460px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" placeholder="企业名称" />
        </el-form-item>
        <el-form-item label="代码" prop="code">
          <el-input v-model="form.code" placeholder="股票代码/统一编号（可选）" />
        </el-form-item>
        <el-form-item label="行业" prop="industry">
          <el-input v-model="form.industry" placeholder="所属行业（可选）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.dashboard {
  background: #fff;
  padding: 16px;
  border-radius: 6px;
}
.toolbar {
  margin-bottom: 16px;
  display: flex;
  gap: 8px;
}
</style>
