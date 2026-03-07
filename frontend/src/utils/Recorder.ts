/**
 * 音频录制器类 - 软著申请：Web音频采集核心模块
 * 作用：基于MediaRecorder API实现高质量的音频录制，支持实时流传输和多种音频格式
 */

export interface RecorderConfig {
  sampleRate?: number
  channels?: number
  chunkSize?: number
  streaming?: boolean
  format?: 'audio/webm' | 'audio/mp4' | 'audio/wav'
  maxDuration?: number // 最大录制时长（秒）
  autoStart?: boolean // 是否自动开始
  onAudioData?: (data: Blob) => void // 音频数据回调
  onError?: (error: Error) => void // 错误回调
  onStart?: () => void // 开始录制回调
  onStop?: () => void // 停止录制回调
  onPause?: () => void // 暂停录制回调
  onResume?: () => void // 恢复录制回调
}

export interface RecorderState {
  isRecording: boolean
  isPaused: boolean
  duration: number
  audioLevel: number
  sampleRate: number
  chunks: Blob[]
}

export class AudioRecorder {
  private mediaRecorder: MediaRecorder | null = null
  private audioContext: AudioContext | null = null
  private analyser: AnalyserNode | null = null
  private microphone: MediaStreamAudioSourceNode | null = null
  private stream: MediaStream | null = null
  private animationId: number | null = null
  
  private config: Required<RecorderConfig>
  private state: RecorderState
  private startTime: number = 0
  private pausedTime: number = 0
  private onVolumeChange?: (level: number) => void
  private stopResolver: ((audioBlob: Blob | null) => void) | null = null
  
  constructor(config: RecorderConfig = {}) {
    this.config = {
      sampleRate: config.sampleRate || 16000,
      channels: config.channels || 1,
      chunkSize: config.chunkSize || 1024,
      streaming: config.streaming ?? true,
      format: config.format || 'audio/webm',
      maxDuration: config.maxDuration || 300, // 5分钟
      autoStart: config.autoStart || false,
      onAudioData: config.onAudioData || (() => {}),
      onError: config.onError || (() => {}),
      onStart: config.onStart || (() => {}),
      onStop: config.onStop || (() => {}),
      onPause: config.onPause || (() => {}),
      onResume: config.onResume || (() => {})
    }
    
    this.state = {
      isRecording: false,
      isPaused: false,
      duration: 0,
      audioLevel: 0,
      sampleRate: this.config.sampleRate,
      chunks: []
    }
    
    // 自动初始化
    if (this.config.autoStart) {
      this.init().catch(error => {
        this.config.onError(new Error(`自动初始化失败: ${error.message}`))
      })
    }
  }

  /**
   * 初始化音频录制器 - 软著申请：音频设备初始化
   */
  async init(): Promise<void> {
    try {
      // 请求麦克风权限
      this.stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: this.config.sampleRate,
          channelCount: this.config.channels,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        },
        video: false
      })

      // 创建音频上下文
      this.audioContext = new (window.AudioContext || (window as any).webkitAudioContext)({
        sampleRate: this.config.sampleRate
      })

      // 创建分析器节点（用于音量检测）
      this.analyser = this.audioContext.createAnalyser()
      this.analyser.fftSize = 256
      this.analyser.smoothingTimeConstant = 0.8

      // 创建麦克风源
      this.microphone = this.audioContext.createMediaStreamSource(this.stream)
      this.microphone.connect(this.analyser)

      // 创建MediaRecorder
      const mimeType = this.getSupportedMimeType()
      if (!mimeType) {
        throw new Error('浏览器不支持音频录制')
      }

      this.mediaRecorder = new MediaRecorder(this.stream, {
        mimeType: mimeType,
        audioBitsPerSecond: 128000
      })

      // 设置事件监听器
      this.setupEventListeners()

      console.log('音频录制器初始化成功:', mimeType)
    } catch (error) {
      console.error('音频录制器初始化失败:', error)
      throw error
    }
  }

  /**
   * 开始录制 - 软著申请：音频录制启动
   */
  async start(): Promise<void> {
    if (!this.mediaRecorder || !this.stream) {
      await this.init()
    }

    if (this.state.isRecording) {
      console.warn('录制已在进行中')
      return
    }

    try {
      this.state.chunks = []
      this.state.isRecording = true
      this.state.isPaused = false
      this.startTime = Date.now()
      this.pausedTime = 0
      this.stopResolver = null

      if (this.config.streaming) {
        this.mediaRecorder?.start(this.config.chunkSize)
      } else {
        this.mediaRecorder?.start()
      }
      
      // 开始音量检测
      this.startVolumeDetection()
      
      // 开始时长计时
      this.startTimer()

      this.config.onStart()
      console.log('开始录制音频')
    } catch (error) {
      this.config.onError(error as Error)
      throw error
    }
  }

  /**
   * 停止录制 - 软著申请：音频录制停止
   */
  async stop(): Promise<Blob | null> {
    if (!this.state.isRecording) {
      console.warn('当前没有在录制')
      return null
    }

    try {
      this.state.isRecording = false
      this.state.isPaused = false

      if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
        const stopPromise = new Promise<Blob | null>((resolve) => {
          this.stopResolver = resolve
        })
        this.mediaRecorder.stop()
        return await stopPromise
      }

      // 停止音量检测
      this.stopVolumeDetection()
      
      // 停止计时器
      this.stopTimer()

      const audioBlob = this.createAudioBlob()

      this.finalizeStop(audioBlob)
      return audioBlob
    } catch (error) {
      this.config.onError(error as Error)
      return null
    }
  }

  /**
   * 暂停录制 - 软著申请：音频录制暂停
   */
  pause(): void {
    if (!this.state.isRecording || this.state.isPaused) {
      return
    }

    if (this.mediaRecorder && this.mediaRecorder.state === 'recording') {
      this.mediaRecorder.pause()
      this.pausedTime = Date.now()
      this.stopTimer()
      this.state.isPaused = true
      this.config.onPause()
      console.log('暂停录制')
    }
  }

  /**
   * 恢复录制 - 软著申请：音频录制恢复
   */
  resume(): void {
    if (!this.state.isRecording || !this.state.isPaused) {
      return
    }

    if (this.mediaRecorder && this.mediaRecorder.state === 'paused') {
      this.mediaRecorder.resume()
      
      // 调整开始时间
      const pauseDuration = Date.now() - this.pausedTime
      this.startTime += pauseDuration
      
      this.startTimer()
      this.state.isPaused = false
      this.config.onResume()
      console.log('恢复录制')
    }
  }

  /**
   * 获取当前状态 - 软著申请：录制状态查询
   */
  getState(): RecorderState {
    return { ...this.state }
  }

  /**
   * 设置音量回调 - 软著申请：实时音量监测
   */
  setVolumeCallback(callback: (level: number) => void): void {
    this.onVolumeChange = callback
  }

  /**
   * 清理资源 - 软著申请：资源释放
   */
  cleanup(): void {
    try {
      this.stopVolumeDetection()
      this.stopTimer()

      if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
        this.mediaRecorder.stop()
      }

      if (this.stream) {
        this.stream.getTracks().forEach(track => track.stop())
      }

      if (this.microphone) {
        this.microphone.disconnect()
      }

      if (this.analyser) {
        this.analyser.disconnect()
      }

      if (this.audioContext && this.audioContext.state !== 'closed') {
        this.audioContext.close()
      }

      // 重置状态
      this.state = {
        isRecording: false,
        isPaused: false,
        duration: 0,
        audioLevel: 0,
        sampleRate: this.config.sampleRate,
        chunks: []
      }

      console.log('音频录制器资源已清理')
    } catch (error) {
      console.error('清理音频录制器时出错:', error)
    }
  }

  /**
   * 下载录制的音频 - 软著申请：音频文件导出
   */
  downloadAudio(filename?: string): void {
    const audioBlob = this.createAudioBlob()
    if (!audioBlob) {
      console.error('没有音频数据可下载')
      return
    }

    const url = URL.createObjectURL(audioBlob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename || `recording_${Date.now()}.webm`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  // 私有方法

  private setupEventListeners(): void {
    if (!this.mediaRecorder) return

    this.mediaRecorder.ondataavailable = (event: BlobEvent) => {
      if (event.data.size > 0) {
        this.state.chunks.push(event.data)
        if (this.config.streaming) {
          this.config.onAudioData(event.data)
        }
      }
    }

    this.mediaRecorder.onerror = (event: Event) => {
      const error = (event as any).error || new Error('录制过程中发生未知错误')
      this.config.onError(error)
    }

    this.mediaRecorder.onstop = () => {
      const audioBlob = this.createAudioBlob()
      this.finalizeStop(audioBlob)
    }
  }

  private finalizeStop(audioBlob: Blob | null): void {
    if (audioBlob && !this.config.streaming) {
      this.config.onAudioData(audioBlob)
    }

    if (this.stopResolver) {
      const resolve = this.stopResolver
      this.stopResolver = null
      resolve(audioBlob)
    }

    this.config.onStop()
    console.log('停止录制音频，时长:', this.state.duration.toFixed(2), '秒')
  }

  private getSupportedMimeType(): string | null {
    const types = [
      this.config.format,
      'audio/webm;codecs=opus',
      'audio/mp4',
      'audio/wav'
    ]

    for (const type of types) {
      if (MediaRecorder.isTypeSupported(type)) {
        return type
      }
    }

    return null
  }

  private createAudioBlob(): Blob | null {
    if (this.state.chunks.length === 0) {
      return null
    }

    const mimeType = this.getSupportedMimeType()
    return new Blob(this.state.chunks, { type: mimeType || 'audio/webm' })
  }

  private startVolumeDetection(): void {
    if (!this.analyser) return

    const bufferLength = this.analyser.frequencyBinCount
    const dataArray = new Uint8Array(bufferLength)

    const detectVolume = () => {
      if (!this.state.isRecording || this.state.isPaused) return

      this.analyser?.getByteFrequencyData(dataArray)
      
      // 计算平均音量
      let sum = 0
      for (let i = 0; i < bufferLength; i++) {
        sum += dataArray[i]
      }
      const average = sum / bufferLength
      this.state.audioLevel = average / 255

      // 触发音量变化回调
      if (this.onVolumeChange) {
        this.onVolumeChange(this.state.audioLevel)
      }

      this.animationId = requestAnimationFrame(detectVolume)
    }

    detectVolume()
  }

  private stopVolumeDetection(): void {
    if (this.animationId) {
      cancelAnimationFrame(this.animationId)
      this.animationId = null
    }
  }

  private startTimer(): void {
    // 使用requestAnimationFrame实现高精度计时
    const updateTimer = () => {
      if (!this.state.isRecording || this.state.isPaused) return

      const currentTime = Date.now()
      this.state.duration = (currentTime - this.startTime) / 1000

      // 检查最大时长限制
      if (this.state.duration >= this.config.maxDuration) {
        this.stop()
        return
      }

      requestAnimationFrame(updateTimer)
    }

    updateTimer()
  }

  private stopTimer(): void {
    // Timer通过检查状态自动停止
  }

  /**
   * 获取设备信息 - 软著申请：音频设备检测
   */
  static async getAudioDevices(): Promise<MediaDeviceInfo[]> {
    try {
      const devices = await navigator.mediaDevices.enumerateDevices()
      return devices.filter(device => device.kind === 'audioinput')
    } catch (error) {
      console.error('获取音频设备失败:', error)
      return []
    }
  }

  /**
   * 检查浏览器支持 - 软著申请：浏览器兼容性检测
   */
  static checkBrowserSupport(): {
    supported: boolean
    features: string[]
    limitations: string[]
  } {
    const features: string[] = []
    const limitations: string[] = []

    // 检查MediaRecorder支持
    if (typeof navigator !== 'undefined' && navigator.mediaDevices && typeof navigator.mediaDevices.getUserMedia === 'function') {
      features.push('MediaRecorder API')
    } else {
      limitations.push('MediaRecorder API不支持')
    }

    // 检查AudioContext支持
    if (window.AudioContext || (window as any).webkitAudioContext) {
      features.push('Web Audio API')
    } else {
      limitations.push('Web Audio API不支持')
    }

    // 检查支持的视频格式
    const formats = ['audio/webm', 'audio/mp4', 'audio/wav']
    const supportedFormats = formats.filter(format => MediaRecorder.isTypeSupported(format))
    
    if (supportedFormats.length > 0) {
      features.push(`音频格式: ${supportedFormats.join(', ')}`)
    } else {
      limitations.push('没有支持的音频格式')
    }

    return {
      supported: limitations.length === 0,
      features,
      limitations
    }
  }
}

export default AudioRecorder