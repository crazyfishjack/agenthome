import client from './client'
import type { AgentTeam, CreateTeamRequest, UpdateTeamRequest } from '@/types/team'

export const teamsApi = {
  // 获取所有Teams
  getAll: async () => {
    const response = await client.get<{ teams: AgentTeam[] }>('/teams/teams')
    return response.data.teams
  },

  // 获取指定Team
  getById: async (teamId: string) => {
    const response = await client.get<AgentTeam>(`/teams/teams/${teamId}`)
    return response.data
  },

  // 创建Team
  create: async (data: CreateTeamRequest) => {
    const response = await client.post<AgentTeam>('/teams/teams', data)
    return response.data
  },

  // 更新Team
  update: async (teamId: string, data: UpdateTeamRequest) => {
    const response = await client.put<AgentTeam>(`/teams/teams/${teamId}`, data)
    return response.data
  },

  // 删除Team
  delete: async (teamId: string) => {
    const response = await client.delete(`/teams/teams/${teamId}`)
    return response.data
  },

  // 获取Team的实例化状态
  getInstantiationStatus: async (teamId: string) => {
    const response = await client.get<{
      team_id: string
      is_instantiated: boolean
      status: string
    }>(`/teams/teams/${teamId}/instantiation-status`)
    return response.data
  },

  // 实例化Team
  instantiate: async (teamId: string) => {
    const response = await client.post<{
      team_id: string
      is_instantiated: boolean
      status: string
      message: string
    }>(`/teams/teams/${teamId}/instantiate`)
    return response.data
  }
}
