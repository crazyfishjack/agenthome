import { Trash2 } from 'lucide-react'
import { useState } from 'react'
import type { Conversation } from '@/store/conversationStore'

interface ConversationItemProps {
  conversation: Conversation
  isActive: boolean
  onClick: () => void
  onDelete: (e: React.MouseEvent) => void
}

export default function ConversationItem({
  conversation,
  isActive,
  onClick,
  onDelete,
}: ConversationItemProps) {
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMs / 3600000)
    const diffDays = Math.floor(diffMs / 86400000)

    if (diffMins < 1) return '刚刚'
    if (diffMins < 60) return `${diffMins}分钟前`
    if (diffHours < 24) return `${diffHours}小时前`
    if (diffDays < 7) return `${diffDays}天前`
    return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
  }

  const handleDeleteClick = (e: React.MouseEvent) => {
    e.stopPropagation()
    setShowDeleteConfirm(true)
  }

  const handleConfirmDelete = (e: React.MouseEvent) => {
    e.stopPropagation()
    setShowDeleteConfirm(false)
    onDelete(e)
  }

  const handleCancelDelete = (e: React.MouseEvent) => {
    e.stopPropagation()
    setShowDeleteConfirm(false)
  }

  return (
    <div
      onClick={onClick}
      className={`group relative px-4 py-3 cursor-pointer transition-colors border-l-2 ${
        isActive
          ? 'bg-gradient-primary border-primary-700'
          : conversation.isGenerating
          ? 'bg-green-50 border-green-500'
          : 'bg-white border-transparent hover:bg-gray-50'
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <p
              className={`text-sm font-medium truncate ${
                isActive ? 'text-primary-800' : conversation.isGenerating ? 'text-green-800' : 'text-gray-800'
              }`}
            >
              {conversation.title}
            </p>
            {conversation.isGenerating && (
              <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">
                生成中
              </span>
            )}
          </div>
          <p
            className={`text-xs mt-1 ${
              isActive ? 'text-primary-700' : conversation.isGenerating ? 'text-green-700' : 'text-gray-500'
            }`}
          >
            {conversation.messages.length > 0
              ? `${conversation.messages.length} 条消息`
              : '空对话'}
            {' · '}
            {formatTime(conversation.timestamp)}
          </p>
        </div>
        <button
          onClick={handleDeleteClick}
          className="opacity-0 group-hover:opacity-100 p-1 text-gray-400 hover:text-danger-600 transition-opacity"
          title="删除对话"
        >
          <Trash2 className="w-4 h-4" />
        </button>
      </div>

      {/* 删除确认对话框 */}
      {showDeleteConfirm && (
        <div
          className="absolute inset-0 bg-white/95 backdrop-blur-sm z-10 flex items-center justify-center p-4"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="text-center">
            <p className="text-sm text-gray-700 mb-3">确定要删除这个对话吗？</p>
            <div className="flex items-center justify-center gap-2">
              <button
                onClick={handleCancelDelete}
                className="px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 rounded-full transition-colors"
              >
                取消
              </button>
              <button
                onClick={handleConfirmDelete}
                className="px-3 py-1.5 text-sm text-white bg-danger-500 hover:bg-danger-600 rounded-full transition-colors"
              >
                确定
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
