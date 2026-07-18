<script setup lang="ts">
defineProps<{
  title: string
  blurb: string
  badgeType: 'success' | 'warning' | 'info' | 'danger' | 'primary' | undefined
  badgeText: string
  lines: string[]
}>()
</script>

<template>
  <el-card class="summary-card" shadow="never">
    <div class="summary-head">
      <div>
        <div class="summary-title">{{ title }}</div>
        <div class="summary-sub">
          {{ blurb }} · 规则阈值仅供参考，非投资建议
        </div>
      </div>
      <el-tag :type="badgeType" effect="dark" size="large">
        {{ badgeText }}
      </el-tag>
    </div>
    <ul class="summary-lines">
      <li v-for="(line, i) in lines" :key="i">{{ line }}</li>
    </ul>
  </el-card>
</template>

<style scoped>
.summary-card {
  margin-bottom: 12px;
  border-radius: 8px;
  border: 1px solid #ebeef5;
}
.summary-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 10px;
}
.summary-title {
  font-size: 18px;
  font-weight: 700;
  color: #1f2d3d;
}
.summary-sub {
  margin-top: 4px;
  font-size: 12px;
  color: #909399;
}
.summary-lines {
  margin: 0;
  padding-left: 18px;
  color: #606266;
  line-height: 1.7;
  font-size: 13px;
}
.summary-card :deep(.el-card__body) {
  padding: 12px 14px;
}
</style>
