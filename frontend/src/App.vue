<template>
  <div id="app" class="min-h-screen bg-gray-50">
    <!-- 移动端适配导航 -->
    <header class="bg-white shadow-sm border-b border-gray-200 sticky top-0 z-40">
      <nav class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex justify-between items-center h-16">
          <!-- Logo和标题 -->
          <div class="flex items-center space-x-3">
            <div class="flex-shrink-0">
              <Shield class="h-8 w-8 text-primary-600" />
            </div>
            <div class="hidden sm:block">
              <h1 class="text-lg font-semibold text-gray-900">
                诈骗风险阻断系统
              </h1>
              <p class="text-xs text-gray-500">基于Qwen2Audio实时检测</p>
            </div>
          </div>

          <!-- 桌面端导航 -->
          <div class="hidden md:flex space-x-8">
            <router-link
              v-for="item in navigation"
              :key="item.name"
              :to="item.to"
              class="inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium"
              :class="[
                route.name === item.name
                  ? 'border-primary-500 text-primary-600'
                  : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
              ]"
            >
              <component :is="item.icon" class="h-4 w-4 mr-2" />
              {{ item.label }}
            </router-link>
          </div>

          <!-- 移动端菜单按钮 -->
          <div class="md:hidden">
            <button
              @click="mobileMenuOpen = !mobileMenuOpen"
              class="inline-flex items-center justify-center p-2 rounded-md text-gray-400 hover:text-gray-500 hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-primary-500"
            >
              <Menu v-if="!mobileMenuOpen" class="h-6 w-6" />
              <X v-else class="h-6 w-6" />
            </button>
          </div>
        </div>

        <!-- 移动端导航菜单 -->
        <div v-if="mobileMenuOpen" class="md:hidden border-t border-gray-200">
          <div class="pt-2 pb-3 space-y-1">
            <router-link
              v-for="item in navigation"
              :key="item.name"
              :to="item.to"
              class="block pl-3 pr-4 py-2 border-l-4 text-base font-medium"
              :class="[
                route.name === item.name
                  ? 'bg-primary-50 border-primary-500 text-primary-700'
                  : 'border-transparent text-gray-600 hover:bg-gray-50 hover:border-gray-300 hover:text-gray-800'
              ]"
              @click="mobileMenuOpen = false"
            >
              <div class="flex items-center">
                <component :is="item.icon" class="h-5 w-5 mr-3" />
                {{ item.label }}
              </div>
            </router-link>
          </div>
        </div>
      </nav>
    </header>

    <!-- 主要内容区域 -->
    <main class="flex-1">
      <router-view v-slot="{ Component, route }">
        <transition
          name="page"
          mode="out-in"
          appear
        >
          <component :is="Component" :key="route.name" />
        </transition>
      </router-view>
    </main>

    <!-- 全局状态指示器 -->
    <div
      v-if="globalLoading"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
    >
      <div class="bg-white rounded-lg p-6 flex items-center space-x-3">
        <div class="animate-spin rounded-full h-6 w-6 border-b-2 border-primary-600"></div>
        <span class="text-gray-700">处理中...</span>
      </div>
    </div>

    <!-- 网络状态提示 -->
    <div
      v-if="!isOnline"
      class="fixed top-20 left-4 right-4 bg-danger-100 border border-danger-400 text-danger-700 px-4 py-3 rounded-lg z-30"
    >
      <div class="flex items-center">
        <WifiOff class="h-4 w-4 mr-2" />
        网络连接已断开，请检查网络设置
      </div>
    </div>

    <!-- WebSocket连接状态 -->
    <div
      v-if="wsStatus !== 'connected' && wsStatus !== 'disconnected'"
      class="fixed bottom-4 right-4 bg-yellow-100 border border-yellow-400 text-yellow-700 px-4 py-2 rounded-lg z-30"
    >
      <div class="flex items-center">
        <div class="animate-pulse h-2 w-2 bg-yellow-600 rounded-full mr-2"></div>
        {{ wsStatusText }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import {
  Shield,
  MessageCircle,
  Activity,
  FileText,
  Settings,
  Menu,
  X,
  WifiOff
} from 'lucide-vue-next'

// 响应式数据
const route = useRoute()
const mobileMenuOpen = ref(false)
const globalLoading = ref(false)
const isOnline = ref(navigator.onLine)
const wsStatus = ref<'connecting' | 'connected' | 'disconnected' | 'error'>('disconnected')

// 导航配置
const navigation = [
  { name: 'Home', to: '/', label: '首页', icon: Shield },
  { name: 'Practice', to: '/practice', label: 'AI陪练', icon: MessageCircle },
  { name: 'Monitor', to: '/monitor', label: '实时监护', icon: Activity },
  { name: 'Analysis', to: '/analysis', label: '案例分析', icon: FileText },
  { name: 'Settings', to: '/settings', label: '设置', icon: Settings }
]

// 计算属性
const wsStatusText = computed(() => {
  const statusMap = {
    connecting: '连接中...',
    connected: '已连接',
    disconnected: '已断开',
    error: '连接错误'
  }
  return statusMap[wsStatus.value]
})

// 全局事件监听
const handleGlobalLoading = (event: CustomEvent) => {
  globalLoading.value = event.detail.loading
}

const handleWsStatusChange = (event: CustomEvent) => {
  wsStatus.value = event.detail.status
}

const handleOnline = () => {
  isOnline.value = true
}

const handleOffline = () => {
  isOnline.value = false
}

// 生命周期
onMounted(() => {
  // 监听全局事件
  window.addEventListener('globalLoading', handleGlobalLoading as EventListener)
  window.addEventListener('wsStatusChange', handleWsStatusChange as EventListener)
  
  // 监听网络状态
  window.addEventListener('online', handleOnline)
  window.addEventListener('offline', handleOffline)
  
  // 初始化PWA安装提示
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.addEventListener('message', (event) => {
      if (event.data?.type === 'SW_UPDATED') {
        // 显示应用更新提示
        if (confirm('应用已更新，是否立即重启？')) {
          window.location.reload()
        }
      }
    })
  }
})

onUnmounted(() => {
  // 清理事件监听
  window.removeEventListener('globalLoading', handleGlobalLoading as EventListener)
  window.removeEventListener('wsStatusChange', handleWsStatusChange as EventListener)
  window.removeEventListener('online', handleOnline)
  window.removeEventListener('offline', handleOffline)
})
</script>

<style scoped>
/* 页面切换动画 */
.page-enter-active,
.page-leave-active {
  transition: all 0.3s ease;
}

.page-enter-from {
  opacity: 0;
  transform: translateX(20px);
}

.page-leave-to {
  opacity: 0;
  transform: translateX(-20px);
}

/* 移动端适配 */
@media (max-width: 768px) {
  .nav-container {
    padding-left: 1rem;
    padding-right: 1rem;
  }
}

/* 高对比度模式支持 */
@media (prefers-contrast: high) {
  .bg-gray-50 {
    background-color: white;
  }
  
  .border-gray-200 {
    border-color: black;
  }
}

/* 减少动画模式支持 */
@media (prefers-reduced-motion: reduce) {
  .page-enter-active,
  .page-leave-active {
    transition: none;
  }
  
  .animate-pulse {
    animation: none;
  }
}
</style>