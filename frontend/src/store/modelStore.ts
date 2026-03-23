import { create } from 'zustand'
import type { ModelConfig, ModelConfigCreate, TestResult, Provider, WizardState } from '@/types/model'
import type { AgentTeam } from '@/types/team'

// 统一的选中项类型，可以是普通 Agent 或 Team
export type SelectedEntity = 
  | { type: 'agent'; entity: ModelConfig }
  | { type: 'team'; entity: AgentTeam }
  | null

interface ModelState {
  models: ModelConfig[]
  selectedModel: ModelConfig | null
  selectedEntity: SelectedEntity  // 新增：统一的选中项（Agent 或 Team）
  isLoading: boolean
  error: string | null
  
  wizardState: WizardState
  providers: Provider[]
  providerModels: Record<string, string[]>
  
  setModels: (models: ModelConfig[]) => void
  setSelectedModel: (model: ModelConfig | null) => void
  setSelectedEntity: (entity: SelectedEntity) => void  // 新增：设置选中的实体
  updateModelConfig: (id: string, config: Partial<ModelConfig>) => void
  addModel: (model: ModelConfig) => void
  removeModel: (id: string) => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  
  setModelTesting: (id: string, isTesting: boolean) => void
  setModelTestResult: (id: string, result: TestResult) => void
  
  openWizard: (agentId: string) => void
  closeWizard: () => void
  setWizardStep: (step: number) => void
  setWizardFormData: (data: Partial<ModelConfigCreate>) => void
  setTestResult: (result: TestResult | null) => void
  setProviders: (providers: Provider[]) => void
  setProviderModels: (provider: string, models: string[]) => void
}

export const useModelStore = create<ModelState>((set) => ({
  models: [],
  selectedModel: null,
  selectedEntity: null,  // 新增：初始为 null
  isLoading: false,
  error: null,
  
  wizardState: {
    isOpen: false,
    currentStep: 0,
    agentId: null,
    formData: {},
    testResult: null,
  },
  
  providers: [],
  providerModels: {},
  
  setModels: (models) => set({ models }),
  
  setSelectedModel: (model) => set({ selectedModel: model }),
  
  setSelectedEntity: (entity) => set({ selectedEntity: entity }),  // 新增：设置选中的实体
  
  updateModelConfig: (id, config) =>
    set((state) => ({
      models: state.models.map((m) => (m.id === id ? { ...m, ...config } : m)),
      selectedModel: state.selectedModel?.id === id ? { ...state.selectedModel, ...config } : state.selectedModel,
    })),
  
  addModel: (model) =>
    set((state) => ({
      models: [...state.models, model],
    })),
  
  removeModel: (id) =>
    set((state) => ({
      models: state.models.filter((m) => m.id !== id),
      selectedModel: state.selectedModel?.id === id ? null : state.selectedModel,
    })),
  
  setLoading: (isLoading) => set({ isLoading }),
  
  setError: (error) => set({ error }),
  
  setModelTesting: (id, isTesting) =>
    set((state) => ({
      models: state.models.map((m) => (m.id === id ? { ...m, is_testing: isTesting } : m)),
      selectedModel: state.selectedModel?.id === id ? { ...state.selectedModel, is_testing: isTesting } : state.selectedModel,
    })),
  
  setModelTestResult: (id, result) =>
    set((state) => ({
      models: state.models.map((m) => 
        m.id === id ? { ...m, is_tested: true, is_testing: false, test_result: result } : m
      ),
      selectedModel: state.selectedModel?.id === id 
        ? { ...state.selectedModel, is_tested: true, is_testing: false, test_result: result } 
        : state.selectedModel,
    })),
  
  openWizard: (agentId) =>
    set((state) => ({
      wizardState: {
        ...state.wizardState,
        isOpen: true,
        currentStep: 0,
        agentId,
        formData: {},
        testResult: null,
      },
    })),
  
  closeWizard: () =>
    set((state) => ({
      wizardState: {
        ...state.wizardState,
        isOpen: false,
        currentStep: 0,
        agentId: null,
        formData: {},
        testResult: null,
      },
    })),
  
  setWizardStep: (step) =>
    set((state) => ({
      wizardState: {
        ...state.wizardState,
        currentStep: step,
      },
    })),
  
  setWizardFormData: (data) =>
    set((state) => ({
      wizardState: {
        ...state.wizardState,
        formData: { ...state.wizardState.formData, ...data },
      },
    })),
  
  setTestResult: (result) =>
    set((state) => ({
      wizardState: {
        ...state.wizardState,
        testResult: result,
      },
    })),
  
  setProviders: (providers) => set({ providers }),
  
  setProviderModels: (provider, models) =>
    set((state) => ({
      providerModels: {
        ...state.providerModels,
        [provider]: models,
      },
    })),
}))
