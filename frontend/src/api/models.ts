import client from './client'
import type { ModelConfig, ModelUpdate, ModelConfigCreate, TestResult, Provider, OllamaSearchResult } from '@/types/model'

export const modelsApi = {
  getAll: () => client.get<ModelConfig[]>('/models').then(res => res.data),
  
  getById: (id: string) => client.get<ModelConfig>(`/models/${id}`).then(res => res.data),
  
  getConfigs: () => client.get<ModelConfig[]>('/models/config').then(res => res.data),
  
  getConfigById: (id: string) => client.get<ModelConfig>(`/models/config/${id}`).then(res => res.data),
  
  createConfig: (config: ModelConfigCreate) => client.post<ModelConfig>('/models/config', config).then(res => res.data),
  
  updateConfig: (id: string, config: ModelUpdate) => client.put<ModelConfig>(`/models/config/${id}`, config).then(res => res.data),
  
  deleteConfig: (id: string) => client.delete(`/models/config/${id}`).then(res => res.data),
  
  testConnection: (id: string) => client.post<TestResult>(`/models/config/${id}/test`).then(res => res.data),
  
  getProviders: () => client.get<Provider[]>('/models/providers').then(res => res.data),
  
  getProviderModels: (provider: string) => client.get<string[]>(`/models/providers/${provider}/models`).then(res => res.data),
  
  searchOllama: async () => {
    const result = await client.post<OllamaSearchResult>('/models/ollama/search')
    return result.data
  },
}
