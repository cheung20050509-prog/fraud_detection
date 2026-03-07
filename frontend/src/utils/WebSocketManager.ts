/**
 * WebSocket客户端管理器 - 软著申请：实时通信核心模块
 * 作用：管理WebSocket连接，支持自动重连、心跳检测、错误处理
 */

export interface WebSocketConfig {
  url: string
  protocols?: string | string[]
  reconnectInterval?: number // 重连间隔（毫秒）
  maxReconnectAttempts?: number // 最大重连次数
  heartbeatInterval?: number // 心跳间隔（毫秒）
  timeout?: number // 连接超时时间（毫秒）
  onOpen?: (event: Event) => void
  onMessage?: (event: MessageEvent) => void
  onClose?: (event: CloseEvent) => void
  onError?: (event: Event) => void
  onReconnect?: (attempt: number) => void
  onStatusChange?: (status: WebSocketStatus) => void
}

export enum WebSocketStatus {
  CONNECTING = 'connecting',
  OPEN = 'open',
  CLOSING = 'closing',
  CLOSED = 'closed',
  RECONNECTING = 'reconnecting',
  ERROR = 'error'
}

export interface QueuedMessage {
  data: string | ArrayBuffer | Blob
  timestamp: number
  retryCount?: number
}

export class WebSocketManager {
  private ws: WebSocket | null = null
  private config: Required<WebSocketConfig>
  private status: WebSocketStatus = WebSocketStatus.CLOSED
  private reconnectAttempts = 0
  private heartbeatTimer: number | null = null
  private connectTimer: number | null = null
  private messageQueue: QueuedMessage[] = []
  private lastActivity = Date.now()
  
  constructor(config: WebSocketConfig) {
    this.config = {
      protocols: [],
      reconnectInterval: 3000,
      maxReconnectAttempts: 10,
      heartbeatInterval: 30000,
      timeout: 10000,
      onOpen: () => {},
      onMessage: () => {},
      onClose: () => {},
      onError: () => {},
      onReconnect: () => {},
      onStatusChange: () => {},
      ...config
    }
  }

  /**
   * 连接WebSocket - 软著申请：建立WebSocket连接
   */
  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        // 清理现有连接
        this.disconnect()
        
        // 更新状态
        this.updateStatus(WebSocketStatus.CONNECTING)
        
        // 创建WebSocket连接
        this.ws = new WebSocket(this.config.url, this.config.protocols)
        
        // 设置连接超时
        this.connectTimer = window.setTimeout(() => {
          if (this.ws?.readyState === WebSocket.CONNECTING) {
            this.ws.close()
            this.handleConnectError(new Error('连接超时'))
            reject(new Error('连接超时'))
          }
        }, this.config.timeout)
        
        // 绑定事件监听器
        this.setupEventListeners()
        
        // 连接成功resolve
        const originalOnOpen = this.config.onOpen
        this.config.onOpen = (event) => {
          originalOnOpen(event)
          resolve()
        }
        
      } catch (error) {
        this.handleConnectError(error as Error)
        reject(error)
      }
    })
  }

  /**
   * 断开连接 - 软著申请：主动断开WebSocket连接
   */
  disconnect(): void {
    this.clearTimers()
    
    if (this.ws) {
      this.updateStatus(WebSocketStatus.CLOSING)
      
      // 移除事件监听器
      this.ws.onopen = null
      this.ws.onmessage = null
      this.ws.onclose = null
      this.ws.onerror = null
      
      // 关闭连接
      if (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING) {
        this.ws.close()
      }
      
      this.ws = null
    }
    
    this.updateStatus(WebSocketStatus.CLOSED)
  }

  /**
   * 发送消息 - 软著申请：向服务器发送消息
   */
  send(data: string | ArrayBuffer | Blob): boolean {
    if (!this.isConnected()) {
      // 连接未建立，加入队列
      this.queueMessage(data)
      return false
    }
    
    try {
      this.lastActivity = Date.now()
      this.ws!.send(data)
      return true
    } catch (error) {
      console.error('发送消息失败:', error)
      this.queueMessage(data)
      return false
    }
  }

  /**
   * 发送JSON消息 - 软著申请：发送结构化数据
   */
  sendJSON(data: object): boolean {
    return this.send(JSON.stringify(data))
  }

  /**
   * 获取连接状态 - 软著申请：查询当前连接状态
   */
  getStatus(): WebSocketStatus {
    return this.status
  }

  /**
   * 检查是否已连接 - 软著申请：连接状态检查
   */
  isConnected(): boolean {
    return this.status === WebSocketStatus.OPEN && this.ws?.readyState === WebSocket.OPEN
  }

  /**
   * 获取WebSocket实例 - 软著申请：获取原生WebSocket对象
   */
  getWebSocket(): WebSocket | null {
    return this.ws
  }

  /**
   * 强制重连 - 软著申请：手动触发重连
   */
  forceReconnect(): void {
    this.disconnect()
    this.reconnect()
  }

  /**
   * 获取连接统计 - 软著申请：连接性能监控
   */
  getStats(): {
    status: WebSocketStatus
    reconnectAttempts: number
    queuedMessages: number
    lastActivity: Date
    uptime: number
  } {
    return {
      status: this.status,
      reconnectAttempts: this.reconnectAttempts,
      queuedMessages: this.messageQueue.length,
      lastActivity: new Date(this.lastActivity),
      uptime: this.status === WebSocketStatus.OPEN ? Date.now() - this.lastActivity : 0
    }
  }

  // 私有方法

  private setupEventListeners(): void {
    if (!this.ws) return

    this.ws.onopen = (event: Event) => {
      this.clearConnectTimer()
      this.reconnectAttempts = 0
      this.updateStatus(WebSocketStatus.OPEN)
      
      // 发送队列中的消息
      this.flushMessageQueue()
      
      // 启动心跳
      this.startHeartbeat()
      
      this.config.onOpen(event)
    }

    this.ws.onmessage = (event: MessageEvent) => {
      this.lastActivity = Date.now()
      
      // 处理心跳响应
      if (this.isHeartbeatMessage(event.data)) {
        return
      }
      
      this.config.onMessage(event)
    }

    this.ws.onclose = (event: CloseEvent) => {
      this.clearTimers()
      
      if (this.status !== WebSocketStatus.CLOSED) {
        this.updateStatus(WebSocketStatus.CLOSED)
      }
      
      this.config.onClose(event)
      
      // 如果不是主动关闭，尝试重连
      if (!event.wasClean && event.code !== 1000) {
        this.reconnect()
      }
    }

    this.ws.onerror = (event: Event) => {
      this.updateStatus(WebSocketStatus.ERROR)
      this.config.onError(event)
    }
  }

  private updateStatus(status: WebSocketStatus): void {
    if (this.status !== status) {
      this.status = status
      this.config.onStatusChange(status)
      
      // 触发全局状态变更事件
      window.dispatchEvent(new CustomEvent('wsStatusChange', {
        detail: { status }
      }))
    }
  }

  private reconnect(): void {
    if (this.reconnectAttempts >= this.config.maxReconnectAttempts) {
      console.error('WebSocket重连次数已达上限，停止重连')
      this.updateStatus(WebSocketStatus.ERROR)
      return
    }
    
    this.reconnectAttempts++
    this.updateStatus(WebSocketStatus.RECONNECTING)
    
    this.config.onReconnect(this.reconnectAttempts)
    
    // 延迟重连
    setTimeout(() => {
      this.connect().catch(error => {
        console.error('WebSocket重连失败:', error)
        this.handleConnectError(error as Error)
      })
    }, this.config.reconnectInterval)
  }

  private startHeartbeat(): void {
    this.clearHeartbeat()

    if (this.config.heartbeatInterval <= 0) {
      return
    }
    
    this.heartbeatTimer = window.setInterval(() => {
      if (this.isConnected()) {
        try {
          this.send(this.getHeartbeatMessage())
        } catch (error) {
          console.error('发送心跳失败:', error)
        }
      }
    }, this.config.heartbeatInterval)
  }

  private clearHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer)
      this.heartbeatTimer = null
    }
  }

  private clearConnectTimer(): void {
    if (this.connectTimer) {
      clearTimeout(this.connectTimer)
      this.connectTimer = null
    }
  }

  private clearTimers(): void {
    this.clearHeartbeat()
    this.clearConnectTimer()
  }

  private queueMessage(data: string | ArrayBuffer | Blob): void {
    this.messageQueue.push({
      data,
      timestamp: Date.now(),
      retryCount: 0
    })
    
    // 限制队列大小
    if (this.messageQueue.length > 100) {
      this.messageQueue.shift()
    }
  }

  private flushMessageQueue(): void {
    while (this.messageQueue.length > 0 && this.isConnected()) {
      const message = this.messageQueue.shift()!
      
      try {
        this.ws!.send(message.data)
      } catch (error) {
        console.error('发送队列消息失败:', error)
        
        // 重新加入队列（限制重试次数）
        if ((message.retryCount || 0) < 3) {
          message.retryCount = (message.retryCount || 0) + 1
          this.messageQueue.unshift(message)
        }
      }
    }
  }

  private handleConnectError(error: Error): void {
    console.error('WebSocket连接错误:', error)
    this.updateStatus(WebSocketStatus.ERROR)
    
    // 清理连接
    if (this.ws) {
      this.ws = null
    }
  }

  private getHeartbeatMessage(): string {
    return JSON.stringify({
      type: 'heartbeat',
      timestamp: Date.now()
    })
  }

  private isHeartbeatMessage(data: string): boolean {
    try {
      const parsed = JSON.parse(data)
      return parsed.type === 'heartbeat' || parsed.type === 'pong'
    } catch {
      return false
    }
  }

  /**
   * 销毁管理器 - 软著申请：资源清理
   */
  destroy(): void {
    this.disconnect()
    this.messageQueue = []
  }
}

/**
 * WebSocket连接池管理器 - 软著申请：多连接管理
 */
export class WebSocketPool {
  private connections = new Map<string, WebSocketManager>()
  private defaultConfig: Partial<WebSocketConfig> = {}

  constructor(defaultConfig?: Partial<WebSocketConfig>) {
    this.defaultConfig = defaultConfig || {}
  }

  /**
   * 创建连接 - 软著申请：创建命名连接
   */
  async create(name: string, url: string, config?: Partial<WebSocketConfig>): Promise<WebSocketManager> {
    const manager = new WebSocketManager({
      ...this.defaultConfig,
      url,
      ...config
    })

    this.connections.set(name, manager)
    
    try {
      await manager.connect()
      return manager
    } catch (error) {
      // 连接失败时也返回管理器，让调用者处理错误
      return manager
    }
  }

  /**
   * 获取连接 - 软著申请：获取已创建的连接
   */
  get(name: string): WebSocketManager | undefined {
    return this.connections.get(name)
  }

  /**
   * 关闭连接 - 软著申请：关闭指定连接
   */
  close(name: string): void {
    const manager = this.connections.get(name)
    if (manager) {
      manager.disconnect()
      this.connections.delete(name)
    }
  }

  /**
   * 关闭所有连接 - 软著申请：全局连接清理
   */
  closeAll(): void {
    for (const [name, manager] of this.connections) {
      manager.disconnect()
    }
    this.connections.clear()
  }

  /**
   * 广播消息 - 软著申请：向所有连接发送消息
   */
  broadcast(data: string | ArrayBuffer | Blob): number {
    let sentCount = 0
    
    for (const manager of this.connections.values()) {
      if (manager.send(data)) {
        sentCount++
      }
    }
    
    return sentCount
  }

  /**
   * 获取所有连接状态 - 软著申请：连接池状态监控
   */
  getAllStats(): Record<string, any> {
    const stats: Record<string, any> = {}
    
    for (const [name, manager] of this.connections) {
      stats[name] = manager.getStats()
    }
    
    return stats
  }
}

/**
 * WebSocket工厂 - 软著申请：连接管理工厂
 */
export class WebSocketFactory {
  private static pool = new WebSocketPool()

  /**
   * 创建音频流连接 - 软著申请：音频专用连接
   */
  static async createAudioConnection(mode: 'practice' | 'monitoring' | 'analysis', 
                                   config?: Partial<WebSocketConfig>): Promise<WebSocketManager> {
    const wsUrl = this.getWebSocketUrl(mode)
    
    return this.pool.create(`audio_${mode}`, wsUrl, {
      ...config,
      reconnectInterval: 5000,
      maxReconnectAttempts: 5,
      heartbeatInterval: 30000
    })
  }

  /**
   * 创建控制连接 - 软著申请：控制信令连接
   */
  static async createControlConnection(config?: Partial<WebSocketConfig>): Promise<WebSocketManager> {
    const wsUrl = this.getWebSocketUrl('control')
    
    return this.pool.create('control', wsUrl, {
      ...config,
      reconnectInterval: 3000,
      maxReconnectAttempts: 10,
      heartbeatInterval: 60000
    })
  }

  /**
   * 获取WebSocket URL - 软著申请：动态URL构建
   */
  private static getWebSocketUrl(mode: string): string {
    // 从配置或环境变量获取服务器地址
    const wsUrl = import.meta.env.VITE_WS_URL || 'ws://localhost:8000'
    return `${wsUrl}/ws/audio/${mode}`
  }

  /**
   * 关闭指定类型连接 - 软著申请：批量关闭
   */
  static closeAudioConnections(): void {
    this.pool.close('audio_practice')
    this.pool.close('audio_monitoring')
    this.pool.close('audio_analysis')
  }

  /**
   * 关闭所有连接 - 软著申请：全局清理
   */
  static closeAll(): void {
    this.pool.closeAll()
  }

  /**
   * 获取连接池 - 软著申请：访问全局连接池
   */
  static getPool(): WebSocketPool {
    return this.pool
  }
}

export default WebSocketManager