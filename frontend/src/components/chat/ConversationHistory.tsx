import { Plus, MessageSquare } from 'lucide-react'
import { useConversationStore } from '@/store/conversationStore'
import ConversationItem from './ConversationItem'

interface ConversationHistoryProps {
  agentId: string | null
  onNewConversation: () => void
  onConversationSelect: (conversationId: string) => void
}

export default function ConversationHistory({
  agentId,
  onNewConversation,
  onConversationSelect,
}: ConversationHistoryProps) {
  const {
    getConversationsByAgent,
    deleteConversation,
    currentConversationId,
    getConversationSummary,
  } = useConversationStore()

  const conversations = agentId ? getConversationsByAgent(agentId) : []

  const handleDeleteConversation = (e: React.MouseEvent, conversationId: string) => {
    e.stopPropagation()
    if (agentId) {
      deleteConversation(agentId, conversationId)
    }
  }

  return (
    <div className="w-72 bg-white flex flex-col border-l border-gray-200">
      <div className="p-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-gray-700 flex items-center space-x-2">
            <MessageSquare className="w-4 h-4" />
            <span>对话历史</span>
          </h3>
          <button
            onClick={onNewConversation}
            disabled={!agentId}
            className="p-1.5 text-gray-600 hover:text-gray-900 hover:bg-gray-100 shadow-elegant hover:shadow-elegant-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            title="新建对话"
          >
            <Plus className="w-4 h-4" />
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto scrollbar-thin">
        {!agentId ? (
          <div className="flex flex-col items-center justify-center h-full text-gray-400 p-6">
            <MessageSquare className="w-12 h-12 mb-3 opacity-50" />
            <p className="text-sm text-center">请先选择一个Agent</p>
          </div>
        ) : conversations.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-gray-400 p-6">
            <MessageSquare className="w-12 h-12 mb-3 opacity-50" />
            <p className="text-sm text-center">暂无对话历史</p>
            <p className="text-xs text-center mt-1">点击上方按钮创建新对话</p>
          </div>
        ) : (
          <div className="py-2">
            {conversations.map((conversation) => (
              <ConversationItem
                key={conversation.id}
                conversation={{
                  ...conversation,
                  title: getConversationSummary(conversation.id)
                }}
                isActive={conversation.id === currentConversationId}
                onClick={() => onConversationSelect(conversation.id)}
                onDelete={(e) => handleDeleteConversation(e, conversation.id)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
