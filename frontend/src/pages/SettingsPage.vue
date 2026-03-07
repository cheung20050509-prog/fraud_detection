<template>
  <div class="min-h-screen bg-gradient-to-br from-primary-50 to-indigo-100">
    <!-- 头部 -->
    <header class="bg-white/80 backdrop-blur-md shadow-sm border-b border-gray-200">
      <div class="max-w-6xl mx-auto px-4 py-6">
        <div class="flex items-center justify-between">
          <div class="flex items-center space-x-3">
            <Settings class="h-8 w-8 text-primary-600" />
            <h1 class="text-3xl font-bold text-gray-900">系统设置</h1>
          </div>
          <router-link to="/" 
                     class="flex items-center space-x-2 text-gray-600 hover:text-primary-600 transition-colors">
            <ArrowLeft class="h-5 w-5" />
            <span>返回首页</span>
          </router-link>
        </div>
      </div>
    </header>

    <!-- 主要内容 -->
    <main class="max-w-6xl mx-auto px-4 py-12">
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <!-- 左侧导航 -->
        <div class="lg:col-span-1">
          <div class="bg-white rounded-2xl shadow-lg p-6">
            <nav class="space-y-2">
              <button
                v-for="section in settingsSections"
                :key="section.id"
                @click="activeSection = section.id"
                :class="[
                  'w-full flex items-center space-x-3 px-4 py-3 rounded-xl text-left transition-all duration-200',
                  activeSection === section.id
                    ? 'bg-primary-100 text-primary-700 border-l-4 border-primary-600'
                    : 'hover:bg-gray-50 text-gray-700'
                ]"
              >
                <component :is="section.icon" class="h-5 w-5" />
                <span class="font-medium">{{ section.title }}</span>
              </button>
            </nav>
          </div>
        </div>

        <!-- 右侧内容 -->
        <div class="lg:col-span-2">
          <!-- 模型设置 -->
          <div v-if="activeSection === 'model'" class="bg-white rounded-2xl shadow-lg p-8">
            <div class="flex items-center space-x-3 mb-6">
              <Cpu class="h-6 w-6 text-primary-600" />
              <h2 class="text-2xl font-bold text-gray-900">模型配置</h2>
            </div>

            <div class="space-y-6">
              <!-- 模型类型选择 -->
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">模型类型</label>
                <select v-model="modelSettings.modelType" 
                        class="w-full px-4 py-2 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent">
                  <option value="local">本地模型</option>
                  <option value="official">官方API</option>
                </select>
              </div>

              <!-- 模型路径 -->
              <div v-if="modelSettings.modelType === 'local'">
                <label class="block text-sm font-medium text-gray-700 mb-2">模型路径</label>
                <div class="flex space-x-2">
                  <input v-model="modelSettings.modelPath" 
                         type="text" 
                         placeholder="请输入本地模型路径"
                         class="flex-1 px-4 py-2 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent">
                  <button @click="browseModelPath"
                          class="px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-xl transition-colors">
                    <FolderOpen class="h-5 w-5" />
                  </button>
                </div>
              </div>

              <!-- API密钥 -->
              <div v-if="modelSettings.modelType === 'official'">
                <label class="block text-sm font-medium text-gray-700 mb-2">API密钥</label>
                <input v-model="modelSettings.apiKey" 
                       type="password" 
                       placeholder="请输入API密钥"
                       class="w-full px-4 py-2 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent">
              </div>

              <!-- 设备选择 -->
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">计算设备</label>
                <div class="flex space-x-4">
                  <label class="flex items-center space-x-2">
                    <input v-model="modelSettings.device" value="cpu" type="radio" class="text-primary-600">
                    <span>CPU</span>
                  </label>
                  <label class="flex items-center space-x-2">
                    <input v-model="modelSettings.device" value="cuda" type="radio" class="text-primary-600">
                    <span>GPU (CUDA)</span>
                  </label>
                </div>
              </div>

              <!-- 性能设置 -->
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">
                  最大内存使用 (GB): {{ modelSettings.maxMemory }}
                </label>
                <input v-model="modelSettings.maxMemory" 
                       type="range" 
                       min="1" 
                       max="16" 
                       step="0.5"
                       class="w-full">
              </div>

              <button @click="saveModelSettings"
                      :disabled="isSaving"
                      class="w-full bg-primary-600 text-white px-6 py-3 rounded-xl font-medium hover:bg-primary-700 transition-colors duration-200 disabled:opacity-50">
                <span v-if="!isSaving">保存模型设置</span>
                <span v-else class="flex items-center justify-center space-x-2">
                  <div class="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                  <span>保存中...</span>
                </span>
              </button>
            </div>
          </div>

          <!-- 音频设置 -->
          <div v-if="activeSection === 'audio'" class="bg-white rounded-2xl shadow-lg p-8">
            <div class="flex items-center space-x-3 mb-6">
              <Mic class="h-6 w-6 text-primary-600" />
              <h2 class="text-2xl font-bold text-gray-900">音频配置</h2>
            </div>

            <div class="space-y-6">
              <!-- 采样率 -->
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">采样率</label>
                <select v-model="audioSettings.sampleRate" 
                        class="w-full px-4 py-2 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent">
                  <option value="16000">16 kHz</option>
                  <option value="22050">22.05 kHz</option>
                  <option value="44100">44.1 kHz</option>
                  <option value="48000">48 kHz</option>
                </select>
              </div>

              <!-- 音频格式 -->
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">音频格式</label>
                <select v-model="audioSettings.format" 
                        class="w-full px-4 py-2 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent">
                  <option value="wav">WAV</option>
                  <option value="mp3">MP3</option>
                  <option value="flac">FLAC</option>
                </select>
              </div>

              <!-- 噪声抑制 -->
              <div>
                <label class="flex items-center space-x-2">
                  <input v-model="audioSettings.noiseReduction" type="checkbox" class="text-primary-600">
                  <span class="text-sm font-medium text-gray-700">启用噪声抑制</span>
                </label>
              </div>

              <!-- 音频增强 -->
              <div>
                <label class="flex items-center space-x-2">
                  <input v-model="audioSettings.enhancement" type="checkbox" class="text-primary-600">
                  <span class="text-sm font-medium text-gray-700">启用音频增强</span>
                </label>
              </div>

              <button @click="saveAudioSettings"
                      class="w-full bg-primary-600 text-white px-6 py-3 rounded-xl font-medium hover:bg-primary-700 transition-colors duration-200">
                保存音频设置
              </button>
            </div>
          </div>

          <!-- 系统设置 -->
          <div v-if="activeSection === 'system'" class="bg-white rounded-2xl shadow-lg p-8">
            <div class="flex items-center space-x-3 mb-6">
              <Monitor class="h-6 w-6 text-primary-600" />
              <h2 class="text-2xl font-bold text-gray-900">系统配置</h2>
            </div>

            <div class="space-y-6">
              <!-- 语言设置 -->
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">界面语言</label>
                <select v-model="systemSettings.language" 
                        class="w-full px-4 py-2 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent">
                  <option value="zh-CN">简体中文</option>
                  <option value="en-US">English</option>
                </select>
              </div>

              <!-- 主题设置 -->
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">主题模式</label>
                <div class="flex space-x-4">
                  <label class="flex items-center space-x-2">
                    <input v-model="systemSettings.theme" value="light" type="radio" class="text-primary-600">
                    <span>浅色</span>
                  </label>
                  <label class="flex items-center space-x-2">
                    <input v-model="systemSettings.theme" value="dark" type="radio" class="text-primary-600">
                    <span>深色</span>
                  </label>
                  <label class="flex items-center space-x-2">
                    <input v-model="systemSettings.theme" value="auto" type="radio" class="text-primary-600">
                    <span>跟随系统</span>
                  </label>
                </div>
              </div>

              <!-- 日志级别 -->
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">日志级别</label>
                <select v-model="systemSettings.logLevel" 
                        class="w-full px-4 py-2 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent">
                  <option value="debug">Debug</option>
                  <option value="info">Info</option>
                  <option value="warn">Warning</option>
                  <option value="error">Error</option>
                </select>
              </div>

              <!-- 自动保存 -->
              <div>
                <label class="flex items-center space-x-2">
                  <input v-model="systemSettings.autoSave" type="checkbox" class="text-primary-600">
                  <span class="text-sm font-medium text-gray-700">自动保存设置</span>
                </label>
              </div>

              <!-- 数据清理 -->
              <div class="border-t pt-6">
                <h3 class="text-lg font-semibold text-gray-900 mb-4">数据管理</h3>
                <div class="space-y-3">
                  <button @click="clearCache"
                          class="w-full px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-xl transition-colors text-left">
                    清理缓存
                  </button>
                  <button @click="exportSettings"
                          class="w-full px-4 py-2 bg-green-100 hover:bg-green-200 text-green-700 rounded-xl transition-colors text-left">
                    导出配置
                  </button>
                  <button @click="importSettings"
                          class="w-full px-4 py-2 bg-blue-100 hover:bg-blue-200 text-blue-700 rounded-xl transition-colors text-left">
                    导入配置
                  </button>
                </div>
              </div>

              <button @click="saveSystemSettings"
                      class="w-full bg-primary-600 text-white px-6 py-3 rounded-xl font-medium hover:bg-primary-700 transition-colors duration-200">
                保存系统设置
              </button>
            </div>
          </div>

          <!-- 关于页面 -->
          <div v-if="activeSection === 'about'" class="bg-white rounded-2xl shadow-lg p-8">
            <div class="flex items-center space-x-3 mb-6">
              <Info class="h-6 w-6 text-primary-600" />
              <h2 class="text-2xl font-bold text-gray-900">关于系统</h2>
            </div>

            <div class="space-y-6">
              <!-- 系统信息 -->
              <div class="bg-gray-50 rounded-xl p-6">
                <h3 class="text-lg font-semibold text-gray-900 mb-4">系统信息</h3>
                <dl class="space-y-3">
                  <div class="flex justify-between">
                    <dt class="text-gray-600">版本号</dt>
                    <dd class="font-medium">v1.0.0</dd>
                  </div>
                  <div class="flex justify-between">
                    <dt class="text-gray-600">构建时间</dt>
                    <dd class="font-medium">2024-01-20</dd>
                  </div>
                  <div class="flex justify-between">
                    <dt class="text-gray-600">运行环境</dt>
                    <dd class="font-medium">Vue 3 + TypeScript</dd>
                  </div>
                  <div class="flex justify-between">
                    <dt class="text-gray-600">AI模型</dt>
                    <dd class="font-medium">Qwen2Audio</dd>
                  </div>
                </dl>
              </div>

              <!-- 功能特性 -->
              <div>
                <h3 class="text-lg font-semibold text-gray-900 mb-4">核心功能</h3>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div class="flex items-center space-x-3">
                    <CheckCircle class="h-5 w-5 text-green-500" />
                    <span>实时语音检测</span>
                  </div>
                  <div class="flex items-center space-x-3">
                    <CheckCircle class="h-5 w-5 text-green-500" />
                    <span>AI智能陪练</span>
                  </div>
                  <div class="flex items-center space-x-3">
                    <CheckCircle class="h-5 w-5 text-green-500" />
                    <span>多场景模拟</span>
                  </div>
                  <div class="flex items-center space-x-3">
                    <CheckCircle class="h-5 w-5 text-green-500" />
                    <span>风险等级评估</span>
                  </div>
                </div>
              </div>

              <!-- 技术支持 -->
              <div>
                <h3 class="text-lg font-semibold text-gray-900 mb-4">技术支持</h3>
                <div class="space-y-3">
                  <a href="#" class="flex items-center space-x-3 text-blue-600 hover:text-blue-700">
                    <Mail class="h-5 w-5" />
                    <span>support@fraud-blocking.com</span>
                  </a>
                  <a href="#" class="flex items-center space-x-3 text-blue-600 hover:text-blue-700">
                    <Github class="h-5 w-5" />
                    <span>GitHub 仓库</span>
                  </a>
                  <a href="#" class="flex items-center space-x-3 text-blue-600 hover:text-blue-700">
                    <FileText class="h-5 w-5" />
                    <span>使用文档</span>
                  </a>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { 
  Settings, 
  ArrowLeft, 
  Cpu, 
  Mic, 
  Monitor, 
  Info, 
  CheckCircle,
  Mail,
  Github,
  FileText,
  FolderOpen
} from 'lucide-vue-next'

// 设置分组
const settingsSections = [
  { id: 'model', title: '模型配置', icon: Cpu },
  { id: 'audio', title: '音频设置', icon: Mic },
  { id: 'system', title: '系统设置', icon: Monitor },
  { id: 'about', title: '关于系统', icon: Info }
]

// 当前激活的设置分组
const activeSection = ref('model')

// 保存状态
const isSaving = ref(false)

// 模型设置
const modelSettings = ref({
  modelType: 'local',
  modelPath: './models/qwen2-audio',
  apiKey: '',
  device: 'cpu',
  maxMemory: 4
})

// 音频设置
const audioSettings = ref({
  sampleRate: '16000',
  format: 'wav',
  noiseReduction: true,
  enhancement: false
})

// 系统设置
const systemSettings = ref({
  language: 'zh-CN',
  theme: 'light',
  logLevel: 'info',
  autoSave: true
})

// 保存模型设置
async function saveModelSettings() {
  isSaving.value = true
  try {
    // 这里可以调用API保存设置
    await new Promise(resolve => setTimeout(resolve, 1000))
    console.log('模型设置已保存:', modelSettings.value)
    // 显示成功提示
  } catch (error) {
    console.error('保存模型设置失败:', error)
  } finally {
    isSaving.value = false
  }
}

// 保存音频设置
function saveAudioSettings() {
  console.log('音频设置已保存:', audioSettings.value)
  // 这里可以调用API保存设置
}

// 保存系统设置
function saveSystemSettings() {
  console.log('系统设置已保存:', systemSettings.value)
  // 这里可以调用API保存设置
}

// 浏览模型路径
function browseModelPath() {
  // 这里可以打开文件选择对话框
  console.log('浏览模型路径')
}

// 清理缓存
function clearCache() {
  console.log('清理缓存')
  // 这里可以调用清理缓存的逻辑
}

// 导出设置
function exportSettings() {
  const settings = {
    model: modelSettings.value,
    audio: audioSettings.value,
    system: systemSettings.value
  }
  
  const blob = new Blob([JSON.stringify(settings, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'fraud-blocking-settings.json'
  a.click()
  URL.revokeObjectURL(url)
}

// 导入设置
function importSettings() {
  const input = document.createElement('input')
  input.type = 'file'
  input.accept = '.json'
  input.onchange = (e) => {
    const file = (e.target as HTMLInputElement).files?.[0]
    if (file) {
      const reader = new FileReader()
      reader.onload = (e) => {
        try {
          const settings = JSON.parse(e.target?.result as string)
          if (settings.model) modelSettings.value = { ...modelSettings.value, ...settings.model }
          if (settings.audio) audioSettings.value = { ...audioSettings.value, ...settings.audio }
          if (settings.system) systemSettings.value = { ...systemSettings.value, ...settings.system }
          console.log('设置导入成功')
        } catch (error) {
          console.error('设置导入失败:', error)
        }
      }
      reader.readAsText(file)
    }
  }
  input.click()
}

// 组件挂载时加载设置
onMounted(() => {
  // 这里可以从localStorage或API加载设置
  const savedSettings = localStorage.getItem('fraud-blocking-settings')
  if (savedSettings) {
    try {
      const settings = JSON.parse(savedSettings)
      if (settings.model) modelSettings.value = { ...modelSettings.value, ...settings.model }
      if (settings.audio) audioSettings.value = { ...audioSettings.value, ...settings.audio }
      if (settings.system) systemSettings.value = { ...systemSettings.value, ...settings.system }
    } catch (error) {
      console.error('加载设置失败:', error)
    }
  }
})
</script>