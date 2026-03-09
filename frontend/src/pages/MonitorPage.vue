<template>
  <div class="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
    <!-- 头部控制区 -->
    <div class="bg-white shadow-sm border-b border-gray-200">
      <div class="max-w-4xl mx-auto px-4 py-4">
        <div class="flex items-center justify-between">
          <div class="flex items-center space-x-3">
            <Shield class="h-6 w-6 text-primary-600" />
            <div>
              <h1 class="text-xl font-semibold text-gray-900">实时通话监护</h1>
              <p class="text-sm text-gray-500">智能识别诈骗风险，保护通话安全</p>
            </div>
          </div>
          
          <div class="flex items-center space-x-2">
            <!-- 状态指示器 -->
            <div class="flex items-center space-x-2 px-3 py-2 rounded-lg"
                 :class="statusBgClass">
              <div class="w-2 h-2 rounded-full animate-pulse"
                   :class="statusDotClass"></div>
              <span class="text-sm font-medium"
                    :class="statusTextClass">
                {{ statusText }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 主要监控区域 -->
    <div class="max-w-4xl mx-auto px-4 py-6">
      <!-- 动态波形球 -->
      <div class="flex justify-center mb-8">
        <div class="relative">
          <!-- 外圈动画 -->
          <div class="absolute inset-0 rounded-full border-4"
               :class="pulseRingClass">
          </div>
          
          <!-- 中心状态球 -->
          <div class="relative w-32 h-32 rounded-full flex items-center justify-center transition-all duration-300"
               :class="centerBallClass">
            <!-- 状态图标 -->
            <component :is="statusIcon" 
                      class="h-12 w-12 transition-all duration-300"
                      :class="iconClass" />
            
            <!-- 音频波形指示器 -->
            <div class="absolute inset-0 rounded-full overflow-hidden">
              <div v-for="i in 3"
                   :key="i"
                   class="absolute inset-0 rounded-full border border-white/20"
                   :class="waveClass(i)"
                   :style="waveStyle(i)"></div>
            </div>
          </div>
          
          <!-- 风险等级环 -->
          <div class="absolute -bottom-2 left-1/2 transform -translate-x-1/2">
            <div class="px-3 py-1 rounded-full text-xs font-semibold"
                 :class="riskRingClass">
              {{ riskLevelText }}
            </div>
          </div>
        </div>
      </div>

      <!-- 实时转录文本 -->
      <div class="bg-white rounded-xl shadow-lg p-6 mb-6">
        <div class="flex items-center justify-between mb-4">
          <h2 class="text-lg font-semibold text-gray-900 flex items-center">
            <FileText class="h-5 w-5 mr-2 text-primary-600" />
            实时转录
          </h2>
          <div class="flex items-center space-x-2 text-sm text-gray-500">
            <Clock class="h-4 w-4" />
            <span>{{ formatDuration(recordingDuration) }}</span>
          </div>
        </div>
        
        <div class="space-y-3 max-h-48 overflow-y-auto">
          <div v-for="(item, index) in transcriptionHistory"
               :key="index"
               class="flex items-start space-x-3 p-3 rounded-lg transition-all duration-200"
               :class="item.riskScore > 50 ? 'bg-danger-50 border border-danger-200' : 'bg-gray-50'">
            <div class="flex-shrink-0">
              <div class="w-2 h-2 rounded-full"
                   :class="item.riskScore > 50 ? 'bg-danger-500' : 'bg-success-500'"></div>
            </div>
            <div class="flex-1">
              <p class="text-sm text-gray-900">{{ item.text }}</p>
              <div class="flex items-center space-x-4 mt-1">
                <span class="text-xs text-gray-500">
                  {{ formatTime(item.timestamp) }}
                </span>
                <span class="text-xs px-2 py-1 rounded-full font-medium"
                      :class="getRiskBadgeClass(item.riskScore)">
                  风险: {{ item.riskScore }}%
                </span>
              </div>
            </div>
          </div>
        </div>
        
        <div v-if="transcriptionHistory.length === 0"
             class="text-center py-8 text-gray-500">
          <Mic class="h-8 w-8 mx-auto mb-2 opacity-50" />
          <p class="text-sm">{{ transcriptEmptyMessage }}</p>
        </div>
      </div>

      <!-- 风险分析面板 -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        <!-- 风险指标 -->
        <div class="bg-white rounded-xl shadow-lg p-6">
          <h3 class="text-lg font-semibold text-gray-900 mb-4 flex items-center">
            <BarChart3 class="h-5 w-5 mr-2 text-primary-600" />
            风险指标
          </h3>
          
          <div class="space-y-4">
            <div v-for="indicator in riskIndicators"
                 :key="indicator.name"
                 class="flex items-center justify-between">
              <span class="text-sm text-gray-600">{{ indicator.name }}</span>
              <div class="flex items-center space-x-2">
                <div class="w-24 bg-gray-200 rounded-full h-2">
                  <div class="h-2 rounded-full transition-all duration-500"
                       :class="indicator.colorClass"
                       :style="{ width: indicator.value + '%' }"></div>
                </div>
                <span class="text-sm font-medium"
                      :class="indicator.textColorClass">
                  {{ indicator.value }}%
                </span>
              </div>
            </div>
          </div>
        </div>

        <!-- 检测到的诈骗特征 -->
        <div class="bg-white rounded-xl shadow-lg p-6">
          <h3 class="text-lg font-semibold text-gray-900 mb-4 flex items-center">
            <AlertTriangle class="h-5 w-5 mr-2 text-primary-600" />
            诈骗特征
          </h3>
          
          <div class="space-y-2">
            <div v-for="feature in detectedFeatures"
                 :key="feature"
                 class="flex items-center space-x-2 px-3 py-2 rounded-lg bg-danger-50 border border-danger-200">
              <X class="h-4 w-4 text-danger-600" />
              <span class="text-sm text-danger-800">{{ feature }}</span>
            </div>
          </div>
          
          <div v-if="detectedFeatures.length === 0"
               class="text-center py-4 text-gray-500">
            <Shield class="h-8 w-8 mx-auto mb-2 opacity-50" />
            <p class="text-sm">未检测到诈骗特征</p>
          </div>
        </div>
      </div>

      <!-- 控制按钮 -->
      <div class="flex justify-center space-x-4">
        <button @click="toggleMonitoring"
                :disabled="isProcessing"
                class="px-6 py-3 rounded-lg font-medium text-white transition-all duration-200 flex items-center space-x-2"
                :class="isMonitoring ? 'bg-danger-600 hover:bg-danger-700' : 'bg-primary-600 hover:bg-primary-700'">
          <component :is="isMonitoring ? Square : Mic" class="h-5 w-5" />
          <span>{{ isMonitoring ? '停止监护' : '开始监护' }}</span>
        </button>
        
        <button @click="clearHistory"
                :disabled="isMonitoring || transcriptionHistory.length === 0"
                class="px-6 py-3 rounded-lg font-medium bg-gray-600 text-white hover:bg-gray-700 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2">
          <Trash2 class="h-5 w-5" />
          <span>清除记录</span>
        </button>
      </div>
    </div>

    <!-- 诈骗警报弹窗 -->
    <div v-if="showAlert"
         class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div class="bg-white rounded-xl shadow-2xl p-6 max-w-md w-full mx-4 animate-pulse">
        <div class="flex items-center space-x-3 mb-4">
          <div class="w-12 h-12 bg-danger-100 rounded-full flex items-center justify-center">
            <AlertTriangle class="h-6 w-6 text-danger-600" />
          </div>
          <div>
            <h3 class="text-lg font-semibold text-danger-900">诈骗风险警报！</h3>
            <p class="text-sm text-danger-700">检测到高风险诈骗行为</p>
          </div>
        </div>
        
        <div class="space-y-3 mb-6">
          <div v-for="warning in alertWarnings"
               :key="warning"
               class="flex items-start space-x-2">
            <ChevronRight class="h-4 w-4 text-danger-600 mt-0.5" />
            <span class="text-sm text-gray-700">{{ warning }}</span>
          </div>
        </div>
        
        <div class="flex space-x-3">
          <button @click="dismissAlert"
                  class="flex-1 px-4 py-2 bg-danger-600 text-white rounded-lg font-medium hover:bg-danger-700 transition-colors">
            我已了解
          </button>
          <button @click="vibrateAndCall"
                  class="flex-1 px-4 py-2 bg-primary-600 text-white rounded-lg font-medium hover:bg-primary-700 transition-colors">
            紧急联系
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import AudioRecorder from '@/utils/Recorder'
import { WebSocketManager, WebSocketStatus } from '@/utils/WebSocketManager'
import {
  Shield,
  Mic,
  Square,
  FileText,
  Clock,
  AlertTriangle,
  X,
  BarChart3,
  ChevronRight,
  Trash2
} from 'lucide-vue-next'

// 状态管理
const isMonitoring = ref(false)
const isProcessing = ref(false)
const recordingDuration = ref(0)
const currentRiskScore = ref(0)
const showAlert = ref(false)
const transcriptionHistory = ref<Array<{
  text: string
  timestamp: Date
  riskScore: number
}>>([])
const detectedIndicators = ref<string[]>([])
const wsStatus = ref<WebSocketStatus>(WebSocketStatus.CLOSED)
const sessionId = ref<string>('')
const analysisFrameCount = ref(0)
const emptyTranscriptCount = ref(0)
const MONITOR_SEGMENT_MS = 2500
const TRANSCRIPT_MERGE_GAP_MS = 6000
const TRANSCRIPT_BLOCK_MAX_LENGTH = 180
const FRAUD_CATEGORY_LABELS: Record<string, string> = {
  urgency: '紧迫施压',
  authority: '权威身份',
  money: '转账汇款',
  threat: '威胁恐吓',
  bait: '利益诱导',
  impersonation: '身份冒充',
}

// 音频录制器
let recorder: AudioRecorder | null = null
let monitoringInterval: number | null = null
let wsManager: WebSocketManager | null = null
let segmentInterval: number | null = null
let segmentFlushInProgress = false

const forceStopMonitoring = () => {
  if (isMonitoring.value) {
    try {
      recorder?.stop()
    } catch (error) {
      console.error('停止录制失败:', error)
    }
  }

  stopMonitoringTimer()
  stopSegmentCapture()
  isMonitoring.value = false
  isProcessing.value = false
}

// 计算属性
const statusText = computed(() => {
  if (isMonitoring.value) {
    if (wsStatus.value === WebSocketStatus.OPEN) return '监听中'
    if (wsStatus.value === WebSocketStatus.RECONNECTING) return '重连中'
    return '连接中'
  }
  if (isProcessing.value) return '处理中'
  return '待机'
})

const statusBgClass = computed(() => {
  if (currentRiskScore.value > 70) return 'bg-danger-100'
  if (currentRiskScore.value > 30) return 'bg-yellow-100'
  return 'bg-success-100'
})

const statusDotClass = computed(() => {
  if (currentRiskScore.value > 70) return 'bg-danger-500'
  if (currentRiskScore.value > 30) return 'bg-yellow-500'
  return 'bg-success-500'
})

const statusTextClass = computed(() => {
  if (currentRiskScore.value > 70) return 'text-danger-800'
  if (currentRiskScore.value > 30) return 'text-yellow-800'
  return 'text-success-800'
})

const statusIcon = computed(() => {
  if (currentRiskScore.value > 70) return AlertTriangle
  if (isMonitoring.value) return Mic
  return Shield
})

const iconClass = computed(() => {
  if (currentRiskScore.value > 70) return 'text-danger-600'
  if (isMonitoring.value) return 'text-primary-600'
  return 'text-gray-400'
})

const centerBallClass = computed(() => {
  if (currentRiskScore.value > 70) return 'bg-danger-500 animate-alert-flash'
  if (currentRiskScore.value > 30) return 'bg-yellow-500'
  return 'bg-success-500'
})

const pulseRingClass = computed(() => {
  if (isMonitoring.value) {
    if (currentRiskScore.value > 70) return 'border-danger-300 animate-pulse-slow'
    return 'border-success-300 animate-pulse-slow'
  }
  return 'border-gray-300'
})

const riskLevelText = computed(() => {
  if (currentRiskScore.value > 70) return '高风险'
  if (currentRiskScore.value > 30) return '中风险'
  return '安全'
})

const riskRingClass = computed(() => {
  if (currentRiskScore.value > 70) return 'bg-danger-600 text-white'
  if (currentRiskScore.value > 30) return 'bg-yellow-600 text-white'
  return 'bg-success-600 text-white'
})

const riskIndicators = computed(() => [
  {
    name: '语音压力',
    value: Math.min(currentRiskScore.value * 0.8, 100),
    colorClass: 'bg-primary-500',
    textColorClass: 'text-primary-700'
  },
  {
    name: '紧急程度',
    value: Math.min(currentRiskScore.value * 1.2, 100),
    colorClass: 'bg-danger-500',
    textColorClass: 'text-danger-700'
  },
  {
    name: '操纵性',
    value: Math.min(currentRiskScore.value * 0.6, 100),
    colorClass: 'bg-yellow-500',
    textColorClass: 'text-yellow-700'
  },
  {
    name: '一致性',
    value: Math.max(100 - currentRiskScore.value * 0.5, 0),
    colorClass: 'bg-success-500',
    textColorClass: 'text-success-700'
  }
])

const detectedFeatures = computed(() => {
  if (detectedIndicators.value.length > 0) {
    return detectedIndicators.value
  }

  const features = []
  if (currentRiskScore.value > 30) features.push('使用紧急性词汇')
  if (currentRiskScore.value > 50) features.push('官方身份冒充')
  if (currentRiskScore.value > 70) features.push('要求转账汇款')
  return features
})

const alertWarnings = computed(() => {
  const warnings = []
  if (currentRiskScore.value > 50) warnings.push('检测到官方身份冒充嫌疑')
  if (currentRiskScore.value > 70) warnings.push('要求转账或提供个人信息')
  if (currentRiskScore.value > 80) warnings.push('使用威胁性语言')
  return warnings
})

const transcriptEmptyMessage = computed(() => {
  if (transcriptionHistory.value.length > 0) return ''
  if (!isMonitoring.value) return '等待音频输入...'
  if (analysisFrameCount.value > 0 || emptyTranscriptCount.value > 0) {
    return '已收到音频，但暂未识别出清晰语音，请连续说 2 到 3 秒并靠近麦克风'
  }
  if (recordingDuration.value >= 3) {
    return '正在接收音频并等待首条转录结果...'
  }
  return '等待音频输入...'
})

const buildWsUrl = (monitoringSessionId: string) => {
  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
  const host = window.location.host
  const query = new URLSearchParams({
    session_id: monitoringSessionId,
  })
  return `${protocol}://${host}/ws/audio/monitoring?${query.toString()}`
}

const createMonitoringSession = async () => {
  const response = await fetch('/api/monitoring/session', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      sensitivity_level: 'medium',
      alert_types: ['voice_biometrics', 'behavioral', 'content'],
      auto_record: true,
    }),
  })

  if (!response.ok) {
    const errorDetail = await response.text()
    throw new Error(errorDetail || '创建监护会话失败')
  }

  const result = await response.json()
  const monitoringSessionId = typeof result?.session_id === 'string' ? result.session_id : ''
  if (!monitoringSessionId) {
    throw new Error('监护会话响应缺少 session_id')
  }

  sessionId.value = monitoringSessionId
  return monitoringSessionId
}

const initWebSocket = async () => {
  if (wsManager) return

  const monitoringSessionId = sessionId.value || await createMonitoringSession()

  wsManager = new WebSocketManager({
    url: buildWsUrl(monitoringSessionId),
    reconnectInterval: 2500,
    maxReconnectAttempts: 8,
    heartbeatInterval: 0,
    onStatusChange: (status) => {
      wsStatus.value = status
    },
    onClose: () => {
      if (isMonitoring.value) {
        forceStopMonitoring()
      }
    },
    onMessage: (event) => {
      try {
        const payload = JSON.parse(event.data)
        handleWsMessage(payload)
      } catch (error) {
        console.error('解析WebSocket消息失败:', error)
      }
    },
    onError: () => {
      console.error('监护WebSocket发生错误')
      if (isMonitoring.value) {
        forceStopMonitoring()
      }
    }
  })

  await wsManager.connect()
}

const disconnectWebSocket = () => {
  wsManager?.disconnect()
  wsManager = null
  wsStatus.value = WebSocketStatus.CLOSED
  sessionId.value = ''
}

const normalizeTranscriptText = (text: string) => text.replace(/\s+/g, ' ').trim()

const mergeTranscriptText = (baseText: string, nextText: string) => {
  const normalizedBase = normalizeTranscriptText(baseText)
  const normalizedNext = normalizeTranscriptText(nextText)

  if (!normalizedBase) return normalizedNext
  if (!normalizedNext) return normalizedBase
  if (normalizedBase.endsWith(normalizedNext) || normalizedBase.includes(normalizedNext)) {
    return normalizedBase
  }

  const maxOverlap = Math.min(normalizedBase.length, normalizedNext.length)
  for (let overlap = maxOverlap; overlap > 1; overlap -= 1) {
    if (normalizedBase.slice(-overlap) === normalizedNext.slice(0, overlap)) {
      return normalizedBase + normalizedNext.slice(overlap)
    }
  }

  const needsSpace = /[A-Za-z0-9]$/.test(normalizedBase) && /^[A-Za-z0-9]/.test(normalizedNext)
  return normalizedBase + (needsSpace ? ' ' : '') + normalizedNext
}

const formatDetectedIndicator = (indicator: unknown) => {
  if (typeof indicator !== 'string') return ''

  const [category, keyword] = indicator.split(':', 2)
  const categoryLabel = FRAUD_CATEGORY_LABELS[category]
  if (!categoryLabel) return indicator
  if (!keyword) return categoryLabel
  return `${categoryLabel}: ${keyword}`
}

const appendTranscriptHistory = (segmentText: string, riskScore: number) => {
  const normalizedSegment = normalizeTranscriptText(segmentText)
  if (!normalizedSegment) return

  const now = new Date()
  const latestItem = transcriptionHistory.value[0]
  if (latestItem) {
    const gapMs = now.getTime() - latestItem.timestamp.getTime()
    const mergedText = mergeTranscriptText(latestItem.text, normalizedSegment)
    const canMerge = (
      gapMs <= TRANSCRIPT_MERGE_GAP_MS
      && latestItem.text.length < TRANSCRIPT_BLOCK_MAX_LENGTH
      && mergedText.length <= TRANSCRIPT_BLOCK_MAX_LENGTH
    )

    if (canMerge) {
      transcriptionHistory.value = [
        {
          text: mergedText,
          timestamp: now,
          riskScore: Math.max(latestItem.riskScore, riskScore),
        },
        ...transcriptionHistory.value.slice(1),
      ]
      return
    }
  }

  transcriptionHistory.value = [
    {
      text: normalizedSegment,
      timestamp: now,
      riskScore,
    },
    ...transcriptionHistory.value,
  ].slice(0, 20)
}

const handleWsMessage = (payload: any) => {
  const messageType = payload?.type

  if (messageType === 'connection_established') {
    sessionId.value = payload?.session_id || ''
    return
  }

  if (messageType === 'risk_analysis') {
    const data = payload?.data || {}
    const score = Number(data?.risk_score || 0)
    currentRiskScore.value = Math.max(0, Math.min(100, score))
    analysisFrameCount.value += 1
    detectedIndicators.value = Array.isArray(data?.fraud_indicators)
      ? data.fraud_indicators
          .map((indicator: unknown) => formatDetectedIndicator(indicator))
          .filter((indicator: string) => indicator.length > 0)
          .slice(0, 6)
      : []

    const transcript = typeof data?.transcript === 'string' ? data.transcript.trim() : ''
    if (transcript) {
      emptyTranscriptCount.value = 0
      appendTranscriptHistory(transcript, currentRiskScore.value)
    } else if (Number(data?.processing_time_ms || 0) > 0) {
      emptyTranscriptCount.value += 1
    }
    return
  }

  if (messageType === 'fraud_alert') {
    const score = Number(payload?.data?.risk_score || currentRiskScore.value)
    currentRiskScore.value = Math.max(currentRiskScore.value, score)
    showAlert.value = true
    vibrateDevice()
    return
  }

  if (messageType === 'error') {
    console.error('监护后端错误:', payload?.message || payload)
    alert(payload?.message || '监护服务异常，请稍后重试')
    forceStopMonitoring()
    disconnectWebSocket()
    return
  }
}

// 方法
const initRecorder = async () => {
  try {
    recorder = new AudioRecorder({
      sampleRate: 16000,
      channels: 1,
      streaming: false,
      format: 'audio/webm',
      onError: (error) => {
        console.error('录制错误:', error)
        isProcessing.value = false
        isMonitoring.value = false
      }
    })

    await recorder.init()
    console.log('音频录制器初始化成功')
  } catch (error) {
    console.error('音频录制器初始化失败:', error)
    alert('无法访问麦克风，请检查权限设置')
  }
}

const sendMonitoringAudio = (blob: Blob) => {
  if (!blob || blob.size === 0 || !wsManager) return

  if (!wsManager.isConnected()) {
    return
  }

  wsManager.send(blob)
}

const flushCurrentSegment = async () => {
  if (!recorder || segmentFlushInProgress) return

  const recorderState = recorder.getState()
  if (!recorderState.isRecording) return

  segmentFlushInProgress = true
  try {
    const audioBlob = await recorder.stop()
    if (audioBlob && audioBlob.size > 0) {
      sendMonitoringAudio(audioBlob)
    }
  } finally {
    segmentFlushInProgress = false
  }
}

const startSegmentCapture = async () => {
  if (!recorder) return

  stopSegmentCapture()
  await recorder.start()

  segmentInterval = window.setInterval(async () => {
    if (!isMonitoring.value || !recorder || segmentFlushInProgress) {
      return
    }

    await flushCurrentSegment()

    if (isMonitoring.value && recorder && !recorder.getState().isRecording) {
      try {
        await recorder.start()
      } catch (error) {
        console.error('重启监护录制失败:', error)
        forceStopMonitoring()
      }
    }
  }, MONITOR_SEGMENT_MS)
}

const stopSegmentCapture = () => {
  if (segmentInterval) {
    clearInterval(segmentInterval)
    segmentInterval = null
  }
}

const finalizeSegmentCapture = async () => {
  stopSegmentCapture()
  await flushCurrentSegment()
}

const toggleMonitoring = async () => {
  isProcessing.value = true

  try {
    if (!recorder) {
      await initRecorder()
    }

    if (isMonitoring.value) {
      // 停止监护
      stopMonitoringTimer()
      await finalizeSegmentCapture()
      disconnectWebSocket()
      isMonitoring.value = false
      currentRiskScore.value = 0
    } else {
      // 开始监护
      showAlert.value = false
      analysisFrameCount.value = 0
      emptyTranscriptCount.value = 0
      await initWebSocket()
      isMonitoring.value = true
      await startSegmentCapture()
      startMonitoringTimer()
    }
  } catch (error) {
    console.error('切换监护状态失败:', error)
    alert('操作失败，请重试')
  } finally {
    isProcessing.value = false
  }
}

const startMonitoringTimer = () => {
  recordingDuration.value = 0
  monitoringInterval = setInterval(() => {
    recordingDuration.value += 1
  }, 1000)
}

const stopMonitoringTimer = () => {
  if (monitoringInterval) {
    clearInterval(monitoringInterval)
    monitoringInterval = null
  }
}

const clearHistory = () => {
  transcriptionHistory.value = []
  detectedIndicators.value = []
  currentRiskScore.value = 0
  analysisFrameCount.value = 0
  emptyTranscriptCount.value = 0
}

const dismissAlert = () => {
  showAlert.value = false
}

const vibrateAndCall = () => {
  vibrateDevice()
  // 这里可以添加紧急联系功能
  alert('正在连接紧急联系人...')
  dismissAlert()
}

const vibrateDevice = () => {
  // 触发手机震动
  if ('vibrate' in navigator) {
    navigator.vibrate([200, 100, 200, 100, 200])
  }
}

const formatDuration = (seconds: number) => {
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
}

const formatTime = (date: Date) => {
  return date.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

const getRiskBadgeClass = (score: number) => {
  if (score > 70) return 'bg-danger-100 text-danger-800'
  if (score > 30) return 'bg-yellow-100 text-yellow-800'
  return 'bg-success-100 text-success-800'
}

const waveClass = (index: number) => {
  const baseDelay = index * 200
  return `animate-sound-wave`
}

const waveStyle = (index: number) => {
  const baseDelay = index * 200
  return {
    animationDelay: `${baseDelay}ms`,
    opacity: 0.3 - index * 0.1
  }
}

// 生命周期
onMounted(async () => {
  await initRecorder()
})

onUnmounted(() => {
  stopSegmentCapture()
  recorder?.cleanup()
  stopMonitoringTimer()
  disconnectWebSocket()
})
</script>

<style scoped>
.animate-alert-flash {
  animation: alertFlash 0.5s ease-in-out infinite;
}

@keyframes alertFlash {
  0%, 100% {
    transform: scale(1);
    box-shadow: 0 0 10px rgba(239, 68, 68, 0.5);
  }
  50% {
    transform: scale(1.05);
    box-shadow: 0 0 30px rgba(239, 68, 68, 0.8);
  }
}

/* 移动端优化 */
@media (max-width: 768px) {
  .monitor-container {
    padding: 1rem;
  }
  
  .center-ball {
    width: 6rem;
    height: 6rem;
  }
}

/* 高对比度模式 */
@media (prefers-contrast: high) {
  .status-indicator {
    border-width: 2px;
  }
}

/* 减少动画模式 */
@media (prefers-reduced-motion: reduce) {
  .animate-pulse-slow,
  .animate-sound-wave,
  .animate-alert-flash {
    animation: none;
  }
}
</style>