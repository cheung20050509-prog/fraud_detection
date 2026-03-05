import { createApp } from 'vue'
import { createPinia } from 'pinia'
import router from './router'
import App from './App.vue'

// 导入全局样式
import './assets/styles/main.css'

// 创建Vue应用实例
const app = createApp(App)

// 安装插件
app.use(createPinia())
app.use(router)

// 全局错误处理
app.config.errorHandler = (error, vm, info) => {
  console.error('全局错误:', error)
  console.error('组件实例:', vm)
  console.error('错误信息:', info)
}

// 全局警告处理
app.config.warnHandler = (msg, vm, trace) => {
  console.warn('全局警告:', msg)
  console.warn('组件实例:', vm)
  console.warn('堆栈跟踪:', trace)
}

// 挂载应用
app.mount('#app')

// 注册Service Worker（PWA支持）
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js')
      .then((registration) => {
        console.log('SW registered: ', registration)
      })
      .catch((registrationError) => {
        console.log('SW registration failed: ', registrationError)
      })
  })
}