import { create } from 'zustand'

/**
 * SUB Agent 执行事件类型
 */
export interface SubAgentEvent {
  type: string
  execution_id: string
  timestamp: number
  data: Record<string, unknown>
}

/**
 * SUB Agent 执行状态
 */
export interface SubAgentExecution {
  executionId: string
  subagentType: string
  description: string
  status: 'pending' | 'running' | 'completed' | 'error'
  events: SubAgentEvent[]
  result?: string
  error?: string
  createdAt: number
  startedAt?: number
  completedAt?: number
  isModalOpen: boolean
  isMinimized: boolean
}

/**
 * SUB Agent Store 状态
 */
interface SubAgentState {
  // 所有执行记录
  executions: Map<string, SubAgentExecution>
  // 当前显示的弹窗 ID 列表
  visibleModalIds: string[]

  // Actions
  createExecution: (executionId: string, subagentType: string, description: string) => void
  updateExecutionStatus: (executionId: string, status: SubAgentExecution['status']) => void
  addEvent: (executionId: string, event: SubAgentEvent) => void
  setResult: (executionId: string, result: string) => void
  setError: (executionId: string, error: string) => void
  openModal: (executionId: string) => void
  closeModal: (executionId: string) => void
  minimizeModal: (executionId: string) => void
  restoreModal: (executionId: string) => void
  removeExecution: (executionId: string) => void
  getExecution: (executionId: string) => SubAgentExecution | undefined
  getAllExecutions: () => SubAgentExecution[]
  getVisibleExecutions: () => SubAgentExecution[]
  hasExecution: (executionId: string) => boolean
}

export const useSubAgentStore = create<SubAgentState>((set, get) => ({
  executions: new Map(),
  visibleModalIds: [],

  /**
   * 创建新的执行记录
   */
  createExecution: (executionId, subagentType, description) => {
    console.log('[subAgentStore] createExecution:', executionId)
    set((state) => {
      const newExecutions = new Map(state.executions)
      newExecutions.set(executionId, {
        executionId,
        subagentType,
        description,
        status: 'pending',
        events: [],
        createdAt: Date.now(),
        isModalOpen: false,
        isMinimized: false,
      })
      return { executions: newExecutions }
    })
  },

  /**
   * 更新执行状态
   */
  updateExecutionStatus: (executionId, status) => {
    console.log('[subAgentStore] updateExecutionStatus:', executionId, status)
    set((state) => {
      const execution = state.executions.get(executionId)
      if (!execution) return state

      const newExecutions = new Map(state.executions)
      const updatedExecution = { ...execution, status }

      if (status === 'running' && !execution.startedAt) {
        updatedExecution.startedAt = Date.now()
      }
      if (status === 'completed' || status === 'error') {
        updatedExecution.completedAt = Date.now()
      }

      newExecutions.set(executionId, updatedExecution)
      return { executions: newExecutions }
    })
  },

  /**
   * 添加事件到执行记录
   */
  addEvent: (executionId, event) => {
    console.log('[subAgentStore] addEvent:', executionId, event.type)
    set((state) => {
      const execution = state.executions.get(executionId)
      if (!execution) return state

      const newExecutions = new Map(state.executions)
      newExecutions.set(executionId, {
        ...execution,
        events: [...execution.events, event],
      })
      return { executions: newExecutions }
    })
  },

  /**
   * 设置执行结果
   */
  setResult: (executionId, result) => {
    set((state) => {
      const execution = state.executions.get(executionId)
      if (!execution) return state

      const newExecutions = new Map(state.executions)
      newExecutions.set(executionId, {
        ...execution,
        result,
        status: 'completed',
        completedAt: Date.now(),
      })
      return { executions: newExecutions }
    })
  },

  /**
   * 设置执行错误
   */
  setError: (executionId, error) => {
    set((state) => {
      const execution = state.executions.get(executionId)
      if (!execution) return state

      const newExecutions = new Map(state.executions)
      newExecutions.set(executionId, {
        ...execution,
        error,
        status: 'error',
        completedAt: Date.now(),
      })
      return { executions: newExecutions }
    })
  },

  /**
   * 打开弹窗
   */
  openModal: (executionId) => {
    console.log('[subAgentStore] openModal:', executionId)
    set((state) => {
      const execution = state.executions.get(executionId)
      if (!execution) return state

      console.log('[subAgentStore] execution.isModalOpen:', execution.isModalOpen)

      const newExecutions = new Map(state.executions)
      newExecutions.set(executionId, {
        ...execution,
        isModalOpen: true,
        isMinimized: false,
      })

      // 添加到可见列表
      const newVisibleIds = state.visibleModalIds.includes(executionId)
        ? state.visibleModalIds
        : [...state.visibleModalIds, executionId]

      console.log('[subAgentStore] 添加到 visibleModalIds:', executionId, '当前列表:', newVisibleIds)

      return { executions: newExecutions, visibleModalIds: newVisibleIds }
    })
  },

  /**
   * 关闭弹窗
   */
  closeModal: (executionId) => {
    set((state) => {
      const execution = state.executions.get(executionId)
      if (!execution) return state

      const newExecutions = new Map(state.executions)
      newExecutions.set(executionId, {
        ...execution,
        isModalOpen: false,
      })

      // 从可见列表移除
      const newVisibleIds = state.visibleModalIds.filter(id => id !== executionId)

      return { executions: newExecutions, visibleModalIds: newVisibleIds }
    })
  },

  /**
   * 最小化弹窗
   */
  minimizeModal: (executionId) => {
    set((state) => {
      const execution = state.executions.get(executionId)
      if (!execution) return state

      const newExecutions = new Map(state.executions)
      newExecutions.set(executionId, {
        ...execution,
        isMinimized: true,
      })

      // 从可见列表移除
      const newVisibleIds = state.visibleModalIds.filter(id => id !== executionId)

      return { executions: newExecutions, visibleModalIds: newVisibleIds }
    })
  },

  /**
   * 恢复弹窗
   */
  restoreModal: (executionId) => {
    set((state) => {
      const execution = state.executions.get(executionId)
      if (!execution) return state

      const newExecutions = new Map(state.executions)
      newExecutions.set(executionId, {
        ...execution,
        isMinimized: false,
        isModalOpen: true,
      })

      // 添加到可见列表
      const newVisibleIds = state.visibleModalIds.includes(executionId)
        ? state.visibleModalIds
        : [...state.visibleModalIds, executionId]

      return { executions: newExecutions, visibleModalIds: newVisibleIds }
    })
  },

  /**
   * 移除执行记录
   */
  removeExecution: (executionId) => {
    set((state) => {
      const newExecutions = new Map(state.executions)
      newExecutions.delete(executionId)

      const newVisibleIds = state.visibleModalIds.filter(id => id !== executionId)

      return { executions: newExecutions, visibleModalIds: newVisibleIds }
    })
  },

  /**
   * 获取执行记录
   */
  getExecution: (executionId) => {
    return get().executions.get(executionId)
  },

  /**
   * 获取所有执行记录
   */
  getAllExecutions: () => {
    return Array.from(get().executions.values())
  },

  /**
   * 获取可见的执行记录
   */
  getVisibleExecutions: () => {
    return get().visibleModalIds
      .map(id => get().executions.get(id))
      .filter((exec): exec is SubAgentExecution => exec !== undefined && !exec.isMinimized)
  },

  /**
   * 检查是否存在执行记录
   */
  hasExecution: (executionId) => {
    return get().executions.has(executionId)
  },
}))

export default useSubAgentStore
