export interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  thinking?: string  // 深度思考内容
  images?: string[]
  timestamp: string
  isStreaming?: boolean  // 是否正在流式输出
  isThinking?: boolean  // 是否正在思考中
  checkpointInfo?: CheckpointInfo  // checkpoint信息
}

export interface CheckpointInfo {
  thread_id: string
  checkpoint_id: string
  parent_checkpoint_id?: string
}

export interface ChatRequest {
  model_config_id: string
  message: string
  images?: string[]
  model?: string
  history?: Message[]
  school_id?: string  // 新增：school_id，用于标识是否使用school中的agent
  conversation_id?: string  // 新增：conversation_id，用于checkpoint隔离
  checkpointInfo?: CheckpointInfo  // checkpoint信息（可选）
}

// Team 聊天请求
export interface TeamChatRequest {
  team_id: string
  message: string
  images?: string[]
  history?: Message[]
  conversation_id?: string  // 用于checkpoint隔离
}

export interface ChatResponse {
  id: string
  role: 'assistant'
  content: string
  thinking?: string  // 深度思考内容
  timestamp: string
}

export interface StreamChunk {
  type: 'task_id' | 'thinking_start' | 'thinking_content' | 'thinking_end' | 'content' | 'done' | 'error' | 'cancelled' | 'checkpoint_info' | 'interrupt' | 'interrupt_rejected'
  content?: string
  error?: string
  task_id?: string
  message?: string
  thread_id?: string
  checkpoint_id?: string
  parent_checkpoint_id?: string
  tool_name?: string
  tool_args?: Record<string, any>
}

export interface InterruptData {
  tool_name: string
  tool_args: Record<string, any>
  thread_id: string
}

export interface InterruptDecisionRequest {
  thread_id: string
  decision: 'approve' | 'reject'
}
