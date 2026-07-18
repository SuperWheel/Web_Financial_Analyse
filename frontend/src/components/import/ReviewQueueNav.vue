<script setup lang="ts">
import type { ImportJob } from '@/api/importFiling'

defineProps<{
  jobs: ImportJob[]
  index: number
  current: ImportJob | null
  committedCount: number
  pendingCount: number
}>()

const emit = defineEmits<{
  prev: []
  next: []
  select: [index: number]
}>()
</script>

<template>
  <div v-if="jobs.length" class="review-nav">
    <el-button :disabled="index <= 0" @click="emit('prev')">上一份</el-button>
    <div class="review-nav-center">
      <strong>
        {{ index + 1 }} / {{ jobs.length }}
        <template v-if="current?.report_year"> · {{ current.report_year }} 年报</template>
      </strong>
      <div class="sub">
        已入库 {{ committedCount }} · 待确认 {{ pendingCount }}
        <template v-if="current?.original_filename"> · {{ current.original_filename }}</template>
      </div>
      <div class="review-chips">
        <el-check-tag
          v-for="(rj, i) in jobs"
          :key="rj.id"
          :checked="i === index"
          class="review-chip"
          @change="emit('select', i)"
        >
          {{ rj.report_year || `#${rj.id}` }}
          <span v-if="rj.status === 'committed'">✓</span>
          <span v-else-if="rj.status === 'failed'">!</span>
        </el-check-tag>
      </div>
    </div>
    <el-button :disabled="index >= jobs.length - 1" @click="emit('next')">下一份</el-button>
  </div>
</template>

<style scoped>
.review-nav {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  padding: 12px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  background: #fafcff;
}
.review-nav-center {
  flex: 1;
  text-align: center;
}
.review-chips {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 6px;
  margin-top: 8px;
}
.review-chip {
  cursor: pointer;
}
.sub {
  margin-top: 8px;
  font-size: 12px;
  color: #909399;
}
</style>
