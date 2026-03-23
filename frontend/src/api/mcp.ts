import client from './client'
import type { MCPConfig } from '@/types/school'

export const mcpApi = {
  // 获取所有 MCP
  getAll: async () => {
    const response = await client.get<{ mcps: MCPConfig[] }>('/mcp/mcps')
    return response.data.mcps
  },

  // 获取指定 MCP
  getById: async (mcpId: string) => {
    const response = await client.get<MCPConfig>(`/mcp/mcps/${mcpId}`)
    return response.data
  },

  // 创建 MCP
  create: async (data: {
    name: string
    description?: string
    mode: 'remote' | 'stdio'
    config: any
  }) => {
    const response = await client.post<MCPConfig>('/mcp/mcps', data)
    return response.data
  },

  // 更新 MCP
  update: async (mcpId: string, data: {
    name?: string
    description?: string
    mode?: 'remote' | 'stdio'
    config?: any
    enabled?: boolean
  }) => {
    const response = await client.put<MCPConfig>(`/mcp/mcps/${mcpId}`, data)
    return response.data
  },

  // 删除 MCP
  delete: async (mcpId: string) => {
    const response = await client.delete(`/mcp/mcps/${mcpId}`)
    return response.data
  },

  // 启用/禁用 MCP
  toggle: async (mcpId: string, enabled: boolean) => {
    const response = await client.patch(`/mcp/mcps/${mcpId}/toggle`, null, {
      params: { enabled }
    })
    return response.data
  },

  // 获取 MCP 的工具列表
  getMcpTools: async (mcpId: string) => {
    const response = await client.get<{ tools: string[] }>(`/mcp/mcps/${mcpId}/tools`)
    return response.data.tools
  },

  // 获取 School 的 MCP 列表
  getSchoolMcps: async (schoolId: string) => {
    const response = await client.get<{ mcps: MCPConfig[] }>(`/mcp/schools/${schoolId}/mcps`)
    return response.data.mcps
  },

  // 更新 School 的 MCP 列表
  updateSchoolMcps: async (schoolId: string, data: { mcps: MCPConfig[] }) => {
    const response = await client.post(`/mcp/schools/${schoolId}/mcps`, data)
    return response.data
  },

  // 启用/禁用 School 的 MCP
  toggleSchoolMcp: async (schoolId: string, mcpId: string, enabled: boolean) => {
    const response = await client.patch(`/mcp/schools/${schoolId}/mcps/${mcpId}`, null, {
      params: { enabled }
    })
    return response.data
  }
}
