export interface ModelConfig {
  id: string
  name: string
  provider: 'openai' | 'anthropic' | 'ollama' | 'aliyun' | 'custom'
  type: 'api' | 'local'
  api_key?: string
  api_base?: string
  model: string
  temperature: number
  max_tokens: number
  thinking?: boolean
  top_p?: number
  top_k?: number
  repeat_penalty?: number
  presence_penalty?: number
  system_prompt?: string
  is_tested?: boolean
  is_testing?: boolean
  test_result?: TestResult
  created_at: string
  updated_at: string
}

export interface TestResult {
  success: boolean
  message: string
  timestamp: string
  latency?: number
}

export interface OllamaSearchResult {
  found: boolean
  api_base?: string
  models: string[]
  message: string
}

export interface ModelUpdate {
  api_key?: string
  api_base?: string
  temperature?: number
  max_tokens?: number
  thinking?: boolean
  top_p?: number
  top_k?: number
  repeat_penalty?: number
  presence_penalty?: number
  system_prompt?: string
}

export interface ModelConfigCreate {
  name: string
  provider: 'openai' | 'anthropic' | 'ollama' | 'aliyun' | 'custom'
  type: 'api' | 'local'
  api_key?: string
  api_base?: string
  model: string
  temperature?: number
  max_tokens?: number
  thinking?: boolean
  top_p?: number
  top_k?: number
  repeat_penalty?: number
  presence_penalty?: number
  system_prompt?: string
}

export interface Provider {
  id: string
  name: string
  description: string
  icon: string
  type: 'api' | 'local'
  default_api_base?: string
  requires_api_key: boolean
}

export interface WizardState {
  isOpen: boolean
  currentStep: number
  agentId: string | null
  formData: Partial<ModelConfigCreate>
  testResult: TestResult | null
}
