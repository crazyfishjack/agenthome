import { create } from 'zustand'
import type { Message } from '@/types/chat'
import type { ModelConfig } from '@/types/model'
import { chatApi } from '@/api/chat'

interface ChatState {
  messages: Message[]
  isLoading: boolean
  error: string | null
  selectedModelConfig: ModelConfig | null
  isGenerating: boolean
  abortController: AbortController | null
  streamingMessageId: string | null  // 当前流式输出的消息ID
  taskId: string | null  // 当前任务ID
  
  setMessages: (messages: Message[]) => void
  addMessage: (message: Message) => void
  updateMessage: (id: string, content: string) => void
  updateMessageThinking: (id: string, thinking: string) => void
  updateMessageStreaming: (id: string, isStreaming: boolean) => void
  updateMessageIsThinking: (id: string, isThinking: boolean) => void
  clearMessages: () => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  setSelectedModelConfig: (config: ModelConfig | null) => void
  startGeneration: (controller: AbortController, messageId?: string) => void
  stopGeneration: () => void
  cancelTask: (taskId: string) => Promise<void>
  setStreamingMessageId: (messageId: string | null) => void
  setTaskId: (taskId: string | null) => void
}

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  isLoading: false,
  error: null,
  selectedModelConfig: null,
  isGenerating: false,
  abortController: null,
  streamingMessageId: null,
  taskId: null,
  
  setMessages: (messages) => set({ messages }),
  
  addMessage: (message) => set((state) => ({ messages: [...state.messages, message] })),
  
  updateMessage: (id, content) =>
    set((state) => ({
      messages: state.messages.map((m) => (m.id === id ? { ...m, content } : m)),
    })),
  
  updateMessageThinking: (id, thinking) =>
    set((state) => ({
      messages: state.messages.map((m) => (m.id === id ? { ...m, thinking } : m)),
    })),
  
  updateMessageStreaming: (id, isStreaming) =>
    set((state) => ({
      messages: state.messages.map((m) => (m.id === id ? { ...m, isStreaming } : m)),
    })),
  
  updateMessageIsThinking: (id, isThinking) =>
    set((state) => ({
      messages: state.messages.map((m) => (m.id === id ? { ...m, isThinking } : m)),
    })),
  
  clearMessages: () => set({ messages: [] }),
  
  setLoading: (isLoading) => set({ isLoading }),
  
  setError: (error) => set({ error }),
  
  setSelectedModelConfig: (config) => set({ selectedModelConfig: config }),
  
  startGeneration: (controller, messageId) =>
    set({ isGenerating: true, abortController: controller, streamingMessageId: messageId || null }),
  
  stopGeneration: () => {
    const { abortController } = useChatStore.getState()
    if (abortController) {
      abortController.abort()
    }
    set({ isGenerating: false, abortController: null, streamingMessageId: null })
  },
  
  cancelTask: async (taskId) => {
    try {
      await chatApi.cancelTask(taskId)
      set({ isGenerating: false, abortController: null, streamingMessageId: null, taskId: null })
    } catch (error) {
      console.error('Failed to cancel task:', error)
    }
  },
  
  setStreamingMessageId: (messageId) => set({ streamingMessageId: messageId }),
  
  setTaskId: (taskId) => set({ taskId }),
}))
