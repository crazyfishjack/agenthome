import { Bot, Plus, Loader2, Users, ChevronDown, ChevronRight, Trash2, MessageCircle } from 'lucide-react'
import { useModelStore } from '@/store/modelStore'
import { useChatStore } from '@/store/chatStore'
import { useSchoolStore } from '@/store/schoolStore'
import { useTeamStore } from '@/store/teamStore'
import { useConversationStore } from '@/store/conversationStore'
import { useEffect, useState } from 'react'
import type { AgentTeam } from '@/types/team'
import type { ModelConfig } from '@/types/model'

export default function Sidebar() {
  const { models, setSelectedModel, setSelectedEntity, selectedEntity } = useModelStore()
  const { setSelectedModelConfig } = useChatStore()
  const { clearCurrentConversation } = useConversationStore()
  const {
    getAgentSchoolInfo,
    isAgentInSchool,
    isAgentInstantiated,
    isAgentInstantiating,
    loadAllAgentInstantiationStatus,
    instantiateAgent
  } = useSchoolStore()
  const {
    teams,
    loadTeams,
    isTeamInstantiated,
    isTeamInstantiating,
    loadAllTeamInstantiationStatus,
    instantiateTeam,
    deleteTeam
  } = useTeamStore()
  
  // 判断当前选中的实体是否是某个 Team
  const isTeamSelected = (teamId: string) => {
    return selectedEntity?.type === 'team' && selectedEntity.entity.id === teamId
  }

  const [expandedTeams, setExpandedTeams] = useState<Set<string>>(new Set())

  useEffect(() => {
    if (models.length > 0) {
      const agentIds = models.map(m => m.id)
      loadAllAgentInstantiationStatus(agentIds)
    }
  }, [models, loadAllAgentInstantiationStatus])

  useEffect(() => {
    loadTeams()
  }, [loadTeams])

  useEffect(() => {
    if (teams.length > 0) {
      const teamIds = teams.map(t => t.id)
      loadAllTeamInstantiationStatus(teamIds)
    }
  }, [teams, loadAllTeamInstantiationStatus])

  const toggleTeamExpand = (teamId: string) => {
    const newExpanded = new Set(expandedTeams)
    if (newExpanded.has(teamId)) {
      newExpanded.delete(teamId)
    } else {
      newExpanded.add(teamId)
    }
    setExpandedTeams(newExpanded)
  }

  const handleModelSelect = async (model: ModelConfig) => {
    const isInSchool = isAgentInSchool(model.id)
    const isInstantiated = isAgentInstantiated(model.id)

    if (isInSchool && !isInstantiated && !isAgentInstantiating(model.id)) {
      try {
        await instantiateAgent(model.id)
      } catch (error) {
        console.error('Failed to instantiate agent:', error)
        return
      }
    }

    // 先清除选中的 Team，确保只有一个高亮
    setSelectedEntity({ type: 'agent', entity: model })
    setSelectedModel(model)
    setSelectedModelConfig(model)
    // 清除当前对话，准备开始新对话
    clearCurrentConversation()
  }

  const getProviderIcon = (provider: string) => {
    const icons: Record<string, string> = {
      openai: '🤖',
      anthropic: '🧠',
      ollama: '🦙',
      custom: '⚙️'
    }
    return icons[provider] || '📦'
  }

  const getProviderName = (provider: string) => {
    const names: Record<string, string> = {
      openai: 'OpenAI',
      anthropic: 'Anthropic',
      ollama: 'Ollama',
      custom: 'Custom',
      aliyun: '阿里云'
    }
    return names[provider] || provider
  }

  const handleTeamSelect = async (team: AgentTeam) => {
    const isInstantiated = isTeamInstantiated(team.id)
    const isInstantiating = isTeamInstantiating(team.id)

    // 如果未实例化，先进行实例化
    if (!isInstantiated && !isInstantiating) {
      try {
        await instantiateTeam(team.id)
      } catch (error) {
        console.error('Failed to instantiate team:', error)
        return
      }
    }

    // 设置选中的实体为 Team 类型，同时清除选中的 Agent，确保只有一个高亮
    setSelectedEntity({ type: 'team', entity: team })
    setSelectedModel(null)
    // 清除当前对话，准备开始新对话
    clearCurrentConversation()
  }

  const handleDeleteTeam = async (e: React.MouseEvent, teamId: string) => {
    e.stopPropagation()
    if (confirm('确定要删除这个Team吗？')) {
      try {
        await deleteTeam(teamId)
      } catch (error) {
        console.error('Failed to delete team:', error)
      }
    }
  }

  return (
    <div className="w-64 bg-white flex flex-col border-r border-gray-200">
      <div className="p-4 border-b border-gray-200">
        <h1 className="text-xl font-extrabold tracking-tight">
          <span className="bg-gradient-to-r from-gray-700 via-gray-600 to-blue-800 bg-clip-text text-transparent">AgentHome</span>
        </h1>
      </div>

      <div className="flex-1 overflow-y-auto scrollbar-thin p-4">
        {/* Agent Teams 部分 */}
        {teams.length > 0 && (
          <>
            <h2 className="text-sm font-semibold text-gray-500 mb-3">Agent Teams</h2>
            <div className="space-y-2 mb-6">
              {teams.map((team) => {
                const isInstantiated = isTeamInstantiated(team.id)
                const isInstantiating = isTeamInstantiating(team.id)
                const isNotInstantiated = !isInstantiated && !isInstantiating
                const isExpanded = expandedTeams.has(team.id)
                const isSelected = isTeamSelected(team.id)

                return (
                  <div
                    key={team.id}
                    className={`rounded-lg border transition-all ${
                      isSelected
                        ? 'bg-gradient-primary border-primary-300'
                        : isNotInstantiated
                        ? 'bg-red-50 border-red-200'
                        : 'bg-blue-50 border-blue-200'
                    }`}
                  >
                    <button
                      onClick={() => handleTeamSelect(team)}
                      className={`w-full text-left px-3 py-2 ${
                        isSelected ? 'text-primary-800' : ''
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-2">
                          <button
                            onClick={(e) => {
                              e.stopPropagation()
                              toggleTeamExpand(team.id)
                            }}
                            className="p-1 text-gray-400 hover:text-gray-600"
                          >
                            {isExpanded ? (
                              <ChevronDown className="w-3 h-3" />
                            ) : (
                              <ChevronRight className="w-3 h-3" />
                            )}
                          </button>
                          <Users className="w-4 h-4 text-primary-600" />
                          <span className="font-medium text-sm truncate">{team.name}</span>
                        </div>
                        <div className="flex items-center space-x-1">
                          {isInstantiating ? (
                            <Loader2 className="w-3 h-3 animate-spin text-yellow-600" />
                          ) : isNotInstantiated ? (
                            <span className="text-xs text-red-600">未实例化</span>
                          ) : (
                            <MessageCircle className="w-3 h-3 text-green-600" />
                          )}
                          <button
                            onClick={(e) => handleDeleteTeam(e, team.id)}
                            className="p-1 text-gray-400 hover:text-danger-600"
                          >
                            <Trash2 className="w-3 h-3" />
                          </button>
                        </div>
                      </div>
                    </button>

                    {/* 展开的Sub Agent列表 */}
                    {isExpanded && (
                      <div className="px-3 pb-2 pt-1 border-t border-blue-200">
                        <p className="text-xs text-gray-500 mb-1">主Agent: {team.main_agent_name}</p>
                        {team.sub_agents.length > 0 && (
                          <div className="space-y-1">
                            <p className="text-xs text-gray-500">Sub Agents:</p>
                            {team.sub_agents.map((sa) => (
                              <div key={sa.agent_id} className="text-xs text-gray-700 pl-2">
                                • {sa.agent_name}
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          </>
        )}

        {/* Agent列表 */}
        <h2 className="text-sm font-semibold text-gray-500 mb-3">Agent列表</h2>
        <div className="space-y-2">
          {models.length === 0 ? (
            <div className="text-center py-8 text-gray-400">
              <Bot className="w-12 h-12 mx-auto mb-2 opacity-50" />
              <p className="text-sm">暂无Agent配置</p>
              <p className="text-xs">点击下方按钮添加您的第一个Agent</p>
            </div>
          ) : (
            models.map((model) => {
              const schoolInfo = getAgentSchoolInfo(model.id)
              const isInSchool = isAgentInSchool(model.id)
              const isInstantiated = isAgentInstantiated(model.id)
              const isInstantiating = isAgentInstantiating(model.id)

              const isNotInstantiated = isInSchool && !isInstantiated
              // 判断当前 Agent 是否被选中（基于 selectedEntity）
              const isAgentSelected = selectedEntity?.type === 'agent' && selectedEntity.entity.id === model.id

              return (
                <button
                  key={model.id}
                  onClick={() => handleModelSelect(model)}
                  className={`w-full text-left px-4 py-3 transition-colors shadow-elegant hover:shadow-elegant-hover ${
                    isAgentSelected
                      ? 'bg-gradient-primary text-primary-800'
                      : isNotInstantiated
                      ? 'bg-red-50 text-red-700 hover:bg-red-100 border border-red-200'
                      : 'bg-gray-50 text-gray-700 hover:bg-gray-100'
                  }`}
                >
                  <div className="flex items-center space-x-3">
                    <div className={`w-8 h-8 flex items-center justify-center text-lg rounded-full ${
                      isNotInstantiated ? 'bg-red-100' : 'bg-primary-100'
                    }`}>
                      {isInstantiating ? (
                        <Loader2 className="w-5 h-5 animate-spin" />
                      ) : (
                        getProviderIcon(model.provider)
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-medium truncate">{model.name}</p>
                      <p className="text-xs text-gray-500 truncate">
                        {getProviderName(model.provider)} · {model.model}
                      </p>
                      {isInSchool && schoolInfo?.school_name && (
                        <p className={`text-xs truncate mt-1 ${
                          isNotInstantiated ? 'text-red-600' : 'text-primary-600'
                        }`}>
                          {isInstantiating ? '实例化中...' : `已加入（${schoolInfo.school_name}）`}
                        </p>
                      )}
                      {isNotInstantiated && !isInstantiating && (
                        <p className="text-xs text-red-600 truncate mt-1">
                          未实例化，点击初始化
                        </p>
                      )}
                    </div>
                    {model.is_tested && (
                      <div className={`w-2 h-2 ${model.test_result?.success ? 'bg-success-500' : 'bg-danger-500'} rounded-full`} />
                    )}
                  </div>
                </button>
              )
            })
          )}
        </div>
      </div>

      <div className="p-4 border-t border-gray-200 space-y-2">
        <button 
          onClick={() => {
            const event = new CustomEvent('route-change', { 
              detail: { route: 'agent-management' as const } 
            })
            window.dispatchEvent(event)
          }}
          className="w-full px-4 py-2 bg-gradient-primary text-white shadow-elegant hover:shadow-elegant-hover transition-colors font-medium flex items-center justify-center space-x-2"
        >
          <Plus className="w-4 h-4" />
          <span>添加Agent</span>
        </button>
      </div>
    </div>
  )
}
