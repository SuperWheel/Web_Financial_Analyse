<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  DataAnalysis,
  Document,
  Odometer,
  TrendCharts,
  Upload,
} from '@element-plus/icons-vue'

// 图标映射：route.meta.icon 名 → 组件
const iconMap = { Odometer, Document, TrendCharts, Upload, DataAnalysis } as const

const route = useRoute()
const router = useRouter()

const activeMenu = computed(() => route.path)

const menus = [
  { index: '/dashboard', title: '仪表盘', icon: 'Odometer' as const },
  { index: '/statements', title: '三大报表', icon: 'Document' as const },
  { index: '/import', title: '年报导入', icon: 'Upload' as const },
  { index: '/analysis', title: '比率分析', icon: 'TrendCharts' as const },
  { index: '/compare', title: '多期对比', icon: 'DataAnalysis' as const },
]

function handleSelect(index: string) {
  router.push(index)
}
</script>

<template>
  <el-container class="layout">
    <el-aside width="220px" class="aside">
      <div class="logo">财务分析系统</div>
      <el-menu
        :default-active="activeMenu"
        class="menu"
        background-color="#001529"
        text-color="#cfd8e3"
        active-text-color="#ffffff"
        @select="handleSelect"
      >
        <el-menu-item v-for="m in menus" :key="m.index" :index="m.index">
          <el-icon><component :is="iconMap[m.icon]" /></el-icon>
          <span>{{ m.title }}</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="header">
        <span class="title">{{ String(route.meta.title || '财务分析') }}</span>
      </el-header>
      <el-main class="main">
        <RouterView />
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
.layout {
  height: 100vh;
}
.aside {
  background-color: #001529;
}
.logo {
  height: 60px;
  line-height: 60px;
  text-align: center;
  color: #fff;
  font-size: 16px;
  font-weight: 600;
  letter-spacing: 1px;
}
.menu {
  border-right: none;
}
.header {
  background-color: #fff;
  border-bottom: 1px solid #eee;
  display: flex;
  align-items: center;
}
.header .title {
  font-size: 18px;
  font-weight: 600;
}
.main {
  background-color: #f5f7fa;
}
</style>
