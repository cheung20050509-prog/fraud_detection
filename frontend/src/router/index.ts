import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

// 路由配置
const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'Home',
    component: () => import('@/pages/HomePage.vue'),
    meta: {
      title: '首页 - 电信诈骗风险阻断系统'
    }
  },
  {
    path: '/practice',
    name: 'Practice',
    component: () => import('@/pages/PracticePage.vue'),
    meta: {
      title: 'AI智能陪练 - 电信诈骗风险阻断系统'
    }
  },
  {
    path: '/monitor',
    name: 'Monitor',
    component: () => import('@/pages/MonitorPage.vue'),
    meta: {
      title: '实时监护 - 电信诈骗风险阻断系统'
    }
  },
  {
    path: '/analysis',
    name: 'Analysis',
    component: () => import('@/pages/AnalysisPage.vue'),
    meta: {
      title: '案例分析 - 电信诈骗风险阻断系统'
    }
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('@/pages/SettingsPage.vue'),
    meta: {
      title: '系统设置 - 电信诈骗风险阻断系统'
    }
  },
  // 404页面
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/pages/NotFoundPage.vue'),
    meta: {
      title: '页面未找到 - 电信诈骗风险阻断系统'
    }
  }
]

// 创建路由实例
const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) {
      return savedPosition
    } else {
      return { top: 0 }
    }
  }
})

// 全局前置守卫
router.beforeEach((to, from, next) => {
  // 设置页面标题
  if (to.meta?.title) {
    document.title = to.meta.title as string
  }
  
  // 移动端性能优化：检测页面切换时清理资源
  if (from.name && from.name !== to.name) {
    // 触发页面切换事件
    window.dispatchEvent(new CustomEvent('pageChange', {
      detail: { from: from.name, to: to.name }
    }))
  }
  
  next()
})

// 全局后置钩子
router.afterEach((to, from) => {
  // 页面加载完成后的处理
  console.log(`路由切换: ${String(from.name)} -> ${String(to.name)}`)
})

export default router