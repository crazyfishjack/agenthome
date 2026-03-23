import { useState } from 'react'
import { AlertTriangle, Check, X, Loader2 } from 'lucide-react'
import type { InterruptData } from '@/types/chat'
import { chatApi } from '@/api/chat'

interface InterruptDialogProps {
  interrupt: InterruptData
  onDecision?: (decision: 'approve' | 'reject') => void
}

export default function InterruptDialog({ interrupt, onDecision }: InterruptDialogProps) {
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [decision, setDecision] = useState<'approve' | 'reject' | null>(null)

  const handleApprove = async () => {
    if (isSubmitting) return

    setIsSubmitting(true)
    setDecision('approve')

    try {
      await chatApi.sendInterruptDecision({
        thread_id: interrupt.thread_id,
        decision: 'approve'
      })
      onDecision?.('approve')
    } catch (error) {
      console.error('Failed to approve interrupt:', error)
      setIsSubmitting(false)
      setDecision(null)
    }
  }

  const handleReject = async () => {
    if (isSubmitting) return

    setIsSubmitting(true)
    setDecision('reject')

    try {
      await chatApi.sendInterruptDecision({
        thread_id: interrupt.thread_id,
        decision: 'reject'
      })
      onDecision?.('reject')
    } catch (error) {
      console.error('Failed to reject interrupt:', error)
      setIsSubmitting(false)
      setDecision(null)
    }
  }

  // 格式化工具参数为可读的字符串
  const formatToolArgs = (args: Record<string, any>): string => {
    try {
      return JSON.stringify(args, null, 2)
    } catch (error) {
      return String(args)
    }
  }

  return (
    <div className="mb-2 w-full">
      {/* 中断提示框 */}
      <div className="bg-gradient-to-r from-amber-50 to-orange-50 border-l-4 border-amber-500 rounded-lg shadow-elegant p-4">
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
              Agent 请求执行以下工具操作，请确认是否继续
            </p>
          </div>
        </div>

        {/* 工具信息 */}
        <div className="bg-white rounded-md border border-amber-200 p-3 mb-3">
          <div className="mb-2">
            <span className="text-xs font-medium text-gray-600">工具名称：</span>
            <span className="ml-2 text-sm font-semibold text-gray-900 font-mono">
              {interrupt.tool_name}
            </span>
          </div>
          <div>
            <span className="text-xs font-medium text-gray-600">工具参数：</span>
            <pre className="mt-2 text-xs text-gray-800 bg-gray-50 rounded p-2 overflow-x-auto font-mono">
              {formatToolArgs(interrupt.tool_args)}
            </pre>
          </div>
        </div>

        {/* 操作按钮 */}
        <div className="flex items-center justify-end gap-2">
          <button
            onClick={handleReject}
            disabled={isSubmitting}
            className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
              isSubmitting && decision === 'reject'
                ? 'bg-gray-400 cursor-not-allowed'
                : 'bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 hover:border-gray-400'
            }`}
          >
            {isSubmitting && decision === 'reject' ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <X className="w-4 h-4" />
            )}
            拒绝
          </button>
          <button
            onClick={handleApprove}
            disabled={isSubmitting}
            className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
              isSubmitting && decision === 'approve'
                ? 'bg-green-400 cursor-not-allowed'
                : 'bg-green-600 text-white hover:bg-green-700 shadow-md hover:shadow-lg'
            }`}
          >
            {isSubmitting && decision === 'approve' ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Check className="w-4 h-4" />
            )}
            同意
          </button>
        </div>
      </div>
    </div>
  )
}
