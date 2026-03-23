import { create } from 'zustand'
import type { Message } from '@/types/chat'
import { chatApi } from '@/api/chat'

export interface Conversation {
  id: string
  agentId: string
  title: string
  messages: Message[]
  timestamp: string
  isGenerating?: boolean  // 是否正在生成中
  // 独立的生成状态管理
  generatingMessageId?: string | null  // 当前正在生成的消息ID
  abortController?: { abort: () => void } | null  // AbortController（序列化时只保存状态）
  taskId?: string | null  // 任务ID
}

interface ConversationState {
  conversations: Record<string, Conversation[]> // {agentId: Conversation[]}
  currentConversationId: string | null

  // Actions
  loadConversations: (agentId: string) => Conversation[]
  createConversation: (agentId: string, title?: string) => Conversation
  selectConversation: (conversationId: string) => void
  deleteConversation: (agentId: string, conversationId: string) => void
  updateConversationMessages: (conversationId: string, messages: Message[]) => void
  clearCurrentConversation: () => void
  getCurrentConversation: () => Conversation | null
  getConversationsByAgent: (agentId: string) => Conversation[]
  getConversationSummary: (conversationId: string) => string
  setConversationGenerating: (conversationId: string, isGenerating: boolean) => void
  getConversationById: (conversationId: string) => Conversation | null
  
  // 新增：每个会话独立的生成状态管理
  startConversationGeneration: (conversationId: string, messageId: string, controller: AbortController, taskId?: string) => void
  stopConversationGeneration: (conversationId: string) => void
  updateConversationMessage: (conversationId: string, messageId: string, content: string) => void
  updateConversationMessageThinking: (conversationId: string, messageId: string, thinking: string) => void
  updateConversationMessageStreaming: (conversationId: string, messageId: string, isStreaming: boolean) => void
  updateConversationMessageIsThinking: (conversationId: string, messageId: string, isThinking: boolean) => void
  setConversationTaskId: (conversationId: string, taskId: string | null) => void
  getConversationGeneratingMessageId: (conversationId: string) => string | null
  getConversationTaskId: (conversationId: string) => string | null
}

const STORAGE_KEY = 'agent_conversations'

// LocalStorage helper functions
const loadFromStorage = (): Record<string, Conversation[]> => {
  try {
    const data = localStorage.getItem(STORAGE_KEY)
    return data ? JSON.parse(data) : {}
  } catch (error) {
    console.error('Failed to load conversations from localStorage:', error)
    return {}
  }
}

const saveToStorage = (data: Record<string, Conversation[]>) => {
  try {
    // 在保存之前，移除不可序列化的字段（如 abortController）
    const serializableData: Record<string, Conversation[]> = {}
    Object.entries(data).forEach(([agentId, convs]) => {
      serializableData[agentId] = convs.map(conv => {
        const { abortController, ...rest } = conv
        return rest
      })
    })
    localStorage.setItem(STORAGE_KEY, JSON.stringify(serializableData))
  } catch (error) {
    console.error('Failed to save conversations to localStorage:', error)
  }
}

export const useConversationStore = create<ConversationState>((set, get) => ({
  conversations: loadFromStorage(),
  currentConversationId: null,

  loadConversations: (agentId: string) => {
    const allConversations = get().conversations
    return allConversations[agentId] || []
  },

  createConversation: (agentId: string, title?: string) => {
    const newConversation: Conversation = {
      id: `conv_${Date.now()}`,
      agentId,
      title: title || `对话 ${new Date().toLocaleString('zh-CN', { hour: '2-digit', minute: '2-digit' })}`,
      messages: [],
      timestamp: new Date().toISOString(),
    }

    set((state) => {
      const agentConversations = state.conversations[agentId] || []
      const updatedConversations = {
        ...state.conversations,
        [agentId]: [newConversation, ...agentConversations],
      }
      saveToStorage(updatedConversations)
      return {
        conversations: updatedConversations,
        currentConversationId: newConversation.id,
      }
    })

    return newConversation
  },

  selectConversation: (conversationId: string) => {
    set({ currentConversationId: conversationId })
  },

  deleteConversation: (agentId: string, conversationId: string) => {
    // 先删除后端的checkpoint数据
    chatApi.deleteConversation(agentId, conversationId).catch(error => {
      console.error('Failed to delete conversation checkpoints:', error)
    })

    // 再删除前端的会话记录
    set((state) => {
      const agentConversations = state.conversations[agentId] || []
      const updatedAgentConversations = agentConversations.filter(
        (conv) => conv.id !== conversationId
      )
      const updatedConversations = {
        ...state.conversations,
        [agentId]: updatedAgentConversations,
      }
      saveToStorage(updatedConversations)
      return {
        conversations: updatedConversations,
        currentConversationId:
          state.currentConversationId === conversationId ? null : state.currentConversationId,
      }
    })
  },

  updateConversationMessages: (conversationId: string, messages: Message[]) => {
    set((state) => {
      const updatedConversations: Record<string, Conversation[]> = {}
      
      Object.entries(state.conversations).forEach(([agentId, convs]) => {
        updatedConversations[agentId] = convs.map((conv) =>
          conv.id === conversationId
            ? { ...conv, messages, timestamp: new Date().toISOString() }
            : conv
        )
      })
      
      saveToStorage(updatedConversations)
      return { conversations: updatedConversations }
    })
  },

  clearCurrentConversation: () => {
    set({ currentConversationId: null })
  },

  getCurrentConversation: () => {
    const { conversations, currentConversationId } = get()
    if (!currentConversationId) return null
    
    for (const agentConversations of Object.values(conversations)) {
      const found = agentConversations.find((conv) => conv.id === currentConversationId)
      if (found) return found
    }
    return null
  },

  getConversationsByAgent: (agentId: string) => {
    const { conversations } = get()
    return conversations[agentId] || []
  },

  getConversationSummary: (conversationId: string) => {
    const { conversations } = get()
    
    // 查找指定对话
    for (const agentConversations of Object.values(conversations)) {
      const found = agentConversations.find((conv) => conv.id === conversationId)
      if (found) {
        // 找到用户最近发送的消息
        const userMessages = found.messages.filter(msg => msg.role === 'user')
        if (userMessages.length > 0) {
          const lastUserMessage = userMessages[userMessages.length - 1]
          const content = lastUserMessage.content || ''
          // 返回摘要，最多40个字符
          return content.length > 40 ? content.substring(0, 40) + '...' : content
        }
      }
    }
    
    // 如果没有用户消息，返回默认标题
    return '新对话'
  },

  setConversationGenerating: (conversationId: string, isGenerating: boolean) => {
    set((state) => {
      const updatedConversations: Record<string, Conversation[]> = {}
      
      Object.entries(state.conversations).forEach(([agentId, convs]) => {
        updatedConversations[agentId] = convs.map((conv) =>
          conv.id === conversationId
            ? { ...conv, isGenerating }
            : conv
        )
      })
      
      saveToStorage(updatedConversations)
      return { conversations: updatedConversations }
    })
  },

  getConversationById: (conversationId: string) => {
    const { conversations } = get()
    for (const agentConversations of Object.values(conversations)) {
      const found = agentConversations.find((conv) => conv.id === conversationId)
      if (found) return found
    }
    return null
  },

  // 新增：每个会话独立的生成状态管理
  startConversationGeneration: (conversationId: string, messageId: string, controller: AbortController, taskId?: string) => {
    set((state) => {
      const updatedConversations: Record<string, Conversation[]> = {}
      
      Object.entries(state.conversations).forEach(([agentId, convs]) => {
        updatedConversations[agentId] = convs.map((conv) =>
          conv.id === conversationId
            ? { 
                ...conv, 
                isGenerating: true, 
                generatingMessageId: messageId, 
                abortController: { abort: controller.abort.bind(controller) },
                taskId: taskId || null 
              }
            : conv
        )
      })
      
      saveToStorage(updatedConversations)
      return { conversations: updatedConversations }
    })
  },

  stopConversationGeneration: (conversationId: string) => {
    set((state) => {
      const updatedConversations: Record<string, Conversation[]> = {}
      
      // 先获取当前会话的 abortController 并调用 abort
      Object.entries(state.conversations).forEach(([, convs]) => {
        const conv = convs.find((c) => c.id === conversationId)
        if (conv && conv.abortController && typeof conv.abortController.abort === 'function') {
          try {
            conv.abortController.abort()
          } catch (error) {
            console.error('Failed to abort generation:', error)
          }
        }
      })
      
      // 更新状态
      Object.entries(state.conversations).forEach(([agentId, convs]) => {
        updatedConversations[agentId] = convs.map((conv) =>
          conv.id === conversationId
            ? { 
                ...conv, 
                isGenerating: false, 
                generatingMessageId: null, 
                abortController: null,
                taskId: null 
              }
            : conv
        )
      })
      
      saveToStorage(updatedConversations)
      return { conversations: updatedConversations }
    })
  },

  updateConversationMessage: (conversationId: string, messageId: string, content: string) => {
    set((state) => {
      const updatedConversations: Record<string, Conversation[]> = {}
      
      Object.entries(state.conversations).forEach(([agentId, convs]) => {
        updatedConversations[agentId] = convs.map((conv) =>
          conv.id === conversationId
            ? {
                ...conv,
                messages: conv.messages.map((m) => (m.id === messageId ? { ...m, content } : m)),
              }
            : conv
        )
      })
      
      saveToStorage(updatedConversations)
      return { conversations: updatedConversations }
    })
  },

  updateConversationMessageThinking: (conversationId: string, messageId: string, thinking: string) => {
    set((state) => {
      const updatedConversations: Record<string, Conversation[]> = {}
      
      Object.entries(state.conversations).forEach(([agentId, convs]) => {
        updatedConversations[agentId] = convs.map((conv) =>
          conv.id === conversationId
            ? {
                ...conv,
                messages: conv.messages.map((m) => (m.id === messageId ? { ...m, thinking } : m)),
              }
            : conv
        )
      })
      
      saveToStorage(updatedConversations)
      return { conversations: updatedConversations }
    })
  },

  updateConversationMessageStreaming: (conversationId: string, messageId: string, isStreaming: boolean) => {
    set((state) => {
      const updatedConversations: Record<string, Conversation[]> = {}
      
      Object.entries(state.conversations).forEach(([agentId, convs]) => {
        updatedConversations[agentId] = convs.map((conv) =>
          conv.id === conversationId
            ? {
                ...conv,
                messages: conv.messages.map((m) => (m.id === messageId ? { ...m, isStreaming } : m)),
              }
            : conv
        )
      })
      
      saveToStorage(updatedConversations)
      return { conversations: updatedConversations }
    })
  },

  updateConversationMessageIsThinking: (conversationId: string, messageId: string, isThinking: boolean) => {
    set((state) => {
      const updatedConversations: Record<string, Conversation[]> = {}
      
      Object.entries(state.conversations).forEach(([agentId, convs]) => {
        updatedConversations[agentId] = convs.map((conv) =>
          conv.id === conversationId
            ? {
                ...conv,
                messages: conv.messages.map((m) => (m.id === messageId ? { ...m, isThinking } : m)),
              }
            : conv
        )
      })
      
      saveToStorage(updatedConversations)
      return { conversations: updatedConversations }
    })
  },

  setConversationTaskId: (conversationId: string, taskId: string | null) => {
    set((state) => {
      const updatedConversations: Record<string, Conversation[]> = {}
      
      Object.entries(state.conversations).forEach(([agentId, convs]) => {
        updatedConversations[agentId] = convs.map((conv) =>
          conv.id === conversationId
            ? { ...conv, taskId }
            : conv
        )
      })
      
      saveToStorage(updatedConversations)
      return { conversations: updatedConversations }
    })
  },

  getConversationGeneratingMessageId: (conversationId: string) => {
    const { conversations } = get()
    for (const agentConversations of Object.values(conversations)) {
      const found = agentConversations.find((conv) => conv.id === conversationId)
      if (found) return found.generatingMessageId || null
    }
    return null
  },

  getConversationTaskId: (conversationId: string) => {
    const { conversations } = get()
    for (const agentConversations of Object.values(conversations)) {
      const found = agentConversations.find((conv) => conv.id === conversationId)
      if (found) return found.taskId || null
    }
    return null
  },
}))
