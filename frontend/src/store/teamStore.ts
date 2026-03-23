import { create } from 'zustand'
import type { AgentTeam, CreateTeamRequest, UpdateTeamRequest } from '@/types/team'
import { teamsApi } from '@/api/teams'

interface TeamState {
  teams: AgentTeam[]
  isLoading: boolean
  error: string | null
  teamInstantiationStatus: Record<string, {
    is_instantiated: boolean
    status: string
    is_instantiating?: boolean
  }>
  // 全局Team更新状态
  updatingTeamId: string | null
  isUpdating: boolean

  // Actions
  setTeams: (teams: AgentTeam[]) => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void

  // Team操作
  createTeam: (data: CreateTeamRequest) => Promise<AgentTeam>
  updateTeam: (teamId: string, data: UpdateTeamRequest) => Promise<void>
  deleteTeam: (teamId: string) => Promise<void>
  loadTeams: () => Promise<void>

  // Team实例化操作
  instantiateTeam: (teamId: string) => Promise<void>
  loadTeamInstantiationStatus: (teamId: string) => Promise<void>
  loadAllTeamInstantiationStatus: (teamIds: string[]) => Promise<void>

  // 查询
  getTeamById: (teamId: string) => AgentTeam | undefined
  isTeamInstantiated: (teamId: string) => boolean
  isTeamInstantiating: (teamId: string) => boolean
  isTeamUpdating: (teamId: string) => boolean
}

export const useTeamStore = create<TeamState>((set, get) => ({
  teams: [],
  isLoading: false,
  error: null,
  teamInstantiationStatus: {},
  // 全局Team更新状态
  updatingTeamId: null,
  isUpdating: false,

  setTeams: (teams) => set({ teams }),

  setLoading: (isLoading) => set({ isLoading }),

  setError: (error) => set({ error }),

  createTeam: async (data) => {
    set({ isLoading: true, error: null })
    try {
      const newTeam = await teamsApi.create(data)
      set((state) => ({
        teams: [...state.teams, newTeam],
        isLoading: false
      }))
      return newTeam
    } catch (error: any) {
      set({
        error: error.response?.data?.detail || '创建Team失败',
        isLoading: false
      })
      throw error
    }
  },

  updateTeam: async (teamId, data) => {
    set({ isLoading: true, error: null, updatingTeamId: teamId, isUpdating: true })
    try {
      const updatedTeam = await teamsApi.update(teamId, data)
      set((state) => ({
        teams: state.teams.map(t => t.id === teamId ? updatedTeam : t),
        isLoading: false,
        updatingTeamId: null,
        isUpdating: false
      }))
    } catch (error: any) {
      set({
        error: error.response?.data?.detail || '更新Team失败',
        isLoading: false,
        updatingTeamId: null,
        isUpdating: false
      })
      throw error
    }
  },

  deleteTeam: async (teamId) => {
    set({ isLoading: true, error: null })
    try {
      await teamsApi.delete(teamId)
      set((state) => ({
        teams: state.teams.filter(t => t.id !== teamId),
        isLoading: false
      }))
    } catch (error: any) {
      set({
        error: error.response?.data?.detail || '删除Team失败',
        isLoading: false
      })
      throw error
    }
  },

  loadTeams: async () => {
    set({ isLoading: true, error: null })
    try {
      const teams = await teamsApi.getAll()
      set({ teams, isLoading: false })
    } catch (error: any) {
      set({
        error: error.response?.data?.detail || '加载Teams失败',
        isLoading: false
      })
    }
  },

  instantiateTeam: async (teamId) => {
    set((state) => ({
      teamInstantiationStatus: {
        ...state.teamInstantiationStatus,
        [teamId]: {
          ...state.teamInstantiationStatus[teamId],
          is_instantiating: true
        }
      }
    }))

    try {
      await teamsApi.instantiate(teamId)
      set((state) => ({
        teamInstantiationStatus: {
          ...state.teamInstantiationStatus,
          [teamId]: {
            is_instantiated: true,
            status: 'instantiated',
            is_instantiating: false
          }
        }
      }))
    } catch (error: any) {
      console.error(`Failed to instantiate team ${teamId}:`, error)
      set((state) => ({
        teamInstantiationStatus: {
          ...state.teamInstantiationStatus,
          [teamId]: {
            ...state.teamInstantiationStatus[teamId],
            is_instantiating: false
          }
        }
      }))
      throw error
    }
  },

  loadTeamInstantiationStatus: async (teamId) => {
    try {
      const status = await teamsApi.getInstantiationStatus(teamId)
      set((state) => ({
        teamInstantiationStatus: {
          ...state.teamInstantiationStatus,
          [teamId]: {
            is_instantiated: status.is_instantiated,
            status: status.status,
            is_instantiating: false
          }
        }
      }))
    } catch (error: any) {
      console.error(`Failed to load instantiation status for team ${teamId}:`, error)
    }
  },

  loadAllTeamInstantiationStatus: async (teamIds) => {
    await Promise.all(
      teamIds.map(teamId => get().loadTeamInstantiationStatus(teamId))
    )
  },

  getTeamById: (teamId) => {
    return get().teams.find(t => t.id === teamId)
  },

  isTeamInstantiated: (teamId) => {
    const status = get().teamInstantiationStatus[teamId]
    return status?.is_instantiated === true
  },

  isTeamInstantiating: (teamId) => {
    const status = get().teamInstantiationStatus[teamId]
    return status?.is_instantiating === true
  },

  isTeamUpdating: (teamId) => {
    return get().updatingTeamId === teamId && get().isUpdating
  }
}))
