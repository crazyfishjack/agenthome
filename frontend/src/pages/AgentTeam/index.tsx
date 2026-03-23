import React, { useEffect, useState } from 'react'
import { Plus, Users, Trash2, ArrowLeft, Bot, Loader2, ChevronDown, ChevronRight, RefreshCw, Edit3, GraduationCap } from 'lucide-react'
import { useModelStore } from '@/store/modelStore'
import { useTeamStore } from '@/store/teamStore'
import { useSchoolStore } from '@/store/schoolStore'
import type { ModelConfig } from '@/types/model'
import type { AgentTeam, SubAgentConfig } from '@/types/team'
import type { SchoolAgent } from '@/types/school'
import ConfirmDialog from '@/components/ConfirmDialog'

// 扩展的Agent类型，包含School信息
interface SchoolAgentWithConfig extends SchoolAgent {
  school_id: string
  school_name: string
  agent_config: ModelConfig
}

// Sub Agent表单数据接口
interface SubAgentFormData {
  agent: SchoolAgentWithConfig
  custom_name: string
  description: string
}

// 校验自定义名称是否合法
const validateCustomName = (name: string): { valid: boolean; error?: string } => {
  if (!name.trim()) {
    return { valid: false, error: '自定义名称不能为空' }
  }
  if (name.length > 10) {
    return { valid: false, error: '自定义名称最多10个字符' }
  }
  // 禁止的字符: / \ : * ? " < > | 和空白字符
  const invalidChars = /[\\/:*?"<>|\s]/
  if (invalidChars.test(name)) {
    return { valid: false, error: '名称不能包含 / \\ : * ? " < > | 和空格' }
  }
  return { valid: true }
}

// 检查自定义名称是否重复
const checkDuplicateName = (subAgents: SubAgentFormData[], currentIndex: number, name: string): boolean => {
  return subAgents.some((sa, index) => index !== currentIndex && sa.custom_name === name)
}

export default function AgentTeamPage() {
  const { models } = useModelStore()
  const {
    teams,
    error,
    createTeam,
    deleteTeam,
    updateTeam,
    loadTeams,
    instantiateTeam,
    isTeamInstantiated,
    isTeamInstantiating,
    isTeamUpdating,
    loadAllTeamInstantiationStatus
  } = useTeamStore()
  const { schools, loadSchools } = useSchoolStore()

  const [draggedAgent, setDraggedAgent] = useState<SchoolAgentWithConfig | null>(null)
  const [dragSource, setDragSource] = useState<'agent-list' | 'sub-agent' | null>(null)

  // 创建Team表单状态
  const [newTeamName, setNewTeamName] = useState('')
  const [selectedMainAgent, setSelectedMainAgent] = useState<SchoolAgentWithConfig | null>(null)
  const [subAgents, setSubAgents] = useState<SubAgentFormData[]>([])
  const [enableSearch, setEnableSearch] = useState(false)
  const [enableThinking, setEnableThinking] = useState(false)

  // 对话框状态
  const [showCreateDialog, setShowCreateDialog] = useState(false)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [teamToDelete, setTeamToDelete] = useState<{ id: string; name: string } | null>(null)
  const [showUpdateDialog, setShowUpdateDialog] = useState(false)
  const [teamToUpdate, setTeamToUpdate] = useState<AgentTeam | null>(null)

  // 展开状态
  const [expandedTeams, setExpandedTeams] = useState<Set<string>>(new Set())

  useEffect(() => {
    loadTeams()
    loadSchools()
  }, [loadTeams, loadSchools])

  useEffect(() => {
    if (teams.length > 0) {
      const teamIds = teams.map(t => t.id)
      loadAllTeamInstantiationStatus(teamIds)
    }
  }, [teams, loadAllTeamInstantiationStatus])

  const handleBack = () => {
    const event = new CustomEvent('route-change', {
      detail: { route: 'chat' as const }
    })
    window.dispatchEvent(event)
  }

  const handleCreateTeam = async () => {
    if (!newTeamName.trim() || !selectedMainAgent) return

    // 校验所有sub agent的自定义名称
    for (let i = 0; i < subAgents.length; i++) {
      const sa = subAgents[i]
      const validation = validateCustomName(sa.custom_name)
      if (!validation.valid) {
        alert(`Sub Agent ${i + 1}: ${validation.error}`)
        return
      }
      if (checkDuplicateName(subAgents, i, sa.custom_name)) {
        alert(`Sub Agent ${i + 1}: 自定义名称 "${sa.custom_name}" 重复`)
        return
      }
    }

    try {
      const subAgentConfigs: SubAgentConfig[] = subAgents.map(({ agent, custom_name, description }) => ({
        agent_id: agent.agent_id,
        agent_name: agent.agent_name,
        custom_name: custom_name.trim(),
        description,
        agent_config: agent.agent_config
      }))

      await createTeam({
        name: newTeamName.trim(),
        main_agent_id: selectedMainAgent.agent_id,
        main_agent_name: selectedMainAgent.agent_name,
        main_agent_config: selectedMainAgent.agent_config,
        sub_agents: subAgentConfigs,
        enable_search: enableSearch,
        enable_thinking: enableThinking
      })

      // 重置表单
      setNewTeamName('')
      setSelectedMainAgent(null)
      setSubAgents([])
      setEnableSearch(false)
      setEnableThinking(false)
      setShowCreateDialog(false)
    } catch (error) {
      console.error('Failed to create team:', error)
      alert('创建Team失败')
    }
  }

  const handleDeleteTeamClick = (teamId: string, teamName: string) => {
    setTeamToDelete({ id: teamId, name: teamName })
    setShowDeleteConfirm(true)
  }

  const handleConfirmDeleteTeam = async () => {
    if (!teamToDelete) return

    try {
      await deleteTeam(teamToDelete.id)
    } catch (error) {
      console.error('Failed to delete team:', error)
      alert('删除Team失败')
    } finally {
      setShowDeleteConfirm(false)
      setTeamToDelete(null)
    }
  }

  const handleUpdateTeamClick = (team: AgentTeam) => {
    setTeamToUpdate(team)
    setNewTeamName(team.name)
    // 从schools中查找对应的agent信息
    const mainAgentConfig = team.main_agent_config as ModelConfig
    const mainAgentSchool = schools.find(s => s.agents?.some(a => a.agent_id === team.main_agent_id))
    const mainAgentInSchool = mainAgentSchool?.agents?.find(a => a.agent_id === team.main_agent_id)

    if (mainAgentInSchool && mainAgentSchool) {
      setSelectedMainAgent({
        ...mainAgentInSchool,
        school_id: mainAgentSchool.id,
        school_name: mainAgentSchool.name,
        agent_config: mainAgentConfig
      })
    } else {
      // 如果找不到school信息，使用team中的数据创建临时对象
      setSelectedMainAgent({
        agent_id: team.main_agent_id,
        agent_name: team.main_agent_name,
        added_at: '',
        school_id: '',
        school_name: '',
        agent_config: mainAgentConfig
      })
    }

    setSubAgents(team.sub_agents.map(sa => {
      const subAgentConfig = sa.agent_config as ModelConfig
      const subAgentSchool = schools.find(s => s.agents?.some(a => a.agent_id === sa.agent_id))
      const subAgentInSchool = subAgentSchool?.agents?.find(a => a.agent_id === sa.agent_id)

      return {
        agent: subAgentInSchool && subAgentSchool ? {
          ...subAgentInSchool,
          school_id: subAgentSchool.id,
          school_name: subAgentSchool.name,
          agent_config: subAgentConfig
        } : {
          agent_id: sa.agent_id,
          agent_name: sa.agent_name,
          added_at: '',
          school_id: '',
          school_name: '',
          agent_config: subAgentConfig
        },
        custom_name: sa.custom_name || sa.agent_name,
        description: sa.description
      }
    }))
    setEnableSearch(team.enable_search || false)
    setEnableThinking(team.enable_thinking || false)
    setShowUpdateDialog(true)
  }

  const handleUpdateTeam = async () => {
    if (!teamToUpdate || !newTeamName.trim() || !selectedMainAgent) return

    // 校验所有sub agent的自定义名称
    for (let i = 0; i < subAgents.length; i++) {
      const sa = subAgents[i]
      const validation = validateCustomName(sa.custom_name)
      if (!validation.valid) {
        alert(`Sub Agent ${i + 1}: ${validation.error}`)
        return
      }
      if (checkDuplicateName(subAgents, i, sa.custom_name)) {
        alert(`Sub Agent ${i + 1}: 自定义名称 "${sa.custom_name}" 重复`)
        return
      }
    }

    try {
      const subAgentConfigs: SubAgentConfig[] = subAgents.map(({ agent, custom_name, description }) => ({
        agent_id: agent.agent_id,
        agent_name: agent.agent_name,
        custom_name: custom_name.trim(),
        description,
        agent_config: agent.agent_config
      }))

      await updateTeam(teamToUpdate.id, {
        name: newTeamName.trim(),
        main_agent_id: selectedMainAgent.agent_id,
        main_agent_name: selectedMainAgent.agent_name,
        main_agent_config: selectedMainAgent.agent_config,
        sub_agents: subAgentConfigs,
        enable_search: enableSearch,
        enable_thinking: enableThinking
      })

      // 重置表单
      setNewTeamName('')
      setSelectedMainAgent(null)
      setSubAgents([])
      setEnableSearch(false)
      setEnableThinking(false)
      setShowUpdateDialog(false)
      setTeamToUpdate(null)
    } catch (error) {
      console.error('Failed to update team:', error)
      alert('更新Team失败')
    }
  }

  const handleAgentDragStart = (e: React.DragEvent, agent: SchoolAgentWithConfig, source: 'agent-list' | 'sub-agent') => {
    setDraggedAgent(agent)
    setDragSource(source)
    e.dataTransfer.effectAllowed = 'move'
    e.dataTransfer.setData('text/plain', JSON.stringify({ type: 'agent', agentId: agent.agent_id }))
  }

  const handleDragEnd = () => {
    setDraggedAgent(null)
    setDragSource(null)
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    e.dataTransfer.dropEffect = 'move'
  }

  const handleDropOnMainAgent = (e: React.DragEvent) => {
    e.preventDefault()
    if (dragSource !== 'agent-list' || !draggedAgent) {
      handleDragEnd()
      return
    }
    setSelectedMainAgent(draggedAgent)
    handleDragEnd()
  }

  const handleDropOnSubAgents = (e: React.DragEvent) => {
    e.preventDefault()
    if (dragSource !== 'agent-list' || !draggedAgent) {
      handleDragEnd()
      return
    }
    if (subAgents.length >= 10) {
      alert('最多只能添加10个Sub Agent')
      handleDragEnd()
      return
    }
    // 生成默认自定义名称
    const defaultCustomName = `${draggedAgent.agent_name}_${subAgents.length + 1}`
    setSubAgents([...subAgents, { agent: draggedAgent, custom_name: defaultCustomName, description: '' }])
    handleDragEnd()
  }

  const handleRemoveSubAgent = (index: number) => {
    setSubAgents(subAgents.filter((_, i) => i !== index))
  }

  const handleSubAgentCustomNameChange = (index: number, custom_name: string) => {
    const newSubAgents = [...subAgents]
    newSubAgents[index].custom_name = custom_name
    setSubAgents(newSubAgents)
  }

  const handleSubAgentDescriptionChange = (index: number, description: string) => {
    const newSubAgents = [...subAgents]
    newSubAgents[index].description = description
    setSubAgents(newSubAgents)
  }

  const toggleTeamExpand = (teamId: string) => {
    const newExpanded = new Set(expandedTeams)
    if (newExpanded.has(teamId)) {
      newExpanded.delete(teamId)
    } else {
      newExpanded.add(teamId)
    }
    setExpandedTeams(newExpanded)
  }

  const handleTeamClick = async (teamId: string) => {
    const isInstantiated = isTeamInstantiated(teamId)
    const isInstantiating = isTeamInstantiating(teamId)

    if (!isInstantiated && !isInstantiating) {
      try {
        await instantiateTeam(teamId)
      } catch (error) {
        console.error('Failed to instantiate team:', error)
        alert('实例化Team失败')
      }
    }
  }

  const getProviderIcon = (provider: string) => {
    const icons: Record<string, string> = {
      openai: '🤖',
      anthropic: '🧠',
      ollama: '🦙',
      custom: '⚙️',
      aliyun: '☁️'
    }
    return icons[provider] || '📦'
  }

  // 获取所有已加入School的Agent列表
  const getSchoolAgents = (): SchoolAgentWithConfig[] => {
    const schoolAgents: SchoolAgentWithConfig[] = []
    schools.forEach(school => {
      school.agents?.forEach(agent => {
        // 查找对应的model配置
        const modelConfig = models.find(m => m.id === agent.agent_id)
        if (modelConfig) {
          schoolAgents.push({
            ...agent,
            school_id: school.id,
            school_name: school.name,
            agent_config: modelConfig
          })
        }
      })
    })
    return schoolAgents
  }

  const schoolAgents = getSchoolAgents()

  // 检查表单是否可以提交
  const canSubmit = (): boolean => {
    if (!newTeamName.trim() || !selectedMainAgent) return false
    if (subAgents.length === 0) return false
    // 检查所有sub agent是否有自定义名称和描述
    return subAgents.every(sa => {
      const validation = validateCustomName(sa.custom_name)
      return validation.valid && sa.description.trim()
    })
  }

  // 获取Sub Agent的校验错误信息
  const getSubAgentError = (index: number): string | null => {
    const sa = subAgents[index]
    const validation = validateCustomName(sa.custom_name)
    if (!validation.valid) {
      return validation.error || '名称不合法'
    }
    if (checkDuplicateName(subAgents, index, sa.custom_name)) {
      return '名称重复'
    }
    if (!sa.description.trim()) {
      return '描述不能为空'
    }
    return null
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* 顶部导航 */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between max-w-7xl mx-auto">
          <div className="flex items-center space-x-4">
            <button
              onClick={handleBack}
              className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div className="flex items-center space-x-3">
              <Users className="w-8 h-8 text-primary-600" />
              <h1 className="text-2xl font-bold text-gray-800">Agent Team</h1>
            </div>
          </div>
          <button
            onClick={() => setShowCreateDialog(true)}
            className="px-4 py-2 bg-gradient-primary text-white shadow-elegant hover:shadow-elegant-hover transition-colors font-medium flex items-center space-x-2"
          >
            <Plus className="w-4 h-4" />
            <span>新建Team</span>
          </button>
        </div>
      </div>

      {/* 主内容区域 */}
      <div className="max-w-7xl mx-auto px-6 py-8">
        {error && (
          <div className="mb-6 p-4 bg-danger-50 border border-danger-200 text-danger-700 rounded-lg">
            {error}
          </div>
        )}

        <div className="flex gap-6">
          {/* 左侧Agent列表 */}
          <div className="w-80 flex-shrink-0">
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
              <div className="px-4 py-3 bg-gray-50 border-b border-gray-200">
                <h2 className="font-semibold text-gray-800">School Agent列表</h2>
                <p className="text-xs text-gray-500 mt-1">拖拽Agent到配置区域，同一个Agent可多次使用</p>
              </div>
              <div className="p-4 space-y-2 max-h-[600px] overflow-y-auto">
                {schoolAgents.length === 0 ? (
                  <div className="text-center py-8 text-gray-400">
                    <Bot className="w-12 h-12 mx-auto mb-2 opacity-50" />
                    <p className="text-sm">暂无School Agent配置</p>
                    <p className="text-xs text-gray-400 mt-1">请先在AgentSchool页面添加Agent</p>
                  </div>
                ) : (
                  schoolAgents.map((schoolAgent, index) => (
                    <div
                      key={`${schoolAgent.agent_id}-${schoolAgent.school_id}-${index}`}
                      draggable
                      onDragStart={(e) => handleAgentDragStart(e, schoolAgent, 'agent-list')}
                      onDragEnd={handleDragEnd}
                      className="p-3 rounded-lg border border-gray-200 bg-white hover:border-primary-300 hover:shadow-sm cursor-move transition-all"
                    >
                      <div className="flex items-center space-x-3">
                        <div className="w-8 h-8 bg-primary-100 flex items-center justify-center text-lg rounded-full">
                          {getProviderIcon(schoolAgent.agent_config.provider)}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="font-medium text-sm truncate">{schoolAgent.agent_name}</p>
                          <p className="text-xs text-gray-500 truncate">{schoolAgent.agent_config.model}</p>
                          <div className="flex items-center mt-1">
                            <GraduationCap className="w-3 h-3 text-primary-500 mr-1" />
                            <p className="text-xs text-primary-600 truncate">{schoolAgent.school_name}</p>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>

          {/* 中间Team配置区域 */}
          <div className="flex-1">
            {(showCreateDialog || showUpdateDialog) ? (
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                <h3 className="text-lg font-semibold text-gray-800 mb-6">
                  {showUpdateDialog ? '更新Team' : '创建新Team'}
                </h3>

                {/* Team名称 */}
                <div className="mb-6">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Team名称
                  </label>
                  <input
                    type="text"
                    value={newTeamName}
                    onChange={(e) => setNewTeamName(e.target.value)}
                    placeholder="输入Team名称"
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                  />
                </div>

                {/* 主Agent选择 */}
                <div className="mb-6">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    主Agent
                  </label>
                  <div
                    onDragOver={handleDragOver}
                    onDrop={handleDropOnMainAgent}
                    className={`p-4 border-2 border-dashed rounded-lg transition-colors ${
                      selectedMainAgent
                        ? 'border-primary-300 bg-primary-50'
                        : 'border-gray-300 bg-gray-50 hover:border-primary-300'
                    }`}
                  >
                    {selectedMainAgent ? (
                      <div className="flex items-center space-x-3">
                        <div className="w-10 h-10 bg-primary-100 flex items-center justify-center text-lg rounded-full">
                          {getProviderIcon(selectedMainAgent.agent_config.provider)}
                        </div>
                        <div className="flex-1">
                          <p className="font-medium">{selectedMainAgent.agent_name}</p>
                          <p className="text-sm text-gray-500">{selectedMainAgent.agent_config.model}</p>
                          <div className="flex items-center mt-1">
                            <GraduationCap className="w-3 h-3 text-primary-500 mr-1" />
                            <p className="text-xs text-primary-600">{selectedMainAgent.school_name}</p>
                          </div>
                        </div>
                        <button
                          onClick={() => setSelectedMainAgent(null)}
                          className="p-1 text-gray-400 hover:text-danger-600"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    ) : (
                      <div className="text-center text-gray-400 py-4">
                        <Bot className="w-8 h-8 mx-auto mb-2 opacity-50" />
                        <p className="text-sm">拖拽Agent到这里作为主Agent</p>
                      </div>
                    )}
                  </div>
                </div>

                {/* Sub Agent拖拽区域 */}
                <div className="mb-6">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Sub Agent ({subAgents.length}/10)
                  </label>
                  <div
                    onDragOver={handleDragOver}
                    onDrop={handleDropOnSubAgents}
                    className="p-4 border-2 border-dashed border-gray-300 rounded-lg bg-gray-50 min-h-[150px]"
                  >
                    {subAgents.length === 0 ? (
                      <div className="text-center text-gray-400 py-8">
                        <Users className="w-8 h-8 mx-auto mb-2 opacity-50" />
                        <p className="text-sm">拖拽Agent到这里作为Sub Agent</p>
                      </div>
                    ) : (
                      <div className="space-y-3">
                        {subAgents.map(({ agent, custom_name, description }, index) => {
                          const error = getSubAgentError(index)
                          return (
                            <div
                              key={`${agent.agent_id}-${index}`}
                              className={`p-3 bg-white border rounded-lg ${error ? 'border-danger-300' : 'border-gray-200'}`}
                            >
                              <div className="flex items-center space-x-3 mb-2">
                                <div className="w-8 h-8 bg-primary-100 flex items-center justify-center text-lg rounded-full">
                                  {getProviderIcon(agent.agent_config.provider)}
                                </div>
                                <div className="flex-1">
                                  <p className="font-medium text-sm">{agent.agent_name}</p>
                                  <p className="text-xs text-gray-500">{agent.agent_config.model}</p>
                                  <div className="flex items-center mt-1">
                                    <GraduationCap className="w-3 h-3 text-primary-500 mr-1" />
                                    <p className="text-xs text-primary-600">{agent.school_name}</p>
                                  </div>
                                </div>
                                <button
                                  onClick={() => handleRemoveSubAgent(index)}
                                  className="p-1 text-gray-400 hover:text-danger-600"
                                >
                                  <Trash2 className="w-4 h-4" />
                                </button>
                              </div>
                              {/* 自定义名称输入 */}
                              <div className="mb-2">
                                <input
                                  type="text"
                                  value={custom_name}
                                  onChange={(e) => handleSubAgentCustomNameChange(index, e.target.value)}
                                  placeholder="输入自定义名称（必填，最多10字）"
                                  className={`w-full px-3 py-2 text-sm border rounded focus:outline-none focus:ring-2 ${
                                    error && error.includes('名称')
                                      ? 'border-danger-300 focus:ring-danger-500'
                                      : 'border-gray-300 focus:ring-primary-500'
                                  }`}
                                />
                                {error && error.includes('名称') && (
                                  <p className="text-xs text-danger-600 mt-1">{error}</p>
                                )}
                                <p className="text-xs text-gray-400 mt-1">
                                  主Agent将通过此名称调用该Sub Agent，不能包含 / \ : * ? &quot; &lt; &gt; | 和空格
                                </p>
                              </div>
                              {/* 描述输入 */}
                              <input
                                type="text"
                                value={description}
                                onChange={(e) => handleSubAgentDescriptionChange(index, e.target.value)}
                                placeholder="输入Sub Agent描述（必填）"
                                className={`w-full px-3 py-2 text-sm border rounded focus:outline-none focus:ring-2 ${
                                  error && error.includes('描述')
                                    ? 'border-danger-300 focus:ring-danger-500'
                                    : 'border-gray-300 focus:ring-primary-500'
                                }`}
                              />
                              {error && error.includes('描述') && (
                                <p className="text-xs text-danger-600 mt-1">{error}</p>
                              )}
                            </div>
                          )
                        })}
                      </div>
                    )}
                  </div>
                </div>

                {/* 阿里云模型配置 */}
                {selectedMainAgent?.agent_config?.provider === 'aliyun' && (
                  <div className="mb-6 p-4 bg-blue-50 rounded-lg">
                    <h4 className="text-sm font-medium text-gray-700 mb-3">阿里云模型配置</h4>
                    <div className="space-y-3">
                      <label className="flex items-center space-x-2">
                        <input
                          type="checkbox"
                          checked={enableSearch}
                          onChange={(e) => setEnableSearch(e.target.checked)}
                          className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                        />
                        <span className="text-sm text-gray-700">启用搜索 (enable_search)</span>
                      </label>
                      <label className="flex items-center space-x-2">
                        <input
                          type="checkbox"
                          checked={enableThinking}
                          onChange={(e) => setEnableThinking(e.target.checked)}
                          className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                        />
                        <span className="text-sm text-gray-700">启用深度思考 (enable_thinking)</span>
                      </label>
                    </div>
                  </div>
                )}

                {/* 操作按钮 */}
                <div className="flex justify-end space-x-3">
                  <button
                    onClick={() => {
                      setShowCreateDialog(false)
                      setShowUpdateDialog(false)
                      setNewTeamName('')
                      setSelectedMainAgent(null)
                      setSubAgents([])
                      setEnableSearch(false)
                      setEnableThinking(false)
                      setTeamToUpdate(null)
                    }}
                    className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
                  >
                    取消
                  </button>
                  <button
                    onClick={showUpdateDialog ? handleUpdateTeam : handleCreateTeam}
                    disabled={!canSubmit()}
                    className="px-4 py-2 bg-gradient-primary text-white rounded-lg hover:shadow-elegant-hover transition-colors disabled:bg-gray-300 disabled:cursor-not-allowed"
                  >
                    {showUpdateDialog ? '更新' : '创建'}
                  </button>
                </div>
              </div>
            ) : (
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-12 text-center">
                <Users className="w-16 h-16 mx-auto mb-4 text-gray-300" />
                <h3 className="text-lg font-semibold text-gray-700 mb-2">配置Agent Team</h3>
                <p className="text-gray-500 mb-4">点击右上角&quot;新建Team&quot;按钮开始配置</p>
                <button
                  onClick={() => setShowCreateDialog(true)}
                  className="px-4 py-2 bg-gradient-primary text-white shadow-elegant hover:shadow-elegant-hover transition-colors font-medium inline-flex items-center space-x-2"
                >
                  <Plus className="w-4 h-4" />
                  <span>创建Team</span>
                </button>
              </div>
            )}
          </div>

          {/* 右侧Team列表 */}
          <div className="w-80 flex-shrink-0">
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
              <div className="px-4 py-3 bg-gray-50 border-b border-gray-200">
                <h2 className="font-semibold text-gray-800">Team列表</h2>
                <p className="text-xs text-gray-500 mt-1">已创建的Agent Team</p>
              </div>
              <div className="p-4 space-y-3 max-h-[600px] overflow-y-auto">
                {teams.length === 0 ? (
                  <div className="text-center py-8 text-gray-400">
                    <Users className="w-12 h-12 mx-auto mb-2 opacity-50" />
                    <p className="text-sm">暂无Team</p>
                  </div>
                ) : (
                  teams.map((team) => {
                    const isInstantiated = isTeamInstantiated(team.id)
                    const isInstantiating = isTeamInstantiating(team.id)
                    const isExpanded = expandedTeams.has(team.id)
                    const isNotInstantiated = !isInstantiated && !isInstantiating

                    return (
                      <div
                        key={team.id}
                        className={`p-4 rounded-lg border transition-all ${
                          isNotInstantiated
                            ? 'bg-red-50 border-red-200'
                            : 'bg-blue-50 border-blue-200'
                        }`}
                      >
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center space-x-2">
                            <button
                              onClick={() => toggleTeamExpand(team.id)}
                              className="p-1 text-gray-400 hover:text-gray-600"
                            >
                              {isExpanded ? (
                                <ChevronDown className="w-4 h-4" />
                              ) : (
                                <ChevronRight className="w-4 h-4" />
                              )}
                            </button>
                            <Users className="w-5 h-5 text-primary-600" />
                            <span className="font-medium text-sm">{team.name}</span>
                          </div>
                          <div className="flex items-center space-x-1">
                            <button
                              onClick={() => handleUpdateTeamClick(team)}
                              disabled={isTeamUpdating(team.id)}
                              className={`p-1 text-gray-400 hover:text-primary-600 disabled:opacity-50 disabled:cursor-not-allowed ${isTeamUpdating(team.id) ? 'animate-pulse' : ''}`}
                              title={isTeamUpdating(team.id) ? '更新中...' : '更新Team'}
                            >
                              {isTeamUpdating(team.id) ? (
                                <Loader2 className="w-4 h-4 animate-spin text-primary-600" />
                              ) : (
                                <Edit3 className="w-4 h-4" />
                              )}
                            </button>
                            <button
                              onClick={() => handleDeleteTeamClick(team.id, team.name)}
                              className="p-1 text-gray-400 hover:text-danger-600"
                              title="删除Team"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        </div>

                        {/* 状态显示 */}
                        <div className="flex items-center space-x-2 mb-2">
                          {isInstantiating ? (
                            <span className="text-xs text-yellow-600 flex items-center">
                              <Loader2 className="w-3 h-3 animate-spin mr-1" />
                              创建中...
                            </span>
                          ) : isNotInstantiated ? (
                            <button
                              onClick={() => handleTeamClick(team.id)}
                              className="text-xs text-red-600 hover:text-red-800 flex items-center"
                            >
                              <RefreshCw className="w-3 h-3 mr-1" />
                              未实例化，点击重新创建
                            </button>
                          ) : (
                            <span className="text-xs text-green-600">运行中</span>
                          )}
                        </div>

                        {/* 展开显示Sub Agent */}
                        {isExpanded && (
                          <div className="mt-3 pt-3 border-t border-blue-200">
                            <p className="text-xs text-gray-500 mb-2">主Agent: {team.main_agent_name}</p>
                            {team.sub_agents.length > 0 && (
                              <div className="space-y-1">
                                <p className="text-xs text-gray-500">Sub Agents:</p>
                                {team.sub_agents.map((sa, idx) => (
                                  <div key={`${sa.agent_id}-${idx}`} className="text-xs text-gray-700 pl-2">
                                    • {sa.custom_name || sa.agent_name}
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    )
                  })
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 删除确认对话框 */}
      <ConfirmDialog
        isOpen={showDeleteConfirm}
        title="删除Team"
        message={`确定要删除Team【${teamToDelete?.name}】吗？`}
        confirmText="确定"
        cancelText="取消"
        onConfirm={handleConfirmDeleteTeam}
        onCancel={() => {
          setShowDeleteConfirm(false)
          setTeamToDelete(null)
        }}
        type="danger"
      />
    </div>
  )
}
