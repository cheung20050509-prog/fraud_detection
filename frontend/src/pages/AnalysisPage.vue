<template>
  <div class="min-h-screen bg-gradient-to-br from-green-50 to-blue-100">
    <!-- 头部控制区 -->
    <header class="bg-white shadow-sm border-b border-gray-200">
      <div class="max-w-4xl mx-auto px-4 py-4">
        <div class="flex items-center justify-between">
          <div class="flex items-center space-x-3">
            <FileText class="h-6 w-6 text-primary-600" />
            <div>
              <h1 class="text-xl font-semibold text-gray-900">案例分析</h1>
              <p class="text-sm text-gray-500">上传音频或文本文件进行诈骗风险分析</p>
            </div>
          </div>
        </div>
      </div>
    </header>

    <!-- 主内容区域 -->
    <div class="max-w-4xl mx-auto px-4 py-6">
      <!-- 文件上传区域 -->
      <div class="bg-white rounded-xl shadow-lg p-8 mb-6">
        <div class="text-center mb-8">
          <div class="mx-auto w-24 h-24 bg-primary-100 rounded-full flex items-center justify-center mb-4">
            <Upload class="h-12 w-12 text-primary-600" />
          </div>
          <h2 class="text-2xl font-bold text-gray-900 mb-2">上传文件进行分析</h2>
          <p class="text-gray-600">支持音频文件 (.mp3, .wav, .m4a) 和文本文件 (.txt)</p>
          <p class="text-sm text-gray-500 mt-1">最大文件大小: 50MB</p>
        </div>

        <!-- 拖拽上传区域 -->
        <div class="relative border-2 border-dashed rounded-xl p-12 text-center transition-all duration-200"
             :class="uploadAreaClass"
             @drop="handleDrop"
             @dragover="handleDragOver"
             @dragleave="handleDragLeave"
             @click="triggerFileInput">
          
          <!-- 上传状态图标 -->
          <div class="mb-4">
            <component :is="uploadIcon" 
                      class="h-16 w-16 mx-auto transition-all duration-300"
                      :class="uploadIconClass" />
          </div>

          <!-- 上传提示文本 -->
          <div class="space-y-2">
            <p class="text-lg font-medium" :class="uploadTextClass">
              {{ uploadStatusText }}
            </p>
            <p class="text-sm text-gray-500">
              或点击选择文件
            </p>
          </div>

          <!-- 进度条 -->
          <div v-if="uploadProgress > 0 && uploadProgress < 100"
               class="mt-6">
            <div class="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
              <div class="bg-primary-600 h-3 rounded-full transition-all duration-300"
                   :style="{ width: uploadProgress + '%' }"></div>
            </div>
            <p class="text-sm text-gray-600 mt-2">
              {{ uploadProgress }}% - {{ formatFileSize(uploadingFileSize) }}
            </p>
          </div>

          <!-- 隐藏的文件输入 -->
          <input ref="fileInput"
                 id="fileInput"
                 type="file"
                 class="hidden"
                 :accept="acceptTypes"
                 :multiple="false"
                 @change="handleFileSelect"
                 :disabled="uploading">
        </div>

        <!-- 支持的文件类型 -->
        <div class="mt-8 grid grid-cols-2 md:grid-cols-4 gap-4">
          <div v-for="type in supportedFileTypes"
               :key="type.extension"
               class="flex items-center space-x-2 p-3 rounded-lg bg-gray-50">
            <component :is="type.icon" class="h-5 w-5 text-gray-600" />
            <div>
              <p class="text-sm font-medium text-gray-900">{{ type.name }}</p>
              <p class="text-xs text-gray-500">{{ type.extension }}</p>
            </div>
          </div>
        </div>
      </div>

      <!-- 分析结果区域 -->
      <div v-if="analysisResult"
           class="bg-white rounded-xl shadow-lg p-6 mb-6">
        <div class="flex items-center justify-between mb-6">
          <h3 class="text-xl font-semibold text-gray-900 flex items-center">
            <BarChart3 class="h-5 w-5 mr-2 text-primary-600" />
            分析结果
          </h3>
          <div class="flex items-center space-x-2">
            <span class="text-sm text-gray-500">
              处理时间: {{ analysisResult.processingTime }}ms
            </span>
            <button @click="clearResult"
                    class="text-gray-400 hover:text-gray-600">
              <X class="h-5 w-5" />
            </button>
          </div>
        </div>

        <!-- 风险等级概览 -->
        <div class="mb-6">
          <div class="flex items-center justify-center mb-4">
            <div class="relative">
              <!-- 风险等级圆环 -->
              <div class="w-32 h-32 rounded-full flex items-center justify-center border-8"
                   :class="riskRingClass">
                <div class="text-center">
                  <div class="text-3xl font-bold" :class="riskScoreClass">
                    {{ analysisResult.riskScore }}
                  </div>
                  <div class="text-sm font-medium" :class="riskLevelClass">
                    {{ riskLevelText }}
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 风险描述 -->
          <div class="text-center">
            <p class="text-gray-700">{{ riskDescription }}</p>
          </div>
        </div>

        <!-- 详细分析数据 -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <!-- 检测到的诈骗类型 -->
          <div class="space-y-3">
            <h4 class="text-lg font-semibold text-gray-900 mb-3">诈骗类型分析</h4>
            <div class="space-y-2">
              <div v-for="(type, index) in analysisResult.fraudTypes"
                   :key="index"
                   class="flex items-center justify-between p-3 rounded-lg"
                   :class="type.confidence > 70 ? 'bg-danger-50' : 'bg-yellow-50'">
                <div class="flex items-center space-x-2">
                  <component :is="type.icon" 
                            class="h-4 w-4"
                            :class="type.confidence > 70 ? 'text-danger-600' : 'text-yellow-600'" />
                  <span class="text-sm font-medium">{{ type.name }}</span>
                </div>
                <span class="text-sm font-semibold"
                      :class="type.confidence > 70 ? 'text-danger-800' : 'text-yellow-800'">
                  {{ type.confidence }}%
                </span>
              </div>
            </div>
          </div>

          <!-- 诈骗关键词和特征 -->
          <div class="space-y-3">
            <h4 class="text-lg font-semibold text-gray-900 mb-3">关键特征检测</h4>
            <div class="space-y-2">
              <div v-for="feature in analysisResult.keyFeatures"
                   :key="feature.name"
                   class="p-3 rounded-lg bg-gray-50">
                <div class="flex items-center justify-between mb-2">
                  <span class="text-sm font-medium text-gray-900">{{ feature.name }}</span>
                  <span class="text-sm px-2 py-1 rounded-full font-medium"
                        :class="feature.severity === 'high' ? 'bg-danger-100 text-danger-800' : 
                               feature.severity === 'medium' ? 'bg-yellow-100 text-yellow-800' : 
                               'bg-blue-100 text-blue-800'">
                    {{ feature.severityText }}
                  </span>
                </div>
                <p class="text-xs text-gray-600">{{ feature.description }}</p>
              </div>
            </div>
          </div>
        </div>

        <!-- 文件转录内容（如果有） -->
        <div v-if="analysisResult.transcript"
             class="mt-6 p-4 bg-gray-50 rounded-lg">
          <h4 class="text-lg font-semibold text-gray-900 mb-3">转录内容</h4>
          <div class="bg-white p-4 rounded border border-gray-200 max-h-48 overflow-y-auto">
            <p class="text-sm text-gray-700 whitespace-pre-wrap">{{ analysisResult.transcript }}</p>
          </div>
        </div>

        <!-- 建议和措施 -->
        <div class="mt-6 p-4 bg-blue-50 rounded-lg">
          <h4 class="text-lg font-semibold text-blue-900 mb-3 flex items-center">
            <Lightbulb class="h-5 w-5 mr-2" />
            防范建议
          </h4>
          <div class="space-y-2">
            <div v-for="suggestion in analysisResult.suggestions"
                 :key="suggestion"
                 class="flex items-start space-x-2">
              <CheckCircle class="h-4 w-4 text-blue-600 mt-0.5" />
              <span class="text-sm text-blue-800">{{ suggestion }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 历史记录 -->
      <div class="bg-white rounded-xl shadow-lg p-6">
        <div class="flex items-center justify-between mb-6">
          <h3 class="text-xl font-semibold text-gray-900 flex items-center">
            <History class="h-5 w-5 mr-2 text-primary-600" />
            分析历史
          </h3>
          <button @click="clearHistory"
                  :disabled="analysisHistory.length === 0"
                  class="px-3 py-2 text-sm text-gray-600 hover:text-gray-800 disabled:opacity-50 disabled:cursor-not-allowed">
            清空历史
          </button>
        </div>

        <div v-if="analysisHistory.length === 0"
             class="text-center py-8 text-gray-500">
          <FileText class="h-8 w-8 mx-auto mb-2 opacity-50" />
          <p class="text-sm">暂无分析记录</p>
        </div>

        <div v-else
             class="space-y-4">
          <div v-for="(record, index) in analysisHistory"
               :key="index"
               class="flex items-center justify-between p-4 rounded-lg border border-gray-200 hover:border-primary-300 transition-colors">
            
            <!-- 文件信息 -->
            <div class="flex-1">
              <div class="flex items-center space-x-2 mb-1">
                <component :is="getFileIcon(record.fileType)" 
                          class="h-4 w-4 text-gray-600" />
                <span class="text-sm font-medium text-gray-900">{{ record.fileName }}</span>
                <span class="text-xs text-gray-500">{{ formatFileSize(record.fileSize) }}</span>
              </div>
              <div class="flex items-center space-x-4 text-xs text-gray-500">
                <span>{{ formatDateTime(record.analyzedAt) }}</span>
                <span>风险: {{ record.riskScore }}</span>
              </div>
            </div>

            <!-- 操作按钮 -->
            <div class="flex items-center space-x-2">
              <button @click="viewHistoryResult(record)"
                      class="px-3 py-1 text-sm bg-primary-100 text-primary-700 rounded hover:bg-primary-200 transition-colors">
                查看详情
              </button>
              <button @click="deleteHistoryRecord(index)"
                      class="px-3 py-1 text-sm bg-danger-100 text-danger-700 rounded hover:bg-danger-200 transition-colors">
                删除
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import {
  FileText,
  Upload,
  X,
  BarChart3,
  Lightbulb,
  CheckCircle,
  History,
  Music,
  File,
  AlertTriangle,
  Shield,
  DollarSign,
  Phone,
  UserCheck
} from 'lucide-vue-next'

// 状态管理
const uploading = ref(false)
const uploadProgress = ref(0)
const uploadingFileSize = ref(0)
const uploadStatus = ref<'idle' | 'dragging' | 'uploading' | 'success' | 'error'>('idle')
const analysisResult = ref<any>(null)
const analysisHistory = ref<Array<any>>([])
const currentAnalysisId = ref('')

const fileInput = ref<HTMLInputElement>()

const ANALYSIS_POLL_INTERVAL_MS = 1200
const ANALYSIS_TIMEOUT_MS = 180000

// 触发文件选择
const triggerFileInput = () => {
  fileInput.value?.click()
}

// 支持的文件类型
const supportedFileTypes = [
  { name: 'MP3音频', extension: '.mp3', icon: Music },
  { name: 'WAV音频', extension: '.wav', icon: Music },
  { name: 'M4A音频', extension: '.m4a', icon: Music },
  { name: '文本文件', extension: '.txt', icon: File }
]

const acceptTypes = computed(() => {
  return '.mp3,.wav,.m4a,.txt'
})

// 上传区域样式
const uploadAreaClass = computed(() => {
  const baseClass = 'cursor-pointer transition-all duration-200'
  
  if (uploadStatus.value === 'dragging') {
    return `${baseClass} border-primary-400 bg-primary-50`
  }
  if (uploadStatus.value === 'uploading') {
    return `${baseClass} border-yellow-400 bg-yellow-50`
  }
  if (uploadStatus.value === 'error') {
    return `${baseClass} border-danger-400 bg-danger-50`
  }
  return `${baseClass} border-gray-300 hover:border-gray-400`
})

const uploadIcon = computed(() => {
  const iconMap = {
    idle: Upload,
    dragging: FileText,
    uploading: Upload,
    success: CheckCircle,
    error: X
  }
  return iconMap[uploadStatus.value]
})

const uploadIconClass = computed(() => {
  const colorMap = {
    idle: 'text-gray-400',
    dragging: 'text-primary-600',
    uploading: 'text-yellow-600',
    success: 'text-success-600',
    error: 'text-danger-600'
  }
  return colorMap[uploadStatus.value]
})

const uploadTextClass = computed(() => {
  const colorMap = {
    idle: 'text-gray-700',
    dragging: 'text-primary-700',
    uploading: 'text-yellow-700',
    success: 'text-success-700',
    error: 'text-danger-700'
  }
  return colorMap[uploadStatus.value]
})

const uploadStatusText = computed(() => {
  const textMap = {
    idle: '拖拽文件到此处或点击上传',
    dragging: '释放文件开始上传',
    uploading: '正在上传文件...',
    success: '上传成功！',
    error: '上传失败，请重试'
  }
  return textMap[uploadStatus.value]
})

// 分析结果相关
const riskLevelText = computed(() => {
  if (!analysisResult.value) return ''
  const score = analysisResult.value.riskScore
  
  if (score >= 80) return '高风险'
  if (score >= 60) return '中风险'
  if (score >= 30) return '低风险'
  return '安全'
})

const riskRingClass = computed(() => {
  if (!analysisResult.value) return 'border-gray-300'
  const score = analysisResult.value.riskScore
  
  if (score >= 80) return 'border-danger-500'
  if (score >= 60) return 'border-yellow-500'
  if (score >= 30) return 'border-blue-500'
  return 'border-success-500'
})

const riskScoreClass = computed(() => {
  if (!analysisResult.value) return 'text-gray-900'
  const score = analysisResult.value.riskScore
  
  if (score >= 80) return 'text-danger-700'
  if (score >= 60) return 'text-yellow-700'
  if (score >= 30) return 'text-blue-700'
  return 'text-success-700'
})

const riskLevelClass = computed(() => {
  if (!analysisResult.value) return 'text-gray-600'
  const score = analysisResult.value.riskScore
  
  if (score >= 80) return 'text-danger-600'
  if (score >= 60) return 'text-yellow-600'
  if (score >= 30) return 'text-blue-600'
  return 'text-success-600'
})

const riskDescription = computed(() => {
  if (!analysisResult.value) return ''
  const score = analysisResult.value.riskScore
  
  if (score >= 80) return '检测到明显的诈骗特征，强烈建议立即终止对话并报警'
  if (score >= 60) return '存在较高的诈骗风险，请谨慎对待并多方核实'
  if (score >= 30) return '存在一定的可疑特征，建议保持警惕'
  return '未检测到明显诈骗特征，但仍需保持基本防范意识'
})

// 方法
const handleDragOver = (event: DragEvent) => {
  event.preventDefault()
  if (uploadStatus.value !== 'uploading') {
    uploadStatus.value = 'dragging'
  }
}

const handleDragLeave = (event: DragEvent) => {
  event.preventDefault()
  if (uploadStatus.value === 'dragging') {
    uploadStatus.value = 'idle'
  }
}

const handleDrop = (event: DragEvent) => {
  event.preventDefault()
  uploadStatus.value = 'idle'
  
  const files = event.dataTransfer?.files
  if (files && files.length > 0) {
    handleFile(files[0])
  }
}

const handleFileSelect = (event: Event) => {
  const target = event.target as HTMLInputElement
  const files = target.files
  
  if (files && files.length > 0) {
    handleFile(files[0])
  }
}

const handleFile = async (file: File) => {
  // 验证文件
  if (!validateFile(file)) return

  uploading.value = true
  uploadStatus.value = 'uploading'
  uploadProgress.value = 0
  uploadingFileSize.value = file.size

  try {
    uploadProgress.value = 15

    // 创建FormData
    const formData = new FormData()
    formData.append('file', file)

    // 上传文件
    const response = await fetch('/api/analysis/upload', {
      method: 'POST',
      body: formData
    })

    if (!response.ok) {
      const detail = await response.text()
      throw new Error(detail || '上传失败')
    }

    uploadProgress.value = 45

    const uploadResult = await response.json()
    const analysisId = uploadResult.analysis_id
    if (!analysisId) {
      throw new Error('后端未返回analysis_id')
    }
    currentAnalysisId.value = analysisId

    uploadProgress.value = 60

    // 轮询获取分析结果
    const analysisPayload = await pollAnalysisResult(analysisId)
    uploadProgress.value = 90

    // 映射为前端展示模型
    const normalized = mapBackendResultToUI(analysisPayload, {
      fileName: file.name,
      fileSize: file.size,
      fileType: file.type,
      analyzedAt: new Date()
    })

    analysisResult.value = normalized
    analysisHistory.value.unshift(normalized)

    if (analysisHistory.value.length > 20) {
      analysisHistory.value = analysisHistory.value.slice(0, 20)
    }

    localStorage.setItem('analysisHistory', JSON.stringify(analysisHistory.value))
    uploadProgress.value = 100
    
    uploadStatus.value = 'success'
    setTimeout(() => {
      uploadStatus.value = 'idle'
    }, 2000)
    
  } catch (error) {
    console.error('文件上传失败:', error)
    uploadStatus.value = 'error'
  } finally {
    uploading.value = false
    setTimeout(() => {
      uploadProgress.value = 0
    }, 1000)
  }
}

const validateFile = (file: File): boolean => {
  // 检查文件大小
  const maxSize = 50 * 1024 * 1024 // 50MB
  if (file.size > maxSize) {
    alert('文件大小不能超过50MB')
    return false
  }

  // 检查文件类型
  const validTypes = ['.mp3', '.wav', '.m4a', '.txt']
  const fileExtension = '.' + file.name.split('.').pop()?.toLowerCase()
  
  if (!validTypes.includes(fileExtension)) {
    alert('不支持的文件类型')
    return false
  }

  return true
}

const wait = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

const pollAnalysisResult = async (analysisId: string) => {
  const startedAt = Date.now()

  while (Date.now() - startedAt < ANALYSIS_TIMEOUT_MS) {
    const response = await fetch(`/api/analysis/results/${analysisId}`)
    if (!response.ok) {
      const detail = await response.text()
      throw new Error(detail || '获取分析结果失败')
    }

    const payload = await response.json()
    const status = payload.status

    if (status === 'completed') {
      return payload
    }

    if (status === 'failed') {
      throw new Error(payload.error || '后端分析任务失败')
    }

    uploadProgress.value = Math.min(95, uploadProgress.value + 3)
    await wait(ANALYSIS_POLL_INTERVAL_MS)
  }

  throw new Error('分析超时，请稍后重试')
}

const mapBackendResultToUI = (
  payload: any,
  fileMeta: { fileName: string; fileSize: number; fileType: string; analyzedAt: Date }
) => {
  const results = payload?.results || {}
  const fraudDetection = results?.fraud_detection || {}
  const voiceAnalysis = results?.voice_analysis || {}
  const transcription = results?.transcription || {}
  const keyFeatureRaw = results?.key_features || {}

  const riskScore = Math.round(Number(fraudDetection.risk_score || 0))
  const fraudTypesRaw = Array.isArray(fraudDetection.fraud_types) ? fraudDetection.fraud_types : []
  const fraudIndicators = Array.isArray(fraudDetection.fraud_indicators) ? fraudDetection.fraud_indicators : []

  const fraudTypeIconMap: Record<string, any> = {
    authority: UserCheck,
    urgency: Phone,
    money: DollarSign,
    threat: AlertTriangle,
    bait: Shield,
    normal: Shield,
  }

  const fraudTypes = fraudTypesRaw.map((item: any) => {
    const typeKey = String(item?.type || '').toLowerCase()
    return {
      name: item?.name || typeKey || '未知类型',
      confidence: Math.round(Number(item?.confidence || 0)),
      icon: fraudTypeIconMap[typeKey] || AlertTriangle,
    }
  })

  const keyFeatures = [
    ...fraudIndicators.map((item: string) => ({
      name: item,
      severity: riskScore >= 70 ? 'high' : riskScore >= 40 ? 'medium' : 'low',
      severityText: riskScore >= 70 ? '高风险' : riskScore >= 40 ? '中风险' : '低风险',
      description: '在转录文本中检测到的可疑话术特征',
    })),
    {
      name: '模型综合评分',
      severity: riskScore >= 70 ? 'high' : riskScore >= 40 ? 'medium' : 'low',
      severityText: riskScore >= 70 ? '高风险' : riskScore >= 40 ? '中风险' : '低风险',
      description: `综合风险分 ${riskScore}，风险等级 ${fraudDetection.risk_level || 'low'}`,
    },
  ]

  return {
    analysisId: payload?.analysis_id,
    status: payload?.status,
    processingTime: Math.round(Number(payload?.processing_time_ms || 0)),
    riskScore,
    riskLevel: fraudDetection.risk_level || 'low',
    fraudTypes,
    keyFeatures,
    transcript: transcription?.text || '',
    suggestions: Array.isArray(results?.suggestions) ? results.suggestions : [],
    voiceAnalysis,
    keyFeatureRaw,
    fileName: fileMeta.fileName,
    fileSize: fileMeta.fileSize,
    fileType: fileMeta.fileType,
    analyzedAt: fileMeta.analyzedAt,
  }
}

const clearResult = () => {
  analysisResult.value = null
}

const clearHistory = () => {
  if (confirm('确定要清空所有分析记录吗？')) {
    analysisHistory.value = []
    localStorage.removeItem('analysisHistory')
  }
}

const viewHistoryResult = (record: any) => {
  analysisResult.value = record
}

const deleteHistoryRecord = (index: number) => {
  analysisHistory.value.splice(index, 1)
  localStorage.setItem('analysisHistory', JSON.stringify(analysisHistory.value))
}

const getFileIcon = (fileType: string) => {
  if (fileType.startsWith('audio/')) return Music
  return File
}

const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes'
  
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const formatDateTime = (date: Date | string): string => {
  const parsed = date instanceof Date ? date : new Date(date)
  if (Number.isNaN(parsed.getTime())) return '-'

  return parsed.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// 生命周期
onMounted(() => {
  // 从localStorage加载历史记录
  const saved = localStorage.getItem('analysisHistory')
  if (saved) {
    try {
      analysisHistory.value = JSON.parse(saved)
    } catch (error) {
      console.error('加载历史记录失败:', error)
    }
  }
})
</script>

<style scoped>
/* 拖拽区域样式 */
.upload-area {
  min-height: 200px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.upload-area:hover {
  transform: scale(1.02);
}

/* 移动端优化 */
@media (max-width: 768px) {
  .upload-container {
    padding: 1rem;
  }
  
  .upload-area {
    min-height: 150px;
    padding: 2rem 1rem;
  }
}

/* 高对比度模式 */
@media (prefers-contrast: high) {
  .upload-area {
    border-width: 2px;
  }
}

/* 减少动画模式 */
@media (prefers-reduced-motion: reduce) {
  .upload-area {
    transition: none;
  }
}
</style>