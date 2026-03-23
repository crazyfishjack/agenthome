import client from './client'
import type { ChatRequest, ChatResponse, StreamChunk, CheckpointInfo, InterruptDecisionRequest, TeamChatRequest } from '@/types/chat'

export const chatApi = {
  sendMessage: (data: ChatRequest, signal?: AbortSignal) => 
    client.post<ChatResponse>('/chat/message', data, { signal }).then(res => res.data),
  
  // Team 聊天流式接口
  streamTeamMessage: async (data: TeamChatRequest, signal?: AbortSignal, onChunk?: (chunk: StreamChunk) => void) => {
    const response = await fetch(`${client.defaults.baseURL}/teams/teams/${data.team_id}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
      signal,
    })
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    
    const reader = response.body?.getReader()
    const decoder = new TextDecoder()
    
    if (!reader) {
      throw new Error('Response body is not readable')
    }
    
    try {
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        
        const chunk = decoder.decode(value)
        const lines = chunk.split('\n')
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6)
            if (data.trim()) {
              try {
                const parsed = JSON.parse(data) as StreamChunk
                console.log('[API Chat] Received team chunk:', parsed)
                if (onChunk) {
                  onChunk(parsed)
                }
              } catch (e) {
                console.error('Failed to parse SSE data:', data, e)
              }
            }
          }
        }
      }
    } finally {
      reader.releaseLock()
    }
  },
  
  streamMessage: async (data: ChatRequest, signal?: AbortSignal, onChunk?: (chunk: StreamChunk) => void) => {
    const response = await fetch(`${client.defaults.baseURL}/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
      signal,
    })
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    
    const reader = response.body?.getReader()
    const decoder = new TextDecoder()
    
    if (!reader) {
      throw new Error('Response body is not readable')
    }
    
    try {
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        
        const chunk = decoder.decode(value)
        const lines = chunk.split('\n')
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6)
            if (data.trim()) {
              try {
                const parsed = JSON.parse(data) as StreamChunk
                console.log('[API Chat] Received chunk:', parsed)
                if (onChunk) {
                  onChunk(parsed)
                }
              } catch (e) {
                console.error('Failed to parse SSE data:', data, e)
              }
            }
          }
        }
      }
    } finally {
      reader.releaseLock()
    }
  },

  cancelTask: async (taskId: string) => {
    const params = new URLSearchParams()
    params.append('task_id', taskId)
    return client.post(`/chat/cancel?${params.toString()}`).then(res => res.data)
  },

  deleteConversation: async (agentId: string, conversationId: string) => {
    return client.delete(`/chat/conversation/${agentId}/${conversationId}`).then(res => res.data)
  },

  getLatestCheckpoint: async (agentId: string, conversationId: string) => {
    const response = await client.get<{success: boolean, data?: CheckpointInfo, message?: string}>(
      `/chat/checkpoint/${agentId}/latest`,
      { params: { conversation_id: conversationId } }
    )
    return response.data
  },

  addCheckpoint: async (agentId: string, sourceCheckpointId: string, targetThreadId: string) => {
    const response = await client.post<{success: boolean, message?: string}>(
      `/chat/checkpoint/${agentId}/copy`,
      {
        source_checkpoint_id: sourceCheckpointId,
        target_thread_id: targetThreadId
      }
    )
    return response.data
  },

  getOutputDir: async () => {
    const response = await client.get<{success: boolean, path: string}>('/chat/output-dir')
    return response.data
  },

  setOutputDir: async (path: string) => {
    const response = await client.post<{success: boolean, message: string, path: string}>(
      '/chat/output-dir',
      { path }
    )
    return response.data
  },

  sendInterruptDecision: async (request: InterruptDecisionRequest) => {
    const response = await client.post<{success: boolean, message: string}>(
      '/chat/interrupt-decision',
      request
    )
    return response.data
  },
}
