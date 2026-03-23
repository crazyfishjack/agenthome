import { create } from 'zustand'
import client from '../api/client'

export interface ToolConfig {
  tool_name: string
  tool_description: string
  parameter_requirements: string
  format_requirements: string
  examples: string[]
  enabled: boolean
}

interface ToolState {
  tools: ToolConfig[]
  isLoading: boolean
  error: string | null

  // Actions
  setTools: (tools: ToolConfig[]) => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void

  // Tool 操作
  scanTools: () => Promise<void>
  getToolConfig: (toolName: string) => Promise<ToolConfig>
}

export const useToolStore = create<ToolState>((set) => ({
  tools: [],
  isLoading: false,
  error: null,

  setTools: (tools) => set({ tools }),

  setLoading: (isLoading) => set({ isLoading }),

  setError: (error) => set({ error }),

  scanTools: async () => {
    set({ isLoading: true, error: null })
    try {
      const response = await client.get<{ tools: ToolConfig[]; total: number }>('/tools/scan')
      set({
        tools: response.data.tools,
        isLoading: false
      })
    } catch (error: any) {
      set({
        error: error.response?.data?.detail || '扫描工具失败',
        isLoading: false
      })
      throw error
    }
  },

  getToolConfig: async (toolName: string) => {
    try {
      const response = await client.get<ToolConfig>(`/tools/config/${toolName}`)
      return response.data
    } catch (error: any) {
      throw error
    }
  }
}))
