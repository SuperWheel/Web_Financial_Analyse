import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

// 路由表：业务页面通过 DefaultLayout 承载
const routes: RouteRecordRaw[] = [
  {
    path: '/',
    component: () => import('@/layouts/DefaultLayout.vue'),
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'dashboard',
        component: () => import('@/views/Dashboard.vue'),
        meta: { title: '仪表盘', icon: 'Odometer' },
      },
      {
        path: 'statements',
        name: 'statements',
        component: () => import('@/views/StatementsView.vue'),
        meta: { title: '三大报表', icon: 'Document' },
      },
      {
        path: 'import',
        name: 'import',
        component: () => import('@/views/ImportView.vue'),
        meta: { title: '年报导入', icon: 'Upload' },
      },
      {
        path: 'analysis',
        name: 'analysis',
        component: () => import('@/views/AnalysisView.vue'),
        meta: { title: '比率分析', icon: 'TrendCharts' },
      },
      {
        path: 'compare',
        name: 'compare',
        component: () => import('@/views/CompareView.vue'),
        meta: { title: '多期对比', icon: 'DataAnalysis' },
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
