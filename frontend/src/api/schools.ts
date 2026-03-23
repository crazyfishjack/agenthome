import client from './client'
import type {
  School,
  SchoolCreate,
  SchoolUpdate,
  AddAgentToSchoolRequest,
  AgentSchoolInfo
} from '@/types/school'
import type { ToolConfig } from '@/store/toolStore'

export const schoolsApi = {
  // 获取所有School
  getAll: async () => {
    const response = await client.get<{ schools: School[] }>('/schools/schools')
    return response.data.schools
  },

  // 获取指定School
  getById: async (schoolId: string) => {
    const response = await client.get<School>(`/schools/schools/${schoolId}`)
    return response.data
  },

  // 创建School
  create: async (data: SchoolCreate) => {
    const response = await client.post<School>('/schools/schools', data)
    return response.data
  },

  // 更新School
  update: async (schoolId: string, data: SchoolUpdate) => {
    const response = await client.put<School>(`/schools/schools/${schoolId}`, data)
    return response.data
  },

  // 删除School
  delete: async (schoolId: string) => {
    const response = await client.delete(`/schools/schools/${schoolId}`)
    return response.data
  },

  // 添加Agent到School
  addAgent: async (schoolId: string, data: AddAgentToSchoolRequest) => {
    const response = await client.post(`/schools/schools/${schoolId}/agents`, data)
    return response.data
  },

  // 从School移除Agent
  removeAgent: async (schoolId: string, agentId: string) => {
    const response = await client.delete(`/schools/schools/${schoolId}/agents/${agentId}`)
    return response.data
  },

  // 获取School中的所有Agent
  getAgents: async (schoolId: string) => {
    const response = await client.get<{ agents: any[] }>(`/schools/schools/${schoolId}/agents`)
    return response.data.agents
  },

  // 获取School中的所有Tool
  getSchoolTools: async (schoolId: string) => {
    const response = await client.get<{ tools: ToolConfig[] }>(`/schools/schools/${schoolId}/tools`)
    return response.data.tools
  },

  // 更新School的Tool列表
  updateSchoolTools: async (schoolId: string, data: { tools: ToolConfig[] }) => {
    const response = await client.post(`/schools/schools/${schoolId}/tools`, data)
    return response.data
  },

  // 获取Agent所在的School
  getAgentSchool: async (agentId: string) => {
    const response = await client.get<AgentSchoolInfo>(`/schools/agent/${agentId}/school`)
    return response.data
  },

  // 获取Agent的实例化状态
  getAgentInstantiationStatus: async (agentId: string) => {
    const response = await client.get<{
      agent_id: string
      is_instantiated: boolean
      status: string
    }>(`/schools/agent/${agentId}/instantiation-status`)
    return response.data
  },

  // 实例化Agent
  instantiateAgent: async (agentId: string) => {
    const response = await client.post<{
      agent_id: string
      is_instantiated: boolean
      status: string
      message: string
    }>(`/schools/agent/${agentId}/instantiate`)
    return response.data
  },

  // 获取所有可用的 Skills
  getAllSkills: async () => {
    const response = await client.get<{ skills: any[] }>('/schools/skills')
    return response.data.skills
  },

  // 获取School中的所有Skill
  getSchoolSkills: async (schoolId: string) => {
    const response = await client.get<{ skills: any[] }>(`/schools/schools/${schoolId}/skills`)
    return response.data.skills
  },

  // 更新School的Skill列表
  updateSchoolSkills: async (schoolId: string, data: { skills: any[] }) => {
    const response = await client.post(`/schools/schools/${schoolId}/skills`, data)
    return response.data
  },

  // 启用/禁用School的Skill
  toggleSchoolSkill: async (schoolId: string, skillId: string, enabled: boolean) => {
    const response = await client.patch(`/schools/schools/${schoolId}/skills/${skillId}`, { enabled })
    return response.data
  }
}
