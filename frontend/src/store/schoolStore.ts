import { create } from 'zustand'
import type { School, AgentSchoolInfo } from '@/types/school'
import { schoolsApi } from '@/api/schools'

interface SchoolState {
  schools: School[]
  isLoading: boolean
  error: string | null
  agentSchools: Record<string, AgentSchoolInfo>  // agent_id -> school info
  agentInstantiationStatus: Record<string, {  // agent_id -> instantiation status
    is_instantiated: boolean
    status: string
    is_instantiating?: boolean  // 是否正在实例化中
  }>

  // Actions
  setSchools: (schools: School[]) => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void

  // School操作
  createSchool: (name: string) => Promise<School>
  updateSchool: (schoolId: string, name: string) => Promise<void>
  deleteSchool: (schoolId: string) => Promise<void>
  loadSchools: () => Promise<void>

  // Agent操作
  addAgentToSchool: (schoolId: string, agentId: string, agentName: string, agentConfig: any) => Promise<void>
  removeAgentFromSchool: (schoolId: string, agentId: string) => Promise<void>
  loadAgentSchool: (agentId: string) => Promise<void>
  loadAllAgentSchools: (agentIds: string[]) => Promise<void>

  // Agent实例化操作
  loadAgentInstantiationStatus: (agentId: string) => Promise<void>
  loadAllAgentInstantiationStatus: (agentIds: string[]) => Promise<void>
  instantiateAgent: (agentId: string) => Promise<void>

  // 查询
  getSchoolById: (schoolId: string) => School | undefined
  getAgentSchoolInfo: (agentId: string) => AgentSchoolInfo | undefined
  isAgentInSchool: (agentId: string) => boolean
  isAgentInstantiated: (agentId: string) => boolean
  isAgentInstantiating: (agentId: string) => boolean
}

export const useSchoolStore = create<SchoolState>((set, get) => ({
  schools: [],
  isLoading: false,
  error: null,
  agentSchools: {},
  agentInstantiationStatus: {},

  setSchools: (schools) => set({ schools }),

  setLoading: (isLoading) => set({ isLoading }),

  setError: (error) => set({ error }),

  createSchool: async (name) => {
    set({ isLoading: true, error: null })
    try {
      const newSchool = await schoolsApi.create({ name })
      set((state) => ({
        schools: [...state.schools, {
          ...newSchool,
          agents: newSchool.agents || []
        }],
        isLoading: false
      }))
      return newSchool
    } catch (error: any) {
      set({
        error: error.response?.data?.detail || '创建School失败',
        isLoading: false
      })
      throw error
    }
  },

  updateSchool: async (schoolId, name) => {
    set({ isLoading: true, error: null })
    try {
      await schoolsApi.update(schoolId, { name })
      set((state) => ({
        schools: state.schools.map(s =>
          s.id === schoolId ? { ...s, name } : s
        ),
        isLoading: false
      }))
    } catch (error: any) {
      set({
        error: error.response?.data?.detail || '更新School失败',
        isLoading: false
      })
      throw error
    }
  },

  deleteSchool: async (schoolId) => {
    set({ isLoading: true, error: null })
    try {
      await schoolsApi.delete(schoolId)
      set((state) => ({
        schools: state.schools.filter(s => s.id !== schoolId),
        isLoading: false
      }))
    } catch (error: any) {
      set({
        error: error.response?.data?.detail || '删除School失败',
        isLoading: false
      })
      throw error
    }
  },

  loadSchools: async () => {
    set({ isLoading: true, error: null })
    try {
      const schools = await schoolsApi.getAll()
      set({ 
        schools: schools.map(school => ({
          ...school,
          agents: school.agents || []
        })), 
        isLoading: false 
      })
    } catch (error: any) {
      set({
        error: error.response?.data?.detail || '加载Schools失败',
        isLoading: false
      })
    }
  },

  addAgentToSchool: async (schoolId, agentId, agentName, agentConfig) => {
    set({ isLoading: true, error: null })
    try {
      await schoolsApi.addAgent(schoolId, {
        agent_id: agentId,
        agent_name: agentName,
        agent_config: agentConfig
      })

      // 更新schools状态
      set((state) => ({
        schools: state.schools.map(s => {
          if (s.id === schoolId) {
            return {
              ...s,
              agents: [...s.agents, {
                agent_id: agentId,
                agent_name: agentName,
                added_at: new Date().toISOString(),
                agent_config: agentConfig
              }]
            }
          }
          return s
        }),
        agentSchools: {
          ...state.agentSchools,
          [agentId]: {
            school_id: schoolId,
            school_name: get().getSchoolById(schoolId)?.name || '',
            agent: {
              agent_id: agentId,
              agent_name: agentName,
              added_at: new Date().toISOString(),
              agent_config: agentConfig
            }
          }
        },
        isLoading: false
      }))
    } catch (error: any) {
      set({
        error: error.response?.data?.detail || '添加Agent到School失败',
        isLoading: false
      })
      throw error
    }
  },

  removeAgentFromSchool: async (schoolId, agentId) => {
    set({ isLoading: true, error: null })
    try {
      await schoolsApi.removeAgent(schoolId, agentId)

      // 更新schools状态
      set((state) => ({
        schools: state.schools.map(s => {
          if (s.id === schoolId) {
            return {
              ...s,
              agents: s.agents.filter(a => a.agent_id !== agentId)
            }
          }
          return s
        }),
        agentSchools: {
          ...state.agentSchools,
          [agentId]: {
            school_id: null,
            school_name: null,
            agent: null
          }
        },
        isLoading: false
      }))
    } catch (error: any) {
      set({
        error: error.response?.data?.detail || '从School移除Agent失败',
        isLoading: false
      })
      throw error
    }
  },

  loadAgentSchool: async (agentId) => {
    try {
      const schoolInfo = await schoolsApi.getAgentSchool(agentId)
      set((state) => ({
        agentSchools: {
          ...state.agentSchools,
          [agentId]: schoolInfo
        }
      }))
    } catch (error: any) {
      console.error(`Failed to load school for agent ${agentId}:`, error)
    }
  },

  loadAllAgentSchools: async (agentIds) => {
    // 并行加载所有agent的school信息
    await Promise.all(
      agentIds.map(agentId => get().loadAgentSchool(agentId))
    )
  },

  getSchoolById: (schoolId) => {
    return get().schools.find(s => s.id === schoolId)
  },

  getAgentSchoolInfo: (agentId) => {
    return get().agentSchools[agentId]
  },

  isAgentInSchool: (agentId) => {
    const schoolInfo = get().agentSchools[agentId]
    return schoolInfo?.school_id !== null
  },

  loadAgentInstantiationStatus: async (agentId) => {
    try {
      const status = await schoolsApi.getAgentInstantiationStatus(agentId)
      set((state) => ({
        agentInstantiationStatus: {
          ...state.agentInstantiationStatus,
          [agentId]: {
            is_instantiated: status.is_instantiated,
            status: status.status,
            is_instantiating: false
          }
        }
      }))
    } catch (error: any) {
      console.error(`Failed to load instantiation status for agent ${agentId}:`, error)
    }
  },

  loadAllAgentInstantiationStatus: async (agentIds) => {
    await Promise.all(
      agentIds.map(agentId => get().loadAgentInstantiationStatus(agentId))
    )
  },

  instantiateAgent: async (agentId) => {
    set((state) => ({
      agentInstantiationStatus: {
        ...state.agentInstantiationStatus,
        [agentId]: {
          ...state.agentInstantiationStatus[agentId],
          is_instantiating: true
        }
      }
    }))

    try {
      await schoolsApi.instantiateAgent(agentId)
      set((state) => ({
        agentInstantiationStatus: {
          ...state.agentInstantiationStatus,
          [agentId]: {
            is_instantiated: true,
            status: 'instantiated',
            is_instantiating: false
          }
        }
      }))
    } catch (error: any) {
      console.error(`Failed to instantiate agent ${agentId}:`, error)
      set((state) => ({
        agentInstantiationStatus: {
          ...state.agentInstantiationStatus,
          [agentId]: {
            ...state.agentInstantiationStatus[agentId],
            is_instantiating: false
          }
        }
      }))
      throw error
    }
  },

  isAgentInstantiated: (agentId) => {
    const status = get().agentInstantiationStatus[agentId]
    return status?.is_instantiated === true
  },

  isAgentInstantiating: (agentId) => {
    const status = get().agentInstantiationStatus[agentId]
    return status?.is_instantiating === true
  }
}))
