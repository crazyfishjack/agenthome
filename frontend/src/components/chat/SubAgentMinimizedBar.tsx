import { Bot, Maximize2, X, Loader2, CheckCircle, AlertCircle } from 'lucide-react'
import { useSubAgentStore } from '@/store/subAgentStore'

interface SubAgentMinimizedBarProps {
  onRestore: (executionId: string) => void
  onClose: (executionId: string) => void
}

export default function SubAgentMinimizedBar({ onRestore, onClose }: SubAgentMinimizedBarProps) {
  const executions = useSubAgentStore((state) => state.getAllExecutions())
  const minimizedExecutions = executions.filter((exec) => exec.isMinimized)

  if (minimizedExecutions.length === 0) return null

  return (
    <div className="fixed bottom-4 left-4 z-40 flex flex-col gap-2">
      {minimizedExecutions.map((execution) => {
        const statusIcons = {
          pending: <Loader2 className="w-3 h-3 animate-spin text-gray-500" />,
          running: <Loader2 className="w-3 h-3 animate-spin text-primary-600" />,
          completed: <CheckCircle className="w-3 h-3 text-success-500" />,
          error: <AlertCircle className="w-3 h-3 text-danger-500" />,
        }

        return (
          <div
            key={execution.executionId}
            className="flex items-center gap-2 px-3 py-2 bg-white border border-primary-200 shadow-elegant hover:shadow-elegant-hover transition-all cursor-pointer group"
            onClick={() => onRestore(execution.executionId)}
          >
            <Bot className="w-4 h-4 text-primary-600" />
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-1.5">
                {statusIcons[execution.status]}
                <span className="text-[11px] font-medium text-gray-700 truncate max-w-[150px]">
                  {execution.subagentType}
                </span>
              </div>
            </div>

            {/* 操作按钮 */}
            <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  onRestore(execution.executionId)
                }}
                className="p-1 hover:bg-primary-100 transition-colors"
                title="恢复"
              >
                <Maximize2 className="w-3 h-3 text-gray-600" />
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  onClose(execution.executionId)
                }}
                className="p-1 hover:bg-danger-100 transition-colors"
                title="关闭"
              >
                <X className="w-3 h-3 text-gray-600 hover:text-danger-600" />
              </button>
            </div>
          </div>
        )
      })}
    </div>
  )
}
