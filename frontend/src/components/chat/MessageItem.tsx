import type { Message } from '@/types/chat'
import ThinkingDialog from './ThinkingDialog'
import { Copy, Check } from 'lucide-react'
import { useState } from 'react'

interface MessageItemProps {
  message: Message
  agentName?: string
}

export default function MessageItem({ message, agentName }: MessageItemProps) {
  const isUser = message.role === 'user'
  const hasThinking = message.thinking && message.thinking.length > 0
  const isThinking = message.isThinking || false

  // 显示ThinkingDialog的条件：正在思考中 或者 有thinking内容
  const shouldShowThinking = !isUser && (isThinking || hasThinking)

  // 调试信息
  console.log('[MessageItem] Rendering message:', {
    id: message.id,
    role: message.role,
    checkpointInfo: message.checkpointInfo,
    isUser
  })

  // 复制状态
  const [copiedId, setCopiedId] = useState<string | null>(null)

  // 复制checkpoint ID到剪贴板
  const handleCopyCheckpointId = async (checkpointId: string, type: 'checkpoint' | 'parent') => {
    try {
      await navigator.clipboard.writeText(checkpointId)
      setCopiedId(`${type}_${checkpointId}`)
      setTimeout(() => setCopiedId(null), 2000)
    } catch (error) {
      console.error('Failed to copy checkpoint ID:', error)
    }
  }

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      {!isUser && (
        <div className="w-8 h-8 bg-gradient-primary flex items-center justify-center text-white font-medium text-sm flex-shrink-0 mr-3 rounded-full">
          {agentName ? agentName.charAt(0).toUpperCase() : 'A'}
        </div>
      )}

      <div className={`max-w-[80%] ${isUser ? 'flex flex-col items-end' : ''}`}>
        {!isUser && agentName && (
          <div className="text-xs text-gray-500 mb-1 ml-1">{agentName}</div>
        )}

        {/* 思考内容区域 - 显示在输出内容上方 */}
        {shouldShowThinking && (
          <div className="mb-2">
            <ThinkingDialog
              thinking={message.thinking || ''}
              isStreaming={message.isStreaming || false}
              isThinking={isThinking}
            />
          </div>
        )}

        {/* 显示checkpoint信息（仅assistant消息）- 在消息气泡上方 */}
        {!isUser && message.checkpointInfo && (
          <>
            {console.log('[MessageItem] Rendering checkpoint info for message:', message.id, message.checkpointInfo)}
            <div className="mb-2 ml-1 space-y-1">
              <div className="flex items-center space-x-2 text-xs text-gray-400 cursor-pointer hover:text-gray-600 transition-colors group">
                <span>Checkpoint ID:</span>
                <span
                  onClick={() => handleCopyCheckpointId(message.checkpointInfo!.checkpoint_id, 'checkpoint')}
                  className="font-mono bg-gray-100 px-2 py-0.5 rounded hover:bg-gray-200 transition-colors"
                >
                  {message.checkpointInfo.checkpoint_id}
                </span>
                {copiedId === `checkpoint_${message.checkpointInfo.checkpoint_id}` ? (
                  <Check className="w-3 h-3 text-green-500" />
                ) : (
                  <Copy className="w-3 h-3 opacity-0 group-hover:opacity-100 transition-opacity" />
                )}
              </div>
              {message.checkpointInfo.parent_checkpoint_id && (
                <div className="flex items-center space-x-2 text-xs text-gray-400 cursor-pointer hover:text-gray-600 transition-colors group">
                  <span>Parent Checkpoint ID:</span>
                  <span
                    onClick={() => handleCopyCheckpointId(message.checkpointInfo!.parent_checkpoint_id!, 'parent')}
                    className="font-mono bg-gray-100 px-2 py-0.5 rounded hover:bg-gray-200 transition-colors"
                  >
                    {message.checkpointInfo.parent_checkpoint_id}
                  </span>
                  {copiedId === `parent_${message.checkpointInfo.parent_checkpoint_id}` ? (
                    <Check className="w-3 h-3 text-green-500" />
                  ) : (
                    <Copy className="w-3 h-3 opacity-0 group-hover:opacity-100 transition-opacity" />
                  )}
                </div>
              )}
            </div>
          </>
        )}

        {/* 消息内容区域 */}
        <div
          className={`px-4 py-3 shadow-elegant rounded-2xl ${
            isUser
              ? 'bg-gradient-primary text-white'
              : 'bg-gray-100 text-gray-800'
          }`}
        >
          {message.images && message.images.length > 0 && (
            <div className="grid grid-cols-2 gap-2 mb-2">
              {message.images.map((image, index) => (
                <img
                  key={index}
                  src={image}
                  alt={`Attached ${index + 1}`}
                  className="max-w-full rounded"
                />
              ))}
            </div>
          )}
          <p className="whitespace-pre-wrap">{message.content}</p>
          {message.isStreaming && (
            <span className="inline-block w-2 h-4 ml-1 bg-current animate-pulse" />
          )}
        </div>
      </div>
    </div>
  )
}
