import { create } from 'zustand'

interface GenerationState {
  // 当前正在生成的会话ID
  generatingConversationId: string | null
  // 当前正在生成的agent ID
  generatingAgentId: string | null
  // 当前正在生成的消息ID
  generatingMessageId: string | null
  // AbortController
  abortController: AbortController | null
  // 任务ID
  taskId: string | null

  // Actions
  startGeneration: (conversationId: string, agentId: string, messageId: string, controller: AbortController, taskId?: string) => void
  stopGeneration: () => void
  isAnyConversationGenerating: () => boolean
  isConversationGenerating: (conversationId: string) => boolean
  isAgentGenerating: (agentId: string) => boolean
  getGeneratingConversationId: () => string | null
  getGeneratingAgentId: () => string | null
}

export const useGlobalGenerationStore = create<GenerationState>((set, get) => ({
  generatingConversationId: null,
  generatingAgentId: null,
  generatingMessageId: null,
  abortController: null,
  taskId: null,

  startGeneration: (conversationId, agentId, messageId, controller, taskId) =>
    set({
      generatingConversationId: conversationId,
      generatingAgentId: agentId,
      generatingMessageId: messageId,
      abortController: controller,
      taskId: taskId || null,
    }),

  stopGeneration: () => {
    const { abortController } = get()
    if (abortController) {
      abortController.abort()
    }
    set({
      generatingConversationId: null,
      generatingAgentId: null,
      generatingMessageId: null,
      abortController: null,
      taskId: null,
    })
  },

  isAnyConversationGenerating: () => {
    const { generatingConversationId } = get()
    return generatingConversationId !== null
  },

  isConversationGenerating: (conversationId) => {
    const { generatingConversationId } = get()
    return generatingConversationId === conversationId
  },

  isAgentGenerating: (agentId) => {
    const { generatingAgentId } = get()
    return generatingAgentId === agentId
  },

  getGeneratingConversationId: () => {
    return get().generatingConversationId
  },

  getGeneratingAgentId: () => {
    return get().generatingAgentId
  },
}))
