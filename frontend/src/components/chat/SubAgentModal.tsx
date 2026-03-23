import { useEffect, useRef, useState, useCallback } from 'react'
import {
  X,
  Minus,
  Maximize2,
  Minimize2,
  Bot,
  Loader2,
  CheckCircle,
  AlertCircle,
  Terminal,
  Cpu,
  MessageSquare,
  ListTodo,
  AlertTriangle,
  Check
} from 'lucide-react'
import { useSubAgentStore, SubAgentEvent } from '@/store/subAgentStore'

interface SubAgentModalProps {
  executionId: string
  onClose: () => void
  onMinimize: () => void
  initialPosition?: { x: number; y: number }
}

/**
 * 格式化时间戳
 */
const formatTime = (timestamp: number): string => {
  const date = new Date(timestamp)
  return date.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

/**
 * 获取事件图标
 */
const getEventIcon = (eventType: string) => {
  switch (eventType) {
    case 'execution_start':
    case 'subagent_start':
      return <Bot className="w-3.5 h-3.5 text-primary-600" />
    case 'subagent_ready':
      return <CheckCircle className="w-3.5 h-3.5 text-success-500" />
    case 'subagent_thinking':
      return <MessageSquare className="w-3.5 h-3.5 text-info-500" />
    case 'subagent_tool_call_request':
      return <Cpu className="w-3.5 h-3.5 text-warning-500" />
    case 'subagent_tool_result':
      return <Terminal className="w-3.5 h-3.5 text-success-500" />
    case 'subagent_todos_update':
      return <ListTodo className="w-3.5 h-3.5 text-primary-500" />
    case 'subagent_error':
    case 'execution_error':
      return <AlertTriangle className="w-3.5 h-3.5 text-danger-500" />
    case 'execution_complete':
    case 'subagent_complete':
      return <CheckCircle className="w-3.5 h-3.5 text-success-500" />
    default:
      return <Bot className="w-3.5 h-3.5 text-gray-500" />
  }
}

/**
 * 获取事件标题
 */
const getEventTitle = (eventType: string): string => {
  const titles: Record<string, string> = {
    execution_start: '开始执行',
    execution_complete: '执行完成',
    execution_error: '执行错误',
    subagent_start: 'SUB Agent 启动',
    subagent_ready: '准备就绪',
    subagent_thinking: '思考中',
    subagent_tool_call_request: '工具调用请求',
    subagent_tool_result: '工具执行结果',
    subagent_todos_update: '任务清单更新',
    subagent_interrupt: '执行中断',
    subagent_error: '执行错误',
    subagent_complete: 'SUB Agent 完成',
    subagent_result: '最终结果',
    subagent_final_result: '最终结果',
  }
  return titles[eventType] || eventType
}

/**
 * 渲染事件内容
 */
const renderEventContent = (event: SubAgentEvent): string => {
  const data = event.data || {}

  switch (event.type) {
    case 'subagent_thinking':
      return data.content as string || ''
    case 'subagent_tool_call_request':
      return `调用工具: ${data.name || 'unknown'}\n参数: ${JSON.stringify(data.args || {}, null, 2)}`
    case 'subagent_tool_result':
      return `工具: ${data.name || 'unknown'}\n结果: ${data.content || ''}`
    case 'subagent_todos_update':
      const todos = (data.todos || []) as Array<{ content?: string; status?: string }>
      return `任务清单:\n${todos.map((t) => `  - ${t.content || ''} (${t.status || 'pending'})`).join('\n')}`
    case 'subagent_error':
    case 'execution_error':
      return `错误: ${data.error || '未知错误'}`
    case 'subagent_final_result':
      return `结果:\n${data.result || ''}`
    case 'execution_complete':
      return `执行完成，共 ${data.events_count || 0} 个事件`
    default:
      return JSON.stringify(data, null, 2)
  }
}

export default function SubAgentModal({
  executionId,
  onClose,
  onMinimize,
  initialPosition,
}: SubAgentModalProps) {
  const execution = useSubAgentStore((state) => state.executions.get(executionId))
  const addEvent = useSubAgentStore((state) => state.addEvent)
  const updateExecutionStatus = useSubAgentStore((state) => state.updateExecutionStatus)
  const setResult = useSubAgentStore((state) => state.setResult)
  const setError = useSubAgentStore((state) => state.setError)
  const removeExecution = useSubAgentStore((state) => state.removeExecution)

  const [isMaximized, setIsMaximized] = useState(false)
  const [isDragging, setIsDragging] = useState(false)
  const [position, setPosition] = useState(initialPosition || { x: 100, y: 100 })
  const [size] = useState({ width: 500, height: 400 })
  const [isPolling, setIsPolling] = useState(false)
  const [pollError, setPollError] = useState<string | null>(null)

  // Human-in-the-loop 中断决策状态
  const [isWaitingForDecision, setIsWaitingForDecision] = useState(false)
  const [interruptData, setInterruptData] = useState<any>(null)
  const [isSubmittingDecision, setIsSubmittingDecision] = useState(false)

  // 记录已处理的中断事件，防止重复弹出
  const processedInterruptsRef = useRef<Set<string>>(new Set())

  const modalRef = useRef<HTMLDivElement>(null)
  const contentRef = useRef<HTMLDivElement>(null)
  const dragStartRef = useRef({ x: 0, y: 0 })
  const latestTimestampRef = useRef<number | null>(null)
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // 获取 API 基础 URL
  const apiBaseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'

  // 轮询执行状态和事件
  const pollExecution = useCallback(async () => {
    if (!executionId) return

    try {
      const sinceTimestamp = latestTimestampRef.current
      const url = `${apiBaseUrl}/api/task-pro/${executionId}/poll?since_timestamp=${sinceTimestamp || '0'}&limit=100`

      const response = await fetch(url)
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()

      // 更新执行状态
      if (data.status && execution?.status !== data.status) {
        updateExecutionStatus(executionId, data.status)
      }

      // 更新结果
      if (data.result) {
        setResult(executionId, data.result)
      }

      // 更新错误
      if (data.error) {
        setError(executionId, data.error)
      }

      // 添加新事件
      if (data.events && Array.isArray(data.events)) {
        data.events.forEach((event: SubAgentEvent) => {
          addEvent(executionId, event)

          // 检测中断事件，显示决策 UI
          if (event.type === 'subagent_interrupt') {
            // 生成唯一的中断事件 ID
            const interruptId = `${executionId}-${event.timestamp}`
            console.log('[SubAgentModal] 检测到中断事件:', event.data, 'ID:', interruptId)

            // 检查是否已经处理过这个中断，且当前没有在等待决策
            if (!processedInterruptsRef.current.has(interruptId) && !isWaitingForDecision) {
              setIsWaitingForDecision(true)
              setInterruptData({ ...event.data, interruptId })
            } else {
              console.log('[SubAgentModal] 中断事件已处理或正在处理中，跳过:', interruptId)
            }
          }
        })

        // 更新最新时间戳
        if (data.latest_timestamp) {
          latestTimestampRef.current = data.latest_timestamp
        }
      }

      setPollError(null)

      // 如果执行完成或出错，停止轮询
      if (data.status === 'completed' || data.status === 'error') {
        if (pollIntervalRef.current) {
          clearInterval(pollIntervalRef.current)
          pollIntervalRef.current = null
          setIsPolling(false)
        }
      }
    } catch (error) {
      console.error('[SubAgentModal] 轮询失败:', error)
      setPollError(error instanceof Error ? error.message : 'Unknown error')
    }
  }, [executionId, apiBaseUrl, execution?.status, updateExecutionStatus, setResult, setError, addEvent])

  // 启动轮询
  useEffect(() => {
    if (!execution || (execution.status !== 'pending' && execution.status !== 'running')) {
      return
    }

    setIsPolling(true)
    setPollError(null)

    // 立即执行一次轮询
    pollExecution()

    // 每 1 秒轮询一次
    pollIntervalRef.current = setInterval(() => {
      pollExecution()
    }, 1000)

    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current)
        pollIntervalRef.current = null
      }
      setIsPolling(false)
    }
  }, [executionId, execution?.status, pollExecution])

  // 自动滚动到底部
  useEffect(() => {
    if (contentRef.current) {
      contentRef.current.scrollTop = contentRef.current.scrollHeight
    }
  }, [execution?.events])

  // 拖拽处理
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    if (isMaximized) return

    setIsDragging(true)
    dragStartRef.current = {
      x: e.clientX - position.x,
      y: e.clientY - position.y,
    }
  }, [isMaximized, position])

  const handleMouseMove = useCallback((e: MouseEvent) => {
    if (!isDragging) return

    const newX = e.clientX - dragStartRef.current.x
    const newY = e.clientY - dragStartRef.current.y

    // 限制在视口内
    const maxX = window.innerWidth - size.width
    const maxY = window.innerHeight - 50 // 保留标题栏可见

    setPosition({
      x: Math.max(0, Math.min(newX, maxX)),
      y: Math.max(0, Math.min(newY, maxY)),
    })
  }, [isDragging, size])

  const handleMouseUp = useCallback(() => {
    setIsDragging(false)
  }, [])

  useEffect(() => {
    if (isDragging) {
      window.addEventListener('mousemove', handleMouseMove)
      window.addEventListener('mouseup', handleMouseUp)
    }

    return () => {
      window.removeEventListener('mousemove', handleMouseMove)
      window.removeEventListener('mouseup', handleMouseUp)
    }
  }, [isDragging, handleMouseMove, handleMouseUp])

  // 切换最大化
  const toggleMaximize = () => {
    setIsMaximized(!isMaximized)
  }

  // 处理中断决策
  const handleInterruptDecision = useCallback(async (decision: 'approve' | 'reject') => {
    if (isSubmittingDecision || !interruptData?.interruptId) return

    setIsSubmittingDecision(true)
    console.log(`[SubAgentModal] 发送决策: ${decision}, interruptId: ${interruptData.interruptId}`)

    try {
      const response = await fetch(
        `${apiBaseUrl}/api/task-pro/${executionId}/interrupt-decision`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ decision })
        }
      )

      if (response.ok) {
        const result = await response.json()
        console.log('[SubAgentModal] 决策发送成功:', result)

        // 记录已处理的中断，防止再次弹出
        processedInterruptsRef.current.add(interruptData.interruptId)
        console.log('[SubAgentModal] 已记录处理的中断:', interruptData.interruptId)

        // 立即隐藏决策 UI
        setIsWaitingForDecision(false)
        setInterruptData(null)
      } else {
        const error = await response.text()
        console.error('[SubAgentModal] 决策发送失败:', error)
        setPollError(`决策发送失败: ${error}`)
      }
    } catch (error) {
      console.error('[SubAgentModal] 发送决策异常:', error)
      setPollError(error instanceof Error ? error.message : '发送决策失败')
    } finally {
      setIsSubmittingDecision(false)
    }
  }, [executionId, apiBaseUrl, isSubmittingDecision, interruptData])

  if (!execution) return null

  const statusColors = {
    pending: 'bg-gray-100 text-gray-600',
    running: 'bg-primary-100 text-primary-600',
    completed: 'bg-success-100 text-success-600',
    error: 'bg-danger-100 text-danger-600',
  }

  const statusIcons = {
    pending: <Loader2 className="w-3 h-3 animate-spin" />,
    running: <Loader2 className="w-3 h-3 animate-spin" />,
    completed: <CheckCircle className="w-3 h-3" />,
    error: <AlertCircle className="w-3 h-3" />,
  }

  return (
    <div
      ref={modalRef}
      className={`fixed z-50 flex flex-col bg-white shadow-2xl overflow-hidden transition-all duration-200 ${
        isMaximized ? 'inset-4 rounded-none' : 'rounded-none'
      }`}
      style={
        isMaximized
          ? {}
          : {
              left: position.x,
              top: position.y,
              width: size.width,
              height: size.height,
            }
      }
    >
      {/* 标题栏 - 可拖拽 */}
      <div
        className="flex items-center justify-between px-3 py-2 bg-gradient-to-r from-primary-50 to-primary-100 border-b border-primary-200 cursor-move select-none"
        onMouseDown={handleMouseDown}
      >
        <div className="flex items-center gap-2">
          <Bot className="w-4 h-4 text-primary-600" />
          <span className="text-xs font-semibold text-primary-700 truncate max-w-[200px]">
            SUB Agent: {execution.subagentType}
          </span>
          <span
            className={`flex items-center gap-1 px-1.5 py-0.5 text-[10px] font-medium ${statusColors[execution.status]}`}
          >
            {statusIcons[execution.status]}
            {execution.status === 'pending' && '等待中'}
            {execution.status === 'running' && '执行中'}
            {execution.status === 'completed' && '已完成'}
            {execution.status === 'error' && '错误'}
          </span>
          {/* 轮询状态指示器 */}
          {execution.status === 'running' && (
            <span className={`w-2 h-2 rounded-full ${isPolling ? 'bg-success-500' : pollError ? 'bg-danger-500' : 'bg-warning-500 animate-pulse'}`}
              title={isPolling ? '轮询中' : pollError ? '轮询错误' : '等待轮询'}
            />
          )}
        </div>

        <div className="flex items-center gap-1">
          {/* 最小化按钮 */}
          <button
            onClick={onMinimize}
            className="p-1 hover:bg-primary-200/50 transition-colors"
            title="最小化"
          >
            <Minus className="w-3.5 h-3.5 text-gray-600" />
          </button>

          {/* 最大化/还原按钮 */}
          <button
            onClick={toggleMaximize}
            className="p-1 hover:bg-primary-200/50 transition-colors"
            title={isMaximized ? '还原' : '最大化'}
          >
            {isMaximized ? (
              <Minimize2 className="w-3.5 h-3.5 text-gray-600" />
            ) : (
              <Maximize2 className="w-3.5 h-3.5 text-gray-600" />
            )}
          </button>

          {/* 关闭按钮 */}
          <button
            onClick={onClose}
            className="p-1 hover:bg-danger-100 transition-colors"
            title="关闭"
          >
            <X className="w-3.5 h-3.5 text-gray-600 hover:text-danger-600" />
          </button>
        </div>
      </div>

      {/* 描述区域 */}
      <div className="px-3 py-2 bg-gray-50 border-b border-gray-200">
        <p className="text-[10px] text-gray-600 line-clamp-2">
          <span className="font-medium">任务:</span> {execution.description}
        </p>
      </div>

      {/* 内容区域 */}
      <div
        ref={contentRef}
        className="flex-1 overflow-y-auto p-3 space-y-2 bg-white scrollbar-thin"
      >
        {execution.events.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-gray-400">
            <Bot className="w-8 h-8 mb-2 opacity-50" />
            <p className="text-xs">等待 SUB Agent 执行...</p>
            {isPolling && (
              <div className="flex items-center gap-1 mt-2 text-primary-500">
                <Loader2 className="w-3 h-3 animate-spin" />
                <span className="text-[10px]">轮询中...</span>
              </div>
            )}
            {pollError && (
              <div className="flex items-center gap-1 mt-2 text-danger-500">
                <AlertCircle className="w-3 h-3" />
                <span className="text-[10px]">{pollError}</span>
              </div>
            )}
          </div>
        ) : (
          execution.events.map((event, index) => (
            <div
              key={`${event.execution_id}-${index}-${event.timestamp}`}
              className="flex gap-2 p-2 bg-gray-50 hover:bg-gray-100 transition-colors"
            >
              <div className="flex-shrink-0 mt-0.5">{getEventIcon(event.type)}</div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-[10px] font-medium text-gray-700">
                    {getEventTitle(event.type)}
                  </span>
                  <span className="text-[9px] text-gray-400">
                    {formatTime(event.timestamp)}
                  </span>
                </div>
                <pre className="text-[10px] text-gray-600 whitespace-pre-wrap break-words font-mono leading-relaxed">
                  {renderEventContent(event)}
                </pre>
              </div>
            </div>
          ))
        )}

        {/* 执行中指示器 */}
        {execution.status === 'running' && execution.events.length > 0 && !isWaitingForDecision && (
          <div className="flex items-center gap-2 p-2 text-primary-600">
            <Loader2 className="w-3 h-3 animate-spin" />
            <span className="text-[10px]">执行中...</span>
          </div>
        )}

        {/* Human-in-the-loop 中断决策 UI - 显示在最下方 */}
        {isWaitingForDecision && interruptData && (
          <div className="mt-4 bg-gradient-to-r from-amber-50 to-orange-50 border-l-4 border-amber-500 rounded-lg shadow-elegant p-4">
            {/* 标题栏 */}
            <div className="flex items-start gap-3 mb-3">
              <div className="flex-shrink-0 mt-0.5">
                <AlertTriangle className="w-5 h-5 text-amber-600" />
              </div>
              <div className="flex-1">
                <h3 className="text-sm font-semibold text-amber-900 mb-1">
                  需要您的批准
                </h3>
                <p className="text-xs text-amber-700">
                  SUB Agent 请求执行以下工具操作，请确认是否继续
                </p>
              </div>
            </div>

            {/* 工具信息 */}
            <div className="bg-white rounded-md border border-amber-200 p-3 mb-3">
              <div className="mb-2">
                <span className="text-xs font-medium text-gray-600">工具名称：</span>
                <span className="ml-2 text-sm font-semibold text-gray-900 font-mono">
                  {interruptData.action_requests?.[0]?.name || 'Unknown'}
                </span>
              </div>
              <div>
                <span className="text-xs font-medium text-gray-600">工具参数：</span>
                <pre className="mt-2 text-xs text-gray-800 bg-gray-50 rounded p-2 overflow-x-auto font-mono">
                  {JSON.stringify(interruptData.action_requests?.[0]?.args || {}, null, 2)}
                </pre>
              </div>
            </div>

            {/* 操作按钮 */}
            <div className="flex items-center justify-end gap-2">
              <button
                onClick={() => handleInterruptDecision('reject')}
                disabled={isSubmittingDecision}
                className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
                  isSubmittingDecision
                    ? 'bg-gray-400 cursor-not-allowed'
                    : 'bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 hover:border-gray-400'
                }`}
              >
                {isSubmittingDecision ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <X className="w-4 h-4" />
                )}
                拒绝
              </button>
              <button
                onClick={() => handleInterruptDecision('approve')}
                disabled={isSubmittingDecision}
                className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
                  isSubmittingDecision
                    ? 'bg-green-400 cursor-not-allowed'
                    : 'bg-green-600 text-white hover:bg-green-700 shadow-md hover:shadow-lg'
                }`}
              >
                {isSubmittingDecision ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Check className="w-4 h-4" />
                )}
                同意
              </button>
            </div>
          </div>
        )}
      </div>

      {/* 底部状态栏 */}
      <div className="flex items-center justify-between px-3 py-1.5 bg-gray-50 border-t border-gray-200 text-[10px] text-gray-500">
        <div className="flex items-center gap-2">
          <span>事件: {execution.events.length}</span>
          {execution.startedAt && (
            <span>
              耗时:
              {execution.completedAt
                ? ((execution.completedAt - execution.startedAt) / 1000).toFixed(1)
                : ((Date.now() - execution.startedAt) / 1000).toFixed(1)}
              s
            </span>
          )}
        </div>
        <div className="flex items-center gap-1">
          <span>ID:</span>
          <span className="font-mono text-[9px]">
            {execution.executionId.slice(-8)}
          </span>
        </div>
      </div>
    </div>
  )

  // 组件卸载时清理 execution 记录
  useEffect(() => {
    return () => {
      console.log('[SubAgentModal] 组件卸载，清理 execution:', executionId)
      removeExecution(executionId)
    }
  }, [executionId, removeExecution])
}
