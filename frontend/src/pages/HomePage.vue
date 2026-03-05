<template>
  <div class="min-h-screen bg-gradient-to-br from-primary-50 to-indigo-100">
    <!-- 头部 -->
    <header class="bg-white/80 backdrop-blur-md shadow-sm border-b border-gray-200">
      <div class="max-w-6xl mx-auto px-4 py-6">
        <div class="text-center">
          <div class="flex items-center justify-center space-x-3 mb-4">
            <Shield class="h-12 w-12 text-primary-600" />
            <h1 class="text-4xl font-bold text-gray-900">电信诈骗风险阻断系统</h1>
          </div>
          <p class="text-xl text-gray-600">基于 Qwen2Audio 的实时智能检测与防护</p>
        </div>
      </div>
    </header>

    <!-- 主要内容 -->
    <main class="max-w-6xl mx-auto px-4 py-12">
      <!-- 功能卡片网格 -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8 mb-16">
        <!-- AI陪练卡片 -->
        <div class="group bg-white rounded-2xl shadow-lg hover:shadow-xl transition-all duration-300 hover:-translate-y-1">
          <div class="p-8">
            <div class="w-16 h-16 bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-300">
              <MessageCircle class="h-8 w-8 text-white" />
            </div>
            <h3 class="text-2xl font-bold text-gray-900 mb-3">AI 智能陪练</h3>
            <p class="text-gray-600 mb-6 leading-relaxed">
              模拟真实诈骗场景，通过AI对话提升您的防诈骗意识和识别能力
            </p>
            <div class="flex items-center justify-between mb-4">
              <div class="flex items-center space-x-2 text-sm text-gray-500">
                <Users class="h-4 w-4" />
                <span>陪练模式</span>
              </div>
              <div class="flex items-center space-x-2 text-sm text-gray-500">
                <Mic class="h-4 w-4" />
                <span>语音交互</span>
              </div>
            </div>
            <router-link to="/practice"
                       class="w-full bg-primary-600 text-white px-6 py-3 rounded-xl font-medium hover:bg-primary-700 transition-colors duration-200 flex items-center justify-center space-x-2">
              <Play class="h-5 w-5" />
              <span>开始陪练</span>
            </router-link>
          </div>
        </div>

        <!-- 实时监护卡片 -->
        <div class="group bg-white rounded-2xl shadow-lg hover:shadow-xl transition-all duration-300 hover:-translate-y-1 relative overflow-hidden">
          <div class="absolute top-0 right-0 bg-danger-500 text-white px-3 py-1 rounded-bl-xl text-sm font-medium">
            核心功能
          </div>
          <div class="p-8">
            <div class="w-16 h-16 bg-gradient-to-br from-danger-500 to-red-600 rounded-xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-300">
              <Activity class="h-8 w-8 text-white" />
            </div>
            <h3 class="text-2xl font-bold text-gray-900 mb-3">实时通话监护</h3>
            <p class="text-gray-600 mb-6 leading-relaxed">
              开启免提通话时，系统在旁边"旁听"，实时识别诈骗风险并即时警报
            </p>
            <div class="flex items-center justify-between mb-4">
              <div class="flex items-center space-x-2 text-sm text-gray-500">
                <Shield class="h-4 w-4" />
                <span>实时监测</span>
              </div>
              <div class="flex items-center space-x-2 text-sm text-gray-500">
                <Bell class="h-4 w-4" />
                <span>风险警报</span>
              </div>
            </div>
            <router-link to="/monitor"
                       class="w-full bg-danger-600 text-white px-6 py-3 rounded-xl font-medium hover:bg-danger-700 transition-colors duration-200 flex items-center justify-center space-x-2">
              <Eye class="h-5 w-5" />
              <span>开始监护</span>
            </router-link>
          </div>
        </div>

        <!-- 案例分析卡片 -->
        <div class="group bg-white rounded-2xl shadow-lg hover:shadow-xl transition-all duration-300 hover:-translate-y-1">
          <div class="p-8">
            <div class="w-16 h-16 bg-gradient-to-br from-green-500 to-emerald-600 rounded-xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-300">
              <FileText class="h-8 w-8 text-white" />
            </div>
            <h3 class="text-2xl font-bold text-gray-900 mb-3">案例上传分析</h3>
            <p class="text-gray-600 mb-6 leading-relaxed">
              上传通话录音或聊天记录，获得详细的诈骗风险分析报告和防范建议
            </p>
            <div class="flex items-center justify-between mb-4">
              <div class="flex items-center space-x-2 text-sm text-gray-500">
                <Upload class="h-4 w-4" />
                <span>文件上传</span>
              </div>
              <div class="flex items-center space-x-2 text-sm text-gray-500">
                <BarChart3 class="h-4 w-4" />
                <span>深度分析</span>
              </div>
            </div>
            <router-link to="/analysis"
                       class="w-full bg-green-600 text-white px-6 py-3 rounded-xl font-medium hover:bg-green-700 transition-colors duration-200 flex items-center justify-center space-x-2">
              <Search class="h-5 w-5" />
              <span>分析案例</span>
            </router-link>
          </div>
        </div>
      </div>

      <!-- 系统特性介绍 -->
      <div class="bg-white/80 backdrop-blur-md rounded-2xl shadow-lg p-8 mb-16">
        <h2 class="text-3xl font-bold text-center text-gray-900 mb-12">核心技术创新</h2>
        
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
          <div class="text-center">
            <div class="w-16 h-16 bg-gradient-to-br from-purple-500 to-purple-600 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <Cpu class="h-8 w-8 text-white" />
            </div>
            <h4 class="text-lg font-semibold text-gray-900 mb-2">Qwen2Audio 引擎</h4>
            <p class="text-sm text-gray-600">
              阿里达最新多模态大模型，深度理解语音语义和情感特征
            </p>
          </div>

          <div class="text-center">
            <div class="w-16 h-16 bg-gradient-to-br from-blue-500 to-blue-600 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <Zap class="h-8 w-8 text-white" />
            </div>
            <h4 class="text-lg font-semibold text-gray-900 mb-2">毫秒级响应</h4>
            <p class="text-sm text-gray-600">
              WebSocket低延迟传输，实时音频流处理和即时风险预警
            </p>
          </div>

          <div class="text-center">
            <div class="w-16 h-16 bg-gradient-to-br from-orange-500 to-orange-600 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <Brain class="h-8 w-8 text-white" />
            </div>
            <h4 class="text-lg font-semibold text-gray-900 mb-2">多算法融合</h4>
            <p class="text-sm text-gray-600">
              结合AI模型、关键词检测、语音特征分析的综合判断体系
            </p>
          </div>

          <div class="text-center">
            <div class="w-16 h-16 bg-gradient-to-br from-green-500 to-green-600 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <Smartphone class="h-8 w-8 text-white" />
            </div>
            <h4 class="text-lg font-semibold text-gray-900 mb-2">移动端适配</h4>
            <p class="text-sm text-gray-600">
              完美适配手机端，支持震动提醒和离线缓存功能
            </p>
          </div>
        </div>
      </div>

      <!-- 统计数据展示 -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-16">
        <div class="bg-gradient-to-br from-blue-500 to-blue-600 rounded-2xl p-6 text-white">
          <div class="flex items-center justify-between mb-2">
            <Shield class="h-6 w-6" />
            <TrendingUp class="h-5 w-5" />
          </div>
          <div class="text-3xl font-bold mb-1">99.2%</div>
          <div class="text-blue-100">检测准确率</div>
        </div>

        <div class="bg-gradient-to-br from-green-500 to-green-600 rounded-2xl p-6 text-white">
          <div class="flex items-center justify-between mb-2">
            <Zap class="h-6 w-6" />
            <Clock class="h-5 w-5" />
          </div>
          <div class="text-3xl font-bold mb-1">&lt;200ms</div>
          <div class="text-green-100">响应延迟</div>
        </div>

        <div class="bg-gradient-to-br from-purple-500 to-purple-600 rounded-2xl p-6 text-white">
          <div class="flex items-center justify-between mb-2">
            <Users class="h-6 w-6" />
            <Award class="h-5 w-5" />
          </div>
          <div class="text-3xl font-bold mb-1">1000+</div>
          <div class="text-purple-100">诈骗场景</div>
        </div>
      </div>

      <!-- 技术架构展示 -->
      <div class="bg-gray-900 text-white rounded-2xl p-8 mb-16">
        <h2 class="text-3xl font-bold text-center mb-12">技术架构</h2>
        
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <!-- 前端架构 -->
          <div class="text-center">
            <div class="w-16 h-16 bg-green-500 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <Monitor class="h-8 w-8 text-white" />
            </div>
            <h3 class="text-xl font-semibold mb-4 text-green-400">前端架构</h3>
            <div class="text-left space-y-3">
              <div class="flex items-center space-x-3">
                <div class="w-2 h-2 bg-green-400 rounded-full"></div>
                <span class="text-sm">Vue 3 + TypeScript</span>
              </div>
              <div class="flex items-center space-x-3">
                <div class="w-2 h-2 bg-green-400 rounded-full"></div>
                <span class="text-sm">Vite + TailwindCSS</span>
              </div>
              <div class="flex items-center space-x-3">
                <div class="w-2 h-2 bg-green-400 rounded-full"></div>
                <span class="text-sm">PWA 移动端适配</span>
              </div>
              <div class="flex items-center space-x-3">
                <div class="w-2 h-2 bg-green-400 rounded-full"></div>
                <span class="text-sm">WebSocket 实时通信</span>
              </div>
            </div>
          </div>

          <!-- 后端架构 -->
          <div class="text-center">
            <div class="w-16 h-16 bg-blue-500 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <Server class="h-8 w-8 text-white" />
            </div>
            <h3 class="text-xl font-semibold mb-4 text-blue-400">后端架构</h3>
            <div class="text-left space-y-3">
              <div class="flex items-center space-x-3">
                <div class="w-2 h-2 bg-blue-400 rounded-full"></div>
                <span class="text-sm">FastAPI 异步框架</span>
              </div>
              <div class="flex items-center space-x-3">
                <div class="w-2 h-2 bg-blue-400 rounded-full"></div>
                <span class="text-sm">Qwen2Audio + Whisper</span>
              </div>
              <div class="flex items-center space-x-3">
                <div class="w-2 h-2 bg-blue-400 rounded-full"></div>
                <span class="text-sm">SQLite 数据存储</span>
              </div>
              <div class="flex items-center space-x-3">
                <div class="w-2 h-2 bg-blue-400 rounded-full"></div>
                <span class="text-sm">WebSocket 流处理</span>
              </div>
            </div>
          </div>

          <!-- AI模型 -->
          <div class="text-center">
            <div class="w-16 h-16 bg-purple-500 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <Brain class="h-8 w-8 text-white" />
            </div>
            <h3 class="text-xl font-semibold mb-4 text-purple-400">AI 模型</h3>
            <div class="text-left space-y-3">
              <div class="flex items-center space-x-3">
                <div class="w-2 h-2 bg-purple-400 rounded-full"></div>
                <span class="text-sm">Qwen2Audio 语音理解</span>
              </div>
              <div class="flex items-center space-x-3">
                <div class="w-2 h-2 bg-purple-400 rounded-full"></div>
                <span class="text-sm">Whisper ASR 识别</span>
              </div>
              <div class="flex items-center space-x-3">
                <div class="w-2 h-2 bg-purple-400 rounded-full"></div>
                <span class="text-sm">EdgeTTS 语音合成</span>
              </div>
              <div class="flex items-center space-x-3">
                <div class="w-2 h-2 bg-purple-400 rounded-full"></div>
                <span class="text-sm">多模态融合算法</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 快速开始 -->
      <div class="text-center">
        <h2 class="text-3xl font-bold text-gray-900 mb-8">立即开始使用</h2>
        <p class="text-xl text-gray-600 mb-8">
          选择适合的功能开始保护您的通信安全
        </p>
        
        <div class="flex flex-col sm:flex-row gap-4 justify-center">
          <router-link to="/practice"
                     class="px-8 py-4 bg-primary-600 text-white rounded-xl font-medium hover:bg-primary-700 transition-colors duration-200 flex items-center justify-center space-x-2">
            <GraduationCap class="h-5 w-5" />
            <span>学习防骗技巧</span>
          </router-link>
          
          <router-link to="/monitor"
                     class="px-8 py-4 bg-danger-600 text-white rounded-xl font-medium hover:bg-danger-700 transition-colors duration-200 flex items-center justify-center space-x-2">
            <Shield class="h-5 w-5" />
            <span>开启实时保护</span>
          </router-link>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import {
  Shield,
  MessageCircle,
  Activity,
  FileText,
  Users,
  Mic,
  Bell,
  Eye,
  Search,
  Upload,
  BarChart3,
  Cpu,
  Zap,
  Brain,
  Smartphone,
  Monitor,
  Server,
  TrendingUp,
  Clock,
  Award,
  GraduationCap,
  Play
} from 'lucide-vue-next'
</script>

<style scoped>
/* 卡片悬停效果 */
.group:hover .group-hover\:scale-110 {
  transform: scale(1.1);
}

/* 移动端优化 */
@media (max-width: 768px) {
  .hero-section {
    padding: 2rem 1rem;
  }
  
  .feature-grid {
    grid-template-columns: 1fr;
    gap: 1rem;
  }
  
  .stats-grid {
    grid-template-columns: 1fr;
  }
}

/* 高对比度模式 */
@media (prefers-contrast: high) {
  .gradient-card {
    border: 2px solid currentColor;
  }
}

/* 减少动画模式 */
@media (prefers-reduced-motion: reduce) {
  .group:hover .group-hover\:scale-110 {
    transform: none;
  }
  
  .transition-all {
    transition: none;
  }
}

/* 滚动条样式 */
::-webkit-scrollbar {
  width: 8px;
}

::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 10px;
}

::-webkit-scrollbar-thumb {
  background: #888;
  border-radius: 10px;
}

::-webkit-scrollbar-thumb:hover {
  background: #555;
}
</style>