import { useState, useEffect, useRef, useCallback } from 'react'
import { ChevronDown, ChevronRight, Brain, CheckCircle, Loader2, Bot, ExternalLink } from 'lucide-react'
import { useSubAgentStore } from '@/store/subAgentStore'

interface TaskProInitInfo {
  execution_id: string
  subagent_type: string
  description: string
}

interface ThinkingDialogProps {
  thinking: string
  isStreaming: boolean
  isThinking: boolean  // 是否正在思考中
  onToggle?: (expanded: boolean) => void
}

/**
 * 从思考内容中解析 [TASK_PRO_INIT] 标记
 */
const parseTaskProInitMarkers = (content: string): TaskProInitInfo[] => {
  const markers: TaskProInitInfo[] = []
  const regex = /\[TASK_PRO_INIT\](.*?)\[\/TASK_PRO_INIT\]/g
  let match

  while ((match = regex.exec(content)) !== null) {
    try {
      const data = JSON.parse(match[1])
      markers.push(data)
    } catch (e) {
      console.error('Failed to parse TASK_PRO_INIT marker:', e)
    }
  }

  console.log('[ThinkingDialog] 解析 TASK_PRO_INIT 标记:', markers)
  return markers
}

/**
 * 清理思考内容中的 [TASK_PRO_INIT] 标记，替换为可读的文本
 * 同时过滤 pre_task_pro 工具的详细执行结果
 */
const cleanThinkingContent = (content: string): string => {
  // 1. 处理 [TASK_PRO_INIT] 标记
  let cleaned = content.replace(
    /\[TASK_PRO_INIT\](.*?)\[\/TASK_PRO_INIT\]/g,
    (_, jsonStr) => {
      try {
        const data = JSON.parse(jsonStr)
        return `[已启动 SUB Agent: ${data.subagent_type}]`
      } catch {
        return '[SUB Agent 启动标记]'
      }
    }
  )

  // 2. 过滤 pre_task_pro 工具的详细执行结果
  // 匹配 "准备完成！execution_id: xxx" 到 "task_pro(" 之间的所有内容
  cleaned = cleaned.replace(
    /✅ 准备完成！execution_id: [\w_]+[\s\S]*?(?=\n\n任务执行|\n\n工具|$)/g,
    ''
  )

  // 3. 过滤 "⚠️ 现在必须立即调用 task_pro 工具！" 及其后续说明
  cleaned = cleaned.replace(
    /⚠️ 现在必须立即调用 task_pro 工具！[\s\S]*?\)/g,
    ''
  )

  // 4. 过滤 "示例：" 及其后续内容（包含 task_pro 调用示例）
  cleaned = cleaned.replace(
    /\n*示例：\s*\n\s*task_pro\([\s\S]*?\)\s*\n*/g,
    ''
  )

  // 5. 过滤 "错误：缺少 execution_id 参数！" 及其后续说明
  cleaned = cleaned.replace(
    /错误：缺少 execution_id 参数！[\s\S]*?请立即调用 pre_task_pro 工具！/g,
    '[错误：请先调用 pre_task_pro 工具]'
  )

  return cleaned
}

export default function ThinkingDialog({
  thinking,
  isStreaming,
  isThinking,
  onToggle
}: ThinkingDialogProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)

  // SubAgent Store
  const { createExecution, openModal, hasExecution } = useSubAgentStore()

  // 解析 TASK_PRO_INIT 标记
  const taskProMarkers = parseTaskProInitMarkers(thinking)

  // 处理新的 TASK_PRO_INIT 标记
  useEffect(() => {
    taskProMarkers.forEach((marker) => {
      console.log('[ThinkingDialog] 检测到 TASK_PRO_INIT 标记:', marker)
      if (!hasExecution(marker.execution_id)) {
        // 创建执行记录（但不自动打开弹窗）
        console.log('[ThinkingDialog] 创建执行记录:', marker.execution_id)
        createExecution(
          marker.execution_id,
          marker.subagent_type,
          marker.description
        )
        // 注意：不自动打开弹窗，用户需要手动点击"查看执行"按钮
        console.log('[ThinkingDialog] 执行记录已创建，等待用户手动打开:', marker.execution_id)
      } else {
        console.log('[ThinkingDialog] 跳过已存在的执行:', marker.execution_id)
      }
    })
  }, [taskProMarkers, hasExecution, createExecution])

  // 思考过程中默认展开，思考完毕后自动折叠
  useEffect(() => {
    if (isThinking) {
      // 正在思考中，保持展开
      setIsExpanded(true)
    } else if (!isStreaming && thinking.length > 0) {
      // 思考完成且非流式输出，自动折叠
      setIsExpanded(false)
    }
  }, [isThinking, isStreaming, thinking])

  // 监听thinking内容变化，自动滚动到底部
  useEffect(() => {
    if (scrollRef.current && isExpanded) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [thinking, isExpanded])

  const handleToggle = () => {
    const newExpanded = !isExpanded
    setIsExpanded(newExpanded)
    onToggle?.(newExpanded)
  }

  // 处理查看 SUB Agent 按钮点击
  const handleViewSubAgent = useCallback((executionId: string) => {
    openModal(executionId)
  }, [openModal])

  // 清理后的思考内容
  const cleanedThinking = cleanThinkingContent(thinking)

  // 计算思考内容的行数和字符数
  const lineCount = cleanedThinking.split('\n').length
  const charCount = cleanedThinking.length

  return (
    <div className="mb-2 w-full">
      {/* 思考标题栏 */}
      <button
        onClick={handleToggle}
        className="w-full flex items-center justify-between px-2.5 py-1.5 bg-gradient-to-r from-primary-50 to-primary-100 border-l-2 border-primary-400 hover:from-primary-100 hover:to-primary-200 transition-all duration-300 shadow-elegant hover:shadow-elegant-hover"
      >
        <div className="flex items-center gap-1.5">
          <div className="flex items-center gap-1">
            {isThinking ? (
              <Loader2 className="w-3 h-3 text-primary-600 animate-spin" />
            ) : (
              <CheckCircle className="w-3 h-3 text-success-500" />
            )}
            <Brain className="w-3 h-3 text-primary-600" />
          </div>
          <span className="text-[10px] font-semibold text-primary-700 uppercase tracking-wide">
            {isThinking ? '深度思考中...' : '深度思考'}
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          {thinking && (
            <span className="text-[10px] text-gray-500">
              {lineCount}行 · {charCount}字
            </span>
          )}
          {isExpanded ? (
            <ChevronDown className="w-3 h-3 text-gray-600 transition-transform duration-300" />
          ) : (
            <ChevronRight className="w-3 h-3 text-gray-600 transition-transform duration-300" />
          )}
        </div>
      </button>

      {/* 思考内容区域 */}
      <div
        className={`overflow-hidden transition-all duration-300 ease-in-out ${
          isExpanded ? 'max-h-[400px] opacity-100' : 'max-h-0 opacity-0'
        }`}
      >
        <div
          ref={scrollRef}
          className="px-2.5 py-2 bg-white border border-primary-200 border-t-0 shadow-elegant max-h-[400px] overflow-y-auto scrollbar-thin"
        >
          {/* SUB Agent 执行按钮列表 */}
          {taskProMarkers.length > 0 && (
            <div className="mb-3 space-y-1.5">
              {taskProMarkers.map((marker) => (
                <button
                  key={marker.execution_id}
                  onClick={() => handleViewSubAgent(marker.execution_id)}
                  className="w-full flex items-center justify-between px-2.5 py-1.5 bg-gradient-to-r from-info-50 to-info-100 border-l-2 border-info-400 hover:from-info-100 hover:to-info-200 transition-all duration-200 group"
                >
                  <div className="flex items-center gap-1.5">
                    <Bot className="w-3 h-3 text-info-600" />
                    <span className="text-[10px] font-medium text-info-700">
                      SUB Agent: {marker.subagent_type}
                    </span>
                  </div>
                  <div className="flex items-center gap-1 text-info-600">
                    <span className="text-[9px]">查看执行</span>
                    <ExternalLink className="w-3 h-3 group-hover:translate-x-0.5 transition-transform" />
                  </div>
                </button>
              ))}
            </div>
          )}

          <div className="whitespace-pre-wrap font-sans text-[11px] text-gray-700 leading-relaxed">
            {cleanedThinking || (
              <span className="text-gray-400 italic text-[11px]">等待思考内容...</span>
            )}
          </div>
          {isThinking && (
            <div className="mt-1.5 flex items-center gap-1.5 text-[10px] text-primary-600">
              <div className="w-1.5 h-1.5 bg-primary-500 rounded-full animate-pulse" />
              <span>正在分析问题...</span>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
