export interface SchoolAgent {
  agent_id: string
  agent_name: string
  added_at: string
  agent_config: any  // Agent的完整配置信息
}

export interface MCPConfig {
  mcp_id: string
  name: string
  description?: string
  mode: 'remote' | 'stdio'
  config: any
  enabled: boolean
  added_at: string
}

export interface School {
  id: string
  name: string
  agents: SchoolAgent[]
  tools?: any[]  // Tool 配置列表
  skills?: any[]  // Skills 配置列表
  mcps?: MCPConfig[]  // MCP 配置列表
  created_at: string
  updated_at: string
}

export interface SchoolCreate {
  name: string
}

export interface SchoolUpdate {
  name?: string
}

export interface AddAgentToSchoolRequest {
  agent_id: string
  agent_name: string
  agent_config: any
}

export interface AgentSchoolInfo {
  school_id: string | null
  school_name: string | null
  agent: SchoolAgent | null
}
