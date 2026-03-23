import type { ModelConfig } from './model'

export interface SubAgentConfig {
  agent_id: string
  agent_name: string
  custom_name: string
  description: string
  agent_config: Partial<ModelConfig> & {
    enable_search?: boolean
    enable_thinking?: boolean
    [key: string]: any
  }
}

export interface AgentTeam {
  id: string
  name: string
  main_agent_id: string
  main_agent_name: string
  main_agent_config: Partial<ModelConfig> & {
    enable_search?: boolean
    enable_thinking?: boolean
    [key: string]: any
  }
  sub_agents: SubAgentConfig[]
  enable_search?: boolean
  enable_thinking?: boolean
  status: 'creating' | 'success' | 'failed' | 'not_instantiated'
  created_at: string
  updated_at: string
}

export interface CreateTeamRequest {
  name: string
  main_agent_id: string
  main_agent_name: string
  main_agent_config: Partial<ModelConfig> & {
    enable_search?: boolean
    enable_thinking?: boolean
    [key: string]: any
  }
  sub_agents: SubAgentConfig[]
  enable_search?: boolean
  enable_thinking?: boolean
}

export interface UpdateTeamRequest {
  name: string
  main_agent_id: string
  main_agent_name: string
  main_agent_config: Partial<ModelConfig> & {
    enable_search?: boolean
    enable_thinking?: boolean
    [key: string]: any
  }
  sub_agents: SubAgentConfig[]
  enable_search?: boolean
  enable_thinking?: boolean
}

export interface TeamInstantiationStatus {
  team_id: string
  is_instantiated: boolean
  status: string
  is_instantiating?: boolean
}
