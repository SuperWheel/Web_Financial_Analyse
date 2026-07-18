<script setup lang="ts">
import { formatRatioValue } from '@/api/ratio'

export type PrimaryKpi = {
  key: string
  name: string
  unit: 'ratio' | 'percent'
  value: number | null
  signal: { level: string; label: string; tagType: 'success' | 'warning' | 'info' | 'danger' | 'primary' | undefined }
  yoy: {
    prev: number | null
    improved: boolean | null
    direction: string
    meaning: string
    meaningLabel: string
    deltaDisplay: string
    relChangeDisplay?: string | null
  }
  transition: string
  variant?: string | null
  reason?: string | null
  missing: string[]
}

defineProps<{
  kpis: PrimaryKpi[]
  highlightedKey: string | null
  yoyClass: (improved: boolean | null, direction: string) => string
  yoyArrow: (direction: string) => string
  meaningClass: (meaning: string) => string
}>()

const emit = defineEmits<{
  focus: [key: string]
}>()
</script>

<template>
  <div>
    <div class="section-label">核心指标</div>
    <el-row :gutter="12" class="kpi-row">
      <el-col
        v-for="kpi in kpis"
        :key="kpi.key"
        :xs="24"
        :sm="12"
        :md="8"
        :lg="4"
      >
        <el-card
          shadow="hover"
          class="kpi-card"
          :class="[
            'sig-' + kpi.signal.level,
            { 'kpi-highlight': highlightedKey === kpi.key },
          ]"
          @click="emit('focus', kpi.key)"
        >
          <div class="kpi-top">
            <span class="kpi-name">{{ kpi.name }}</span>
            <el-tag :type="kpi.signal.tagType" size="small" effect="light">
              {{ kpi.signal.label }}
            </el-tag>
          </div>
          <div class="kpi-value" :class="{ muted: kpi.value === null }">
            {{ formatRatioValue(kpi.value, kpi.unit) }}
          </div>
          <div v-if="kpi.yoy.prev !== null" class="kpi-transition">
            {{ kpi.transition }}
          </div>
          <div
            class="kpi-yoy"
            :class="yoyClass(kpi.yoy.improved, kpi.yoy.direction)"
          >
            <template v-if="kpi.yoy.direction !== 'na'">
              <span class="arrow">{{ yoyArrow(kpi.yoy.direction) }}</span>
              <span :class="meaningClass(kpi.yoy.meaning)">{{ kpi.yoy.meaningLabel }}</span>
              <span class="kpi-delta">{{ kpi.yoy.deltaDisplay }}</span>
              <span v-if="kpi.yoy.relChangeDisplay" class="kpi-rel">
                ({{ kpi.yoy.relChangeDisplay }})
              </span>
            </template>
            <template v-else>
              <span class="yoy-flat">较上期 —</span>
            </template>
          </div>
          <div v-if="kpi.variant" class="kpi-variant">口径 {{ kpi.variant }}</div>
          <div v-else-if="kpi.value === null" class="kpi-variant">
            {{
              kpi.missing.length
                ? '缺：' + kpi.missing.slice(0, 2).join(',')
                : kpi.reason || '暂不可算'
            }}
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped>
.section-label {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  margin: 8px 4px 10px;
}
.kpi-row {
  margin-bottom: 4px;
}
.kpi-card {
  margin-bottom: 12px;
  border-radius: 8px;
  border-top: 3px solid #dcdfe6;
  cursor: pointer;
  transition: box-shadow 0.15s ease, border-color 0.15s ease;
}
.kpi-card.sig-good {
  border-top-color: #67c23a;
}
.kpi-card.sig-watch {
  border-top-color: #e6a23c;
}
.kpi-card.sig-risk {
  border-top-color: #f56c6c;
}
.kpi-card.sig-na,
.kpi-card.sig-neutral {
  border-top-color: #c0c4cc;
}
.kpi-card.kpi-highlight {
  box-shadow: 0 0 0 2px #409eff inset;
}
.kpi-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 6px;
}
.kpi-name {
  font-size: 13px;
  color: #606266;
  font-weight: 500;
}
.kpi-value {
  font-size: 26px;
  font-weight: 700;
  color: #1f2d3d;
  margin: 10px 0 4px;
  letter-spacing: 0.02em;
}
.kpi-value.muted {
  color: #c0c4cc;
  font-size: 20px;
}
.kpi-transition {
  font-size: 12px;
  color: #909399;
  margin-bottom: 4px;
  font-variant-numeric: tabular-nums;
}
.kpi-yoy {
  font-size: 12px;
  font-weight: 600;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px;
}
.kpi-yoy .arrow {
  margin-right: 0;
}
.kpi-delta {
  font-variant-numeric: tabular-nums;
}
.kpi-rel {
  font-weight: 500;
  color: #a0aec0;
}
.kpi-variant {
  margin-top: 4px;
  font-size: 11px;
  color: #a0aec0;
  line-height: 1.3;
  word-break: break-all;
}
.yoy-up {
  color: #67c23a;
}
.yoy-down {
  color: #f56c6c;
}
.yoy-flat {
  color: #909399;
}
.meaning-improve {
  color: #67c23a;
}
.meaning-watch {
  color: #f56c6c;
}
.meaning-flat {
  color: #909399;
}
.kpi-card :deep(.el-card__body) {
  padding: 10px 12px;
}
</style>
