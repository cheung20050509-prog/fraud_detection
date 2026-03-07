<template>
  <div class="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
    <!-- 头部控制区 -->
    <header class="bg-white shadow-sm border-b border-gray-200">
      <div class="max-w-4xl mx-auto px-4 py-4">
        <div class="flex items-center justify-between">
          <div class="flex items-center space-x-3">
            <MessageCircle class="h-6 w-6 text-primary-600" />
            <div>
              <h1 class="text-xl font-semibold text-gray-900">AI智能陪练</h1>
              <p class="text-sm text-gray-500">模拟诈骗场景，提升防范意识</p>
            </div>
          </div>
          
          <div class="flex items-center space-x-3">
            <!-- 场景选择 -->
            <select v-model="selectedScenario" 
                    :disabled="sessionActive"
                    class="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent">
              <option value="">选择诈骗场景</option>
              <option value="impersonation">冒充公检法</option>
              <option value="investment">高回报投资</option>
              <option value="lottery">中奖诈骗</option>
              <option value="customer_service">冒充客服</option>
            </select>
            
            <!-- 难度选择 -->
            <select v-model="difficultyLevel" 
                    :disabled="sessionActive"
                    class="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent">
              <option value="1">简单</option>
              <option value="2">普通</option>
              <option value="3">困难</option>
              <option value="4">专家</option>
              <option value="5">大师</option>
            </select>
          </div>
        </div>
      </div>
    </header>

    <!-- 主聊天区域 -->
    <div class="max-w-4xl mx-auto px-4 py-6">
      <!-- 中心动态波纹球 -->
      <div class="flex justify-center mb-6">
        <div class="relative">
          <!-- 外圈动画 -->
          <div class="absolute inset-0 rounded-full border-4"
               :class="aiStatusRingClass">
          </div>
          
          <!-- 中心状态球 -->
          <div class="relative w-24 h-24 rounded-full flex items-center justify-center transition-all duration-300"
               :class="aiStatusBallClass">
            <!-- AI状态图标 -->
            <component :is="aiStatusIcon" 
                      class="h-10 w-10 transition-all duration-300"
                      :class="aiIconClass" />
            
            <!-- 语音波形指示器 -->
            <div class="absolute inset-0 rounded-full overflow-hidden">
              <div v-for="i in 3"
                   :key="i"
                   class="absolute inset-0 rounded-full border border-white/20"
                   :class="aiWaveClass(i)"
                   :style="aiWaveStyle(i)"></div>
            </div>
          </div>
          
          <!-- AI状态标签 -->
          <div class="absolute -bottom-3 left-1/2 transform -translate-x-1/2">
            <div class="px-3 py-1 rounded-full text-xs font-semibold bg-white shadow-lg">
              {{ aiStatusText }}
            </div>
          </div>
        </div>
      </div>

      <!-- 聊天对话区域 -->
      <div class="bg-white rounded-xl shadow-lg p-6 mb-4">
        <div class="space-y-4 max-h-96 overflow-y-auto" ref="chatContainer">
          <!-- AI开场白 -->
          <div v-if="greetingMessage"
               class="flex items-start space-x-3">
            <div class="flex-shrink-0 w-8 h-8 rounded-full bg-primary-100 flex items-center justify-center">
              <Bot class="h-5 w-5 text-primary-600" />
            </div>
            <div class="flex-1">
              <div class="bg-primary-50 rounded-lg p-3 max-w-md">
                <p class="text-sm text-gray-900">{{ greetingMessage }}</p>
                <div class="flex items-center space-x-2 mt-2">
                  <span class="text-xs text-primary-600 font-medium">
                    {{ scenarioName }} · 难度: {{ difficultyText }}
                  </span>
                </div>
              </div>
            </div>
          </div>

          <!-- 对话消息 -->
          <div v-for="(message, index) in messages"
               :key="index"
               class="flex items-start space-x-3"
               :class="message.role === 'user' ? 'flex-row-reverse space-x-reverse' : ''">
            
            <!-- 头像 -->
            <div class="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center"
                 :class="message.role === 'user' ? 'bg-gray-100' : 'bg-primary-100'">
              <component :is="message.role === 'user' ? User : Bot" 
                        class="h-5 w-5"
                        :class="message.role === 'user' ? 'text-gray-600' : 'text-primary-600'" />
            </div>
            
            <!-- 消息内容 -->
            <div class="flex-1 max-w-md">
              <div class="rounded-lg p-3"
                   :class="message.role === 'user' ? 'bg-gray-100' : 'bg-primary-50'">
                
                <!-- 文本内容 -->
                <p class="text-sm text-gray-900">{{ message.content }}</p>
                
                <!-- 音频播放器 -->
                <div v-if="message.audioUrl" 
                     class="mt-2">
                  <audio controls class="w-full h-8">
                    <source :src="message.audioUrl" type="audio/wav">
                    您的浏览器不支持音频播放
                  </audio>
                </div>
                
                <!-- 诈骗检测提示 -->
                <div v-if="message.fraudIndicators && message.fraudIndicators.length > 0"
                     class="mt-2 space-y-1">
                  <div v-for="indicator in message.fraudIndicators"
                       :key="indicator"
                       class="flex items-center space-x-2 text-xs bg-danger-50 text-danger-800 px-2 py-1 rounded">
                    <AlertTriangle class="h-3 w-3" />
                    <span>{{ indicator }}</span>
                  </div>
                </div>
              </div>
              
              <!-- 消息元信息 -->
              <div class="flex items-center space-x-3 mt-1">
                <span class="text-xs text-gray-500">
                  {{ formatTime(message.timestamp) }}
                </span>
                <span v-if="message.processingTime"
                      class="text-xs text-gray-400">
                  处理时间: {{ message.processingTime }}ms
                </span>
              </div>
            </div>
          </div>

          <!-- AI思考中状态 -->
          <div v-if="aiThinking"
               class="flex items-start space-x-3">
            <div class="flex-shrink-0 w-8 h-8 rounded-full bg-primary-100 flex items-center justify-center">
              <Bot class="h-5 w-5 text-primary-600" />
            </div>
            <div class="flex-1">
              <div class="bg-primary-50 rounded-lg p-3 max-w-md">
                <div class="flex items-center space-x-2">
                  <div class="loading-dots">
                    <span></span>
                    <span></span>
                    <span></span>
                  </div>
                  <span class="text-sm text-primary-600">AI正在思考...</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 控制按钮区 -->
      <div class="flex justify-center space-x-4 mb-6">
        <!-- 开始/结束会话 -->
        <button @click="toggleSession"
                :disabled="isProcessing || !selectedScenario"
                class="px-6 py-3 rounded-lg font-medium text-white transition-all duration-200 flex items-center space-x-2"
                :class="sessionActive ? 'bg-danger-600 hover:bg-danger-700' : 'bg-primary-600 hover:bg-primary-700'">
          <component :is="sessionActive ? Square : Play" class="h-5 w-5" />
          <span>{{ sessionActive ? '结束陪练' : '开始陪练' }}</span>
        </button>
        
        <!-- 清空对话 -->
        <button @click="clearMessages"
                :disabled="sessionActive || messages.length === 0"
                class="px-6 py-3 rounded-lg font-medium bg-gray-600 text-white hover:bg-gray-700 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2">
          <Trash2 class="h-5 w-5" />
          <span>清空对话</span>
        </button>
      </div>

      <!-- 语音录制控制 -->
      <div class="bg-white rounded-xl shadow-lg p-6">
        <div class="flex flex-col items-center space-y-4">
          <!-- 录音状态球 -->
          <div class="relative">
            <div class="w-20 h-20 rounded-full flex items-center justify-center transition-all duration-300"
                 :class="recordingBallClass"
                 @click="toggleRecording">
              <component :is="recordingIcon" 
                        class="h-8 w-8"
                        :class="recordingIconClass" />
            </div>
            
            <!-- 录音时长 -->
            <div v-if="isRecording"
                 class="absolute -bottom-6 left-1/2 transform -translate-x-1/2">
              <div class="bg-gray-900 text-white px-2 py-1 rounded-full text-xs font-mono">
                {{ formatDuration(recordingDuration) }}
              </div>
            </div>
          </div>
          
          <!-- 音量指示器 -->
          <div v-if="recorder"
               class="w-32 h-2 bg-gray-200 rounded-full overflow-hidden">
            <div class="h-full bg-primary-600 rounded-full transition-all duration-100"
                 :style="{ width: (audioLevel * 100) + '%' }"></div>
          </div>
          
          <!-- 录音提示 -->
          <p class="text-sm text-gray-600">
            {{ recordingHint }}
          </p>
        </div>
      </div>
    </div>

    <!-- 会话总结弹窗 -->
    <div v-if="showSummary"
         class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div class="bg-white rounded-xl shadow-2xl p-6 max-w-2xl w-full mx-4 max-h-[80vh] overflow-y-auto">
        <div class="flex items-center justify-between mb-6">
          <h2 class="text-2xl font-bold text-gray-900">陪练总结报告</h2>
          <button @click="showSummary = false"
                  class="text-gray-400 hover:text-gray-600">
            <X class="h-6 w-6" />
          </button>
        </div>
        
        <div v-if="sessionSummary"
             class="space-y-6">
          <!-- 基础统计 -->
          <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div class="bg-gray-50 rounded-lg p-4 text-center">
              <div class="text-2xl font-bold text-primary-600">{{ sessionSummary.totalMessages }}</div>
              <div class="text-sm text-gray-600">总对话数</div>
            </div>
            <div class="bg-gray-50 rounded-lg p-4 text-center">
              <div class="text-2xl font-bold text-success-600">{{ sessionSummary.successfulIdentifications }}</div>
              <div class="text-sm text-gray-600">成功识别</div>
            </div>
            <div class="bg-gray-50 rounded-lg p-4 text-center">
              <div class="text-2xl font-bold text-warning-600">{{ (sessionSummary.detectionRate * 100).toFixed(1) }}%</div>
              <div class="text-sm text-gray-600">识别率</div>
            </div>
            <div class="bg-gray-50 rounded-lg p-4 text-center">
              <div class="text-2xl font-bold text-info-600">{{ sessionSummary.performanceScore.toFixed(1) }}</div>
              <div class="text-sm text-gray-600">表现评分</div>
            </div>
          </div>
          
          <!-- 改进建议 -->
          <div>
            <h3 class="text-lg font-semibold text-gray-900 mb-3">改进建议</h3>
            <div class="space-y-2">
              <div v-for="suggestion in sessionSummary.improvementSuggestions"
                   :key="suggestion"
                   class="flex items-start space-x-2">
                <Lightbulb class="h-5 w-5 text-yellow-500 mt-0.5" />
                <span class="text-sm text-gray-700">{{ suggestion }}</span>
              </div>
            </div>
          </div>
          
          <!-- 学习要点 -->
          <div>
            <h3 class="text-lg font-semibold text-gray-900 mb-3">关键学习要点</h3>
            <div class="space-y-2">
              <div v-for="point in sessionSummary.keyLearningPoints"
                   :key="point"
                   class="flex items-start space-x-2">
                <CheckCircle class="h-5 w-5 text-success-500 mt-0.5" />
                <span class="text-sm text-gray-700">{{ point }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import AudioRecorder from '@/utils/Recorder'
import {
  MessageCircle,
  Bot,
  User,
  Square,
  Play,
  Trash2,
  AlertTriangle,
  X,
  Lightbulb,
  CheckCircle,
  Mic
} from 'lucide-vue-next'

// 状态管理
const selectedScenario = ref('')
const difficultyLevel = ref(1)
const sessionActive = ref(false)
const isProcessing = ref(false)
const aiThinking = ref(false)
const messages = ref<Array<{
  role: 'user' | 'assistant'
  content: string
  audioUrl?: string
  fraudIndicators?: string[]
  timestamp: Date
  processingTime?: number
}>>([])

const greetingMessage = ref('')
const showSummary = ref(false)
const sessionSummary = ref<any>(null)
const currentSessionId = ref('')
const localAudioUrls = ref<string[]>([])
const isSendingAudio = ref(false)

const AUDIO_ERROR_BACKOFF_MS = 4000
const ERROR_DEDUP_WINDOW_MS = 8000
let audioRetryAfter = 0
let lastErrorMessage = ''
let lastErrorTimestamp = 0

// 音频录制相关
const recorder = ref<AudioRecorder | null>(null)
const isRecording = ref(false)
const recordingDuration = ref(0)
const audioLevel = ref(0)
let recordingInterval: number | null = null

// AI状态
const aiStatus = computed(() => {
  if (aiThinking.value) return 'thinking'
  if (sessionActive.value) return 'listening'
  return 'idle'
})

const scenarioConfig = computed(() => {
  const configs = {
    impersonation: { name: '冒充公检法', icon: '👮' },
    investment: { name: '高回报投资', icon: '💰' },
    lottery: { name: '中奖诈骗', icon: '🎁' },
    customer_service: { name: '冒充客服', icon: '📞' }
  }
  return configs[selectedScenario.value as keyof typeof configs] || { name: '未选择', icon: '❓' }
})

const scenarioName = computed(() => scenarioConfig.value.name)

const difficultyText = computed(() => {
  const levels = ['简单', '普通', '困难', '专家', '大师']
  return levels[difficultyLevel.value - 1] || '未知'
})

const aiStatusText = computed(() => {
  const statusMap = {
    idle: '待机',
    listening: '监听中',
    thinking: '思考中'
  }
  return statusMap[aiStatus.value]
})

const aiStatusRingClass = computed(() => {
  const classMap = {
    idle: 'border-gray-300',
    listening: 'border-primary-300 animate-pulse-slow',
    thinking: 'border-yellow-300 animate-pulse-slow'
  }
  return classMap[aiStatus.value]
})

const aiStatusBallClass = computed(() => {
  const classMap = {
    idle: 'bg-gray-500',
    listening: 'bg-primary-500',
    thinking: 'bg-yellow-500'
  }
  return classMap[aiStatus.value]
})

const aiStatusIcon = computed(() => {
  const iconMap = {
    idle: Bot,
    listening: MessageCircle,
    thinking: AlertTriangle
  }
  return iconMap[aiStatus.value]
})

const aiIconClass = computed(() => {
  const classMap = {
    idle: 'text-white',
    listening: 'text-white',
    thinking: 'text-white'
  }
  return classMap[aiStatus.value]
})

const aiWaveClass = (index: number) => {
  return aiStatus.value === 'listening' ? 'animate-sound-wave' : ''
}

const aiWaveStyle = (index: number) => {
  const baseDelay = index * 200
  return {
    animationDelay: `${baseDelay}ms`,
    opacity: aiStatus.value === 'listening' ? 0.3 - index * 0.1 : 0
  }
}

// 录音相关
const recordingBallClass = computed(() => {
  if (!isRecording.value) return 'bg-gray-200 hover:bg-gray-300'
  if (audioLevel.value > 0.5) return 'bg-danger-500 animate-pulse'
  return 'bg-primary-600'
})

const recordingIcon = computed(() => {
  if (!isRecording.value) return Mic
  return Square
})

const recordingIconClass = computed(() => {
  if (!isRecording.value) return 'text-gray-500'
  if (audioLevel.value > 0.5) return 'text-white'
  return 'text-white'
})

const recordingHint = computed(() => {
  if (!sessionActive.value) return '请先开始陪练会话'
  if (isSendingAudio.value || aiThinking.value) return '正在上传并分析录音，请稍候'
  if (!isRecording.value) return '点击开始录音，再次点击结束并发送'
  if (audioLevel.value > 0.5) return '说话声音过大，请适当远离麦克风'
  return '正在录音中，点击麦克风停止并发送'
})

const revokeLocalAudioUrls = () => {
  for (const url of localAudioUrls.value) {
    URL.revokeObjectURL(url)
  }
  localAudioUrls.value = []
}

const pushAssistantErrorOnce = (content: string) => {
  const now = Date.now()
  if (content === lastErrorMessage && now - lastErrorTimestamp < ERROR_DEDUP_WINDOW_MS) {
    return
  }

  messages.value.push({
    role: 'assistant',
    content,
    timestamp: new Date(),
  })

  lastErrorMessage = content
  lastErrorTimestamp = now
  scrollToBottom()
}

// 方法
const initRecorder = async () => {
  try {
    recorder.value = new AudioRecorder({
      sampleRate: 16000,
      channels: 1,
      streaming: false,
      format: 'audio/webm',
      onAudioData: handleAudioData,
      onError: (error) => {
        console.error('录音错误:', error)
        stopRecording()
        alert('录音出现错误，请重试')
      }
    })

    await recorder.value.init()
    
    // 设置音量回调
    recorder.value.setVolumeCallback((level: number) => {
      audioLevel.value = level
    })
    
    console.log('AI陪练录音器初始化成功')
  } catch (error) {
    console.error('AI陪练录音器初始化失败:', error)
    alert('无法访问麦克风，请检查权限设置')
  }
}

const handleAudioData = async (blob: Blob) => {
  if (!sessionActive.value) return
  if (isSendingAudio.value) return

  const now = Date.now()
  if (now < audioRetryAfter) {
    return
  }

  try {
    isSendingAudio.value = true
    aiThinking.value = true
    const startTime = Date.now()

    // 发送音频到后端处理
    const formData = new FormData()
    formData.append('audio', blob)
    formData.append('session_id', currentSessionId.value || 'practice_session')

    const response = await fetch('/api/practice/audio', {
      method: 'POST',
      body: formData
    })

    if (!response.ok) {
      const detail = await response.text().catch(() => '')
      throw new Error(detail || `音频处理失败 (${response.status})`)
    }

    const result = await response.json()
    const processingTime = Date.now() - startTime
    audioRetryAfter = 0

    const hasTranscript = Boolean(result.transcript)
    const localAudioUrl = URL.createObjectURL(blob)
    localAudioUrls.value.push(localAudioUrl)

    // 添加用户消息
    if (hasTranscript) {
      messages.value.push({
        role: 'user',
        content: result.transcript,
        audioUrl: localAudioUrl,
        timestamp: new Date()
      })
    } else {
      messages.value.push({
        role: 'user',
        content: '已发送语音片段',
        audioUrl: localAudioUrl,
        timestamp: new Date()
      })
    }

    // 添加AI回复
    if (result.response) {
      messages.value.push({
        role: 'assistant',
        content: result.response.text,
        audioUrl: result.response.audio_url,
        fraudIndicators: result.response.fraud_indicators,
        timestamp: new Date(),
        processingTime
      })

      // 播放AI语音
      if (result.response.audio_url) {
        playAudioResponse(result.response.audio_url)
      }
    }

    scrollToBottom()
  } catch (error) {
    console.error('处理音频失败:', error)

    // 失败后短暂退避，避免每个录音切片都重复触发错误请求。
    audioRetryAfter = Date.now() + AUDIO_ERROR_BACKOFF_MS

    pushAssistantErrorOnce('抱歉，处理您的语音时出现错误，请重试。')
  } finally {
    isSendingAudio.value = false
    aiThinking.value = false
  }
}

const playAudioResponse = async (audioUrl: string) => {
  try {
    const audio = new Audio(audioUrl)
    await audio.play()
  } catch (error) {
    console.error('播放音频失败:', error)
  }
}

const toggleSession = async () => {
  isProcessing.value = true

  try {
    if (sessionActive.value) {
      // 结束会话
      const response = await fetch('/api/practice/session/end', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: currentSessionId.value || 'practice_session'
        })
      })

      if (response.ok) {
        sessionSummary.value = await response.json()
        showSummary.value = true
      } else {
        const errorDetail = await response.text()
        throw new Error(errorDetail || '结束会话失败')
      }

      sessionActive.value = false
      greetingMessage.value = ''
      currentSessionId.value = ''
    } else {
      // 开始会话
      const response = await fetch('/api/practice/session/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          scenario_type: selectedScenario.value,
          difficulty_level: Number(difficultyLevel.value),
          user_id: 1
        })
      })

      if (response.ok) {
        const result = await response.json()
        currentSessionId.value = result.session_id || 'practice_session'
        greetingMessage.value = result.greeting_message || '陪练会话已开始，请开始对话。'
        sessionActive.value = true
      } else {
        const errorDetail = await response.text()
        throw new Error(errorDetail || '开始会话失败')
      }
    }
  } catch (error) {
    console.error('会话操作失败:', error)
    alert(`操作失败，请重试。${error instanceof Error ? `\n${error.message}` : ''}`)
  } finally {
    isProcessing.value = false
  }
}

const toggleRecording = async () => {
  if (!recorder.value) {
    await initRecorder()
  }

  if (!sessionActive.value) {
    alert('请先开始陪练会话')
    return
  }

  if (isSendingAudio.value || aiThinking.value) {
    return
  }

  try {
    if (isRecording.value) {
      // 停止录音
      const audioBlob = await recorder.value?.stop()
      stopRecording()

      if (!audioBlob) {
        pushAssistantErrorOnce('未检测到有效录音，请重试。')
      }
    } else {
      // 开始录音
      await recorder.value?.start()
      startRecording()
    }
  } catch (error) {
    console.error('录音操作失败:', error)
    alert('录音失败，请重试')
  }
}

const startRecording = () => {
  isRecording.value = true
  recordingDuration.value = 0
  
  recordingInterval = setInterval(() => {
    recordingDuration.value += 1
  }, 1000)
}

const stopRecording = () => {
  isRecording.value = false
  audioLevel.value = 0
  
  if (recordingInterval) {
    clearInterval(recordingInterval)
    recordingInterval = null
  }
}

const clearMessages = () => {
  if (confirm('确定要清空所有对话记录吗？')) {
    revokeLocalAudioUrls()
    messages.value = []
    lastErrorMessage = ''
    lastErrorTimestamp = 0
    audioRetryAfter = 0
  }
}

const scrollToBottom = () => {
  nextTick(() => {
    const container = document.querySelector('.chat-container')
    if (container) {
      container.scrollTop = container.scrollHeight
    }
  })
}

const formatTime = (date: Date) => {
  return date.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

const formatDuration = (seconds: number) => {
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
}

// 生命周期
onMounted(async () => {
  await initRecorder()
})

onUnmounted(() => {
  recorder.value?.cleanup()
  revokeLocalAudioUrls()
  audioRetryAfter = 0
  if (recordingInterval) {
    clearInterval(recordingInterval)
  }
})

// 监听场景变化
watch(selectedScenario, (newScenario) => {
  if (newScenario && sessionActive.value) {
    if (confirm('切换场景将结束当前会话，是否继续？')) {
      toggleSession()
    }
  }
})
</script>

<style scoped>
.chat-container {
  scroll-behavior: smooth;
}

/* 移动端优化 */
@media (max-width: 768px) {
  .practice-container {
    padding: 1rem;
  }
  
  .ai-status-ball {
    width: 5rem;
    height: 5rem;
  }
}

/* 高对比度模式 */
@media (prefers-contrast: high) {
  .message-bubble {
    border-width: 1px;
  }
}

/* 减少动画模式 */
@media (prefers-reduced-motion: reduce) {
  .animate-sound-wave,
  .animate-pulse-slow {
    animation: none;
  }
}
</style>